# Architecture

Job Tracker is a single-user, local-first system with a clear split between the
interactive dashboard and the background automation pipeline.

The current implementation is strongest in four areas:

- manual application tracking
- Gmail read-only inbox scanning
- Greenhouse job discovery
- Greenhouse auto-apply with human-in-the-loop pauses

Everything else in this document is described from the code that exists today,
not from the longer-term product roadmap.

## System context

```mermaid
flowchart LR
    User[Browser]
    FE[React frontend<br/>Vite + Tailwind]
    API[FastAPI backend]
    DB[(Postgres)]
    Broker[(Redis)]
    Beat[Celery Beat]
    Worker[Celery worker]
    Gmail[Gmail API]
    Source[Job source plugin<br/>greenhouse_board]
    ATS[ATS websites<br/>Greenhouse implemented]
    LLM[LLM provider]
    TG[Telegram Bot API]
    Google[Google OAuth]

    User --> FE
    FE -->|HTTP /api| API
    API --> DB
    API -->|enqueue tasks| Broker
    Beat -->|scheduled tasks| Broker
    Broker --> Worker
    Worker --> DB
    Worker --> Gmail
    Worker --> Source
    Worker --> ATS
    Worker --> LLM
    Worker --> TG
    User -->|OAuth consent| Google
    Google -->|callback| API
```

## Runtime topology

| Runtime unit | Source | Responsibility |
| --- | --- | --- |
| `frontend` | `frontend/` | Dashboard UI and workflow pages |
| `backend` | `backend/app/main.py` | REST API, OAuth endpoints, CRUD, analytics |
| `postgres` | Compose / K8s | Durable relational store |
| `redis` | Compose / K8s | Celery broker and result backend |
| `worker` | `backend/app/workers/tasks.py` | Email scan, source polling, apply runs, stale sweep |
| `beat` | `backend/app/workers/celery_app.py` | Periodic task scheduler |
| `storage` volume | `/app/storage` | Resume PDFs and Playwright screenshots |

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Manual tracking | Implemented | CRUD, tags, notes, detail page, audit log, analytics |
| Master profile and resume variants | Implemented | PDF upload, parsed text, default resume selection |
| Gmail OAuth and email scan | Implemented | Read-only Gmail integration with status classification |
| Job source polling | Partially implemented | `greenhouse_board` plugin is live; other kinds are UI scaffolding only |
| ATS auto-apply | Partially implemented | `greenhouse` handler is live; Lever, Workday, Ashby, iCIMS, LinkedIn, and Indeed are stub handlers |
| Paused-session review | Implemented | Captures questions and screenshot path, then re-queues after user input |
| Notifications | Implemented | Telegram notifications for paused/apply/kill switch |
| Multi-user hosting | Not implemented | Current design assumes one user and one profile |

## Directory map

```text
backend/app/api/           FastAPI routers and response schemas
backend/app/models/        SQLAlchemy models
backend/app/services/email Gmail OAuth, fetch, parsing, thread linking
backend/app/services/sources/ Job source plugin registry and fetchers
backend/app/services/ats/  ATS handler registry and Playwright automation
backend/app/services/automation/runner.py
                           Core apply orchestration and audit logging
backend/app/workers/       Celery app and scheduled/background tasks
frontend/src/pages/        Dashboard, postings, paused queue, analytics, profile, settings
docs/                      Architecture and operator notes
```

## Frontend surface

The SPA is intentionally thin. It talks directly to the REST API and does not
carry business logic beyond form state and small UI conveniences.

| Route | Purpose |
| --- | --- |
| `/` | Pipeline dashboard and search/filtering |
| `/applications/:id` | Application detail, linked emails, audit log |
| `/postings` | Discovered posting review and approval queue |
| `/paused` | Paused automation queue |
| `/paused/:id` | Human resolution of blocked questions |
| `/analytics` | Summary metrics and weekly activity |
| `/profile` | Master profile and resume uploads |
| `/settings` | Gmail connection, source management, kill switch |

## API surface

The backend is organized around five router groups.

| Router | Prefix | Responsibility |
| --- | --- | --- |
| `applications` | `/api/applications` | CRUD, audit lookup, linked email lookup |
| `profile` | `/api/profile` | Master profile and resume variant uploads |
| `auth` | `/api/auth` | Gmail OAuth start/callback/status/disconnect |
| `automation` | `/api/automation` | Kill switch, source management, postings, paused sessions, manual task triggers |
| `analytics` | `/api/analytics` | Aggregate job-search metrics |

## Worker schedule

`Celery Beat` drives four recurring tasks:

| Task | Schedule | Purpose |
| --- | --- | --- |
| `scan_email_inbox` | every 15 minutes | Pull Gmail messages and update applications |
| `poll_sources` | hourly | Fetch new postings and score them |
| `drain_apply_queue` | every 3 minutes | Fan out queued postings into apply tasks |
| `sweep_stale_applications` | daily at 09:00 UTC | Mark older unanswered applications as `ghosted` |

## Core data flows

### Gmail scan and status detection

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant W as Worker
    participant G as Gmail API
    participant Parser as Email parser
    participant DB as Postgres
    participant TG as Telegram

    Beat->>W: scan_email_inbox
    W->>DB: load OAuthToken(provider=gmail)
    W->>G: list_message_ids(query)
    loop each fetched message
        W->>G: fetch_message
        W->>Parser: classify(subject, body, sender)
        Parser-->>W: label + confidence + matched rules
        W->>DB: upsert EmailThread
        alt confident application signal
            W->>DB: create or link Application
            W->>DB: update Application.status and last_response_at
            W->>DB: insert AuditLog(email.parsed/status.detected)
            opt notable status change
                W->>TG: notify
            end
        else recruiter_outreach or other
            W->>DB: store thread only
        end
    end
```

### Source polling and scoring

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant W as Worker
    participant Source as greenhouse_board
    participant Scorer as Posting scorer
    participant DB as Postgres

    Beat->>W: poll_sources
    W->>DB: load enabled JobSource rows
    loop each enabled source
        W->>Source: fetch(identifier, config)
        Source-->>W: DiscoveredPosting[]
        loop each new posting
            W->>Scorer: score_posting(posting, profile)
            Scorer-->>W: score + breakdown
            alt score >= apply threshold
                W->>DB: save JobPosting(status=queued)
            else score >= review threshold
                W->>DB: save JobPosting(status=review)
            else below threshold
                W->>DB: save JobPosting(status=skipped)
            end
        end
    end
```

### Apply runner and human-in-the-loop pauses

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant W as Worker
    participant Runner as Apply runner
    participant H as ATS handler
    participant Browser as Playwright
    participant LLM as LLM provider
    participant DB as Postgres
    participant TG as Telegram
    participant FE as Frontend

    Beat->>W: drain_apply_queue
    W->>Runner: run_apply(posting_id)
    Runner->>DB: load JobPosting, Profile, ResumeVariant
    Runner->>Runner: enforce kill switch and rate limits
    Runner->>H: handler.apply(ctx)
    H->>Browser: open job URL and fill form
    alt free-text or ambiguous question
        H->>LLM: answer_question(ctx)
        LLM-->>H: answer + confidence
    end
    alt submit succeeded
        H-->>Runner: ApplyResult(submitted or dry_run)
        Runner->>DB: create Application
        Runner->>DB: insert AuditLog with answers and screenshots
        Runner->>TG: notify_applied
    else pause needed
        H-->>Runner: ApplyResult(paused)
        Runner->>DB: create PausedSession
        Runner->>DB: insert AuditLog(apply.paused)
        Runner->>TG: notify_paused with deep link
        FE->>DB: user resolves paused session through API
        DB-->>Runner: posting re-queued for a fresh attempt
    else failed or skipped
        H-->>Runner: ApplyResult(failed or skipped)
        Runner->>DB: update JobPosting status and audit trail
    end
```

## Database model

The data model is intentionally compact. Most complex form state is stored in
JSONB columns so the product can iterate quickly without constant migrations.

```mermaid
erDiagram
    PROFILES ||--o{ RESUME_VARIANTS : has
    APPLICATIONS ||--o{ EMAIL_THREADS : links
    APPLICATIONS ||--o{ AUDIT_LOGS : emits
    APPLICATIONS ||--o{ APPLICATION_TAGS : has
    TAGS ||--o{ APPLICATION_TAGS : joins
    JOB_POSTINGS ||--o| APPLICATIONS : becomes
    JOB_POSTINGS ||--o{ PAUSED_SESSIONS : creates

    PROFILES {
        uuid id PK
        text full_name
        text email
        jsonb standard_answers
        jsonb eeo_answers
        jsonb skills
        jsonb work_history
        jsonb cover_letter_templates
    }
    RESUME_VARIANTS {
        uuid id PK
        uuid profile_id FK
        text name
        text[] tags
        text pdf_path
        text parsed_text
        boolean is_default
    }
    JOB_SOURCES {
        uuid id PK
        text kind
        text identifier
        boolean enabled
        boolean tos_acknowledged
        jsonb config
    }
    JOB_POSTINGS {
        uuid id PK
        text source
        text source_id
        text ats
        text company
        text role_title
        text job_url
        float score
        jsonb score_breakdown
        text status
    }
    APPLICATIONS {
        uuid id PK
        text company
        text role_title
        text status
        text method
        timestamptz date_applied
        timestamptz last_response_at
        uuid job_posting_id FK
    }
    EMAIL_THREADS {
        uuid id PK
        text gmail_thread_id
        text sender
        text classification
        float classification_confidence
        uuid application_id FK
    }
    AUDIT_LOGS {
        uuid id PK
        uuid application_id FK
        text action
        text ats
        text job_url
        jsonb answers
        text[] screenshot_paths
        jsonb extra
        boolean success
        text error
    }
    PAUSED_SESSIONS {
        uuid id PK
        uuid job_posting_id FK
        text ats
        text reason
        jsonb pending_questions
        jsonb state
        boolean resolved
    }
    OAUTH_TOKENS {
        uuid id PK
        text provider
        text user_email
        text refresh_token
        timestamptz last_scanned_at
    }
    TAGS {
        uuid id PK
        text name
        text color
    }
    APPLICATION_TAGS {
        uuid id PK
        uuid application_id FK
        uuid tag_id FK
    }
```

## Extension points

Two registries make the system extensible without changing the core worker
logic.

### Source plugins

Source plugins normalize external job feeds into a shared `DiscoveredPosting`
shape.

```python
from app.services.sources.base import DiscoveredPosting, JobSourcePlugin
from app.services.sources.registry import register_source

@register_source("my_source")
class MySource(JobSourcePlugin):
    def fetch(self, identifier: str, config: dict) -> list[DiscoveredPosting]:
        ...
```

Today, only `greenhouse_board` is imported and active.

### ATS handlers

ATS handlers own the Playwright logic for one application system.

```python
from app.services.ats.base import ATSHandler, ApplyContext, ApplyResult
from app.services.ats.registry import register

@register("myats")
class MyATSHandler(ATSHandler):
    domain_patterns = ["jobs.example.com"]

    async def apply(self, ctx: ApplyContext) -> ApplyResult:
        ...
```

The runner looks up handlers by `JobPosting.ats`, so the orchestration layer
does not need to know anything about platform-specific selectors.

## Operational notes and limitations

- The product assumes one user and one active profile.
- Gmail OAuth state is cached in memory inside the API process. That is fine for
  the current single-user MVP but not for multi-instance deployment.
- The kill switch endpoint mutates in-memory settings only. Persisting it would
  require a shared store such as Redis or a database-backed flag.
- Paused runs currently restart from the job posting URL after the user answers
  questions. They do not restore mid-form browser state yet.
- Non-Greenhouse ATS handlers currently return `skipped`, so they should be
  treated as placeholders rather than active automation targets.
