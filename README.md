# Job Tracker

Job Tracker is a self-hosted, single-user application for running a disciplined
job search from one place. It combines a manual application tracker, Gmail
status syncing, and a guarded automation pipeline for discovering and applying
to jobs with explicit human review points.

The codebase is already useful today, but it is intentionally honest about
scope:

- Manual application tracking is implemented end to end.
- Gmail read-only sync and status detection are implemented.
- Greenhouse discovery and Greenhouse auto-apply are implemented.
- Other source kinds and ATS handlers are scaffolded as extension points, but
  they are not finished integrations yet.

Architecture details live in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## What ships today

- Application tracker with status pipeline, tags, notes, audit log, and
  analytics.
- Gmail OAuth with read-only scope and inbox scanning for ATS receipts,
  interviews, offers, and rejections.
- Master profile editor with structured answers, work history, resume variants,
  and cover letter templates.
- Source polling, scoring, and review queue for discovered job postings.
- Greenhouse Playwright handler with dry-run mode, per-job approval, audit
  screenshots, and paused-session review for low-confidence questions or
  CAPTCHAs.
- Telegram notifications for paused runs, applications, and kill-switch events.

## Current scope

This repo is strongest as a local-first MVP for one user.

- Implemented now:
  `greenhouse_board` source polling, `greenhouse` ATS submission, Gmail sync,
  paused-session review, analytics, and Telegram notifications.
- Present but not production-ready:
  ATS handlers for Lever, Workday, Ashby, iCIMS, LinkedIn, and Indeed are
  registered as stubs.
- UI scaffolding only:
  the Settings page exposes additional source kinds such as `lever_board`,
  `rss`, `linkedin`, `indeed`, and `clearancejobs`, but the worker currently
  loads only the `greenhouse_board` source plugin.

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18 + Vite + Tailwind |
| Backend | FastAPI + SQLAlchemy + Pydantic |
| Database | PostgreSQL 16 |
| Queue | Celery + Redis |
| Browser automation | Playwright (Chromium) |
| LLM | Anthropic, OpenAI, or Ollama |
| Notifications | Telegram bot |
| Local deploy | Docker Compose |
| Cluster deploy | Kubernetes starter manifests |

## Quick start

```bash
cp .env.example .env
make up
```

Then visit:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Health check: `http://localhost:8000/healthz`

The `migrate` service runs `alembic upgrade head` automatically during startup.

## Required configuration

The defaults in `.env.example` are enough to boot the app locally. The extra
credentials below are only needed for the features that use them.

### Gmail sync

1. Open <https://console.cloud.google.com/>.
2. Enable the Gmail API.
3. Create an OAuth client for a web application.
4. Add this redirect URI:
   `http://localhost:8000/api/auth/gmail/callback`
5. Put `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` into `.env`.
6. In the app, open Settings and use `connect Gmail (read-only)`.

### LLM provider

Set `LLM_PROVIDER` to `anthropic`, `openai`, or `ollama`, then fill in the
matching credential or base URL.

For a local OpenAI-compatible server, point the app at the full `/v1` endpoint.
`OPENAI_API_KEY` can be left blank in that setup.

```bash
LLM_PROVIDER=openai
LLM_MODEL=your-local-model-name
OPENAI_BASE_URL=http://172.22.192.1:1234/v1
OPENAI_API_KEY=
```

For Ollama:

```bash
ollama pull llama3.1:70b
```

Then set:

```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:70b
```

The LLM is only used when the automation runner encounters free-text or
ambiguous application questions.

### Telegram notifications

1. Create a bot with `@BotFather`.
2. Put the token in `TELEGRAM_BOT_TOKEN`.
3. Send the bot a message.
4. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`.
5. Copy the resulting `chat.id` into `TELEGRAM_CHAT_ID`.

## Daily workflow

1. Open `/profile` and fill in your master profile.
2. Upload at least one resume PDF and mark a default variant.
3. Open `/settings` and connect Gmail if you want inbox-driven status updates.
4. Add a `greenhouse_board` source using the company slug.
   Example: `stripe` maps to `boards.greenhouse.io/stripe`.
5. Poll sources from `/postings`.
6. Review scored postings, approve the ones you want, and let the worker run.
7. Resolve anything in `/paused` when a CAPTCHA or low-confidence question
   blocks automation.

## Safety rails

| Control | Default | Effect |
| --- | --- | --- |
| `DRY_RUN` | `true` | Fills forms without clicking submit |
| `PER_JOB_APPROVAL` | `true` | Keeps auto-discovered jobs in review until approved |
| `KILL_SWITCH` | `false` | Stops worker activity on the next tick |
| `MAX_APPS_PER_DAY` | `20` | Global daily cap |
| `MAX_APPS_PER_PLATFORM_PER_DAY` | `10` | Per-ATS daily cap |
| `MAX_APPS_PER_COMPANY_PER_DAY` | `1` | Per-company daily cap |

Two practical notes:

- The Settings screen can toggle the kill switch immediately, but that change is
  in-memory only for the running process.
- `DRY_RUN` and `PER_JOB_APPROVAL` are environment-driven and should be changed
  in `.env` before restarting the stack.

## Useful commands

```bash
make up
make down
make logs
make migrate
make test
make fmt
make shell-backend
make shell-db
```

## Deployment notes

`docker-compose.yml` is the primary local runtime. The `k8s/` directory mirrors
the same services for a later cluster deployment, but the project is still
designed around a single-user, local-first setup.

If you use the Kubernetes manifests, update the image references and secrets
before applying them.

## Repository layout

```text
backend/     FastAPI app, Celery worker, SQLAlchemy models, Playwright handlers
frontend/    React dashboard and workflow pages
docs/        Architecture and system notes
k8s/         Starter manifests for cluster deployment
```
