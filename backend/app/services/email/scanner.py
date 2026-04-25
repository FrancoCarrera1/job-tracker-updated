"""Glue between Gmail API and the parser. Idempotent — safe to run repeatedly."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationMethod,
    ApplicationStatus,
    AuditLog,
    EmailThread,
    OAuthToken,
)
from app.services.email import gmail, parser

log = structlog.get_logger()

# Gmail search query: 30 days back, ATS senders or job-related keywords.
DEFAULT_QUERY = (
    "newer_than:30d "
    '(from:greenhouse.io OR from:lever.co OR from:myworkday.com '
    'OR from:icims.com OR from:ashbyhq.com OR from:smartrecruiters.com '
    'OR from:taleo.net OR from:bamboohr.com OR from:jobvite.com '
    'OR subject:"thank you for applying" OR subject:"application received" '
    'OR subject:interview OR subject:"next steps" OR subject:offer)'
)


@dataclass
class ScanResult:
    fetched: int = 0
    new_threads: int = 0
    updated_threads: int = 0
    new_applications: int = 0
    status_updates: int = 0


def scan_inbox(db: Session, query: str | None = None, max_messages: int = 200) -> ScanResult:
    token = db.query(OAuthToken).filter_by(provider="gmail").one_or_none()
    if token is None:
        raise RuntimeError("Gmail not connected. Visit /api/auth/gmail/start first.")
    service = gmail.get_gmail_service(token)
    msg_ids = gmail.list_message_ids(service, query or DEFAULT_QUERY, max_results=max_messages)
    log.info("email.scan.start", count=len(msg_ids))

    result = ScanResult()
    for msg_id in msg_ids:
        try:
            data = gmail.fetch_message(service, msg_id)
        except Exception as e:
            log.warning("email.scan.fetch_failed", msg_id=msg_id, error=str(e))
            continue
        result.fetched += 1
        process_message(db, data, result)

    token.last_scanned_at = datetime.now(timezone.utc)
    db.commit()
    log.info("email.scan.done", **result.__dict__)
    return result


def process_message(db: Session, data: dict, result: ScanResult) -> None:
    classification = parser.classify(data["subject"], data["body_text"], data["sender"])
    ats = parser.detect_ats(data["sender"])
    domain = parser._extract_domain(data["sender"])

    thread = (
        db.query(EmailThread)
        .filter(EmailThread.gmail_thread_id == data["gmail_thread_id"])
        .one_or_none()
    )
    if thread is None:
        thread = EmailThread(
            gmail_thread_id=data["gmail_thread_id"],
            gmail_message_id=data["gmail_message_id"],
            sender=data["sender"],
            sender_domain=domain,
            subject=data["subject"],
            snippet=data["snippet"],
            body_text=data["body_text"],
            received_at=data["received_at"],
            detected_ats=ats,
            classification=classification.label,
            classification_confidence=classification.confidence,
            matched_rules=classification.matched,
        )
        db.add(thread)
        result.new_threads += 1
    else:
        # Newer messages on the thread can sharpen classification.
        if classification.confidence > thread.classification_confidence:
            thread.classification = classification.label
            thread.classification_confidence = classification.confidence
            thread.matched_rules = classification.matched
            thread.gmail_message_id = data["gmail_message_id"]
            thread.subject = data["subject"]
            thread.snippet = data["snippet"]
            thread.body_text = data["body_text"]
            thread.received_at = data["received_at"]
            result.updated_threads += 1

    # Recruiter outreach without prior application: keep as a thread but don't create app.
    if classification.label == "recruiter_outreach":
        db.commit()
        return

    company, role = parser.extract_company_role(data["subject"], data["body_text"], data["sender"])
    if not company:
        db.commit()
        return

    app = _link_or_create_application(db, thread, company, role, classification)
    if app is None:
        db.commit()
        return

    # Status update from email.
    new_status = parser.status_for(classification.label)
    if new_status and _should_advance(app.status, new_status):
        app.status = ApplicationStatus(new_status)
        app.last_response_at = data["received_at"]
        db.add(
            AuditLog(
                application_id=app.id,
                action="status.detected",
                ats=ats,
                extra={
                    "from_email": data["gmail_message_id"],
                    "classification": classification.label,
                    "confidence": classification.confidence,
                    "matched_rules": classification.matched,
                },
            )
        )
        result.status_updates += 1

    db.commit()


def _link_or_create_application(
    db: Session,
    thread: EmailThread,
    company: str,
    role: str | None,
    classification: parser.Classification,
) -> Application | None:
    if thread.application_id:
        return db.get(Application, thread.application_id)

    # Dedupe against existing apps for same company.
    existing = db.query(Application).filter(Application.company.ilike(company)).all()
    role = role or "(unknown)"
    if parser.is_likely_duplicate(company, role, [(a.company, a.role_title) for a in existing]):
        # link to the most recent matching one
        match = sorted(existing, key=lambda a: a.created_at, reverse=True)[0]
        thread.application_id = match.id
        return match

    # Only create from confident classifications, not from "other"/random emails.
    if classification.label not in ("applied", "interview", "rejection", "offer"):
        return None

    initial_status = (
        ApplicationStatus(parser.status_for(classification.label))
        if parser.status_for(classification.label)
        else ApplicationStatus.APPLIED
    )
    app = Application(
        company=company,
        role_title=role,
        status=initial_status,
        method=ApplicationMethod.MANUAL,
        source="email_detected",
        date_applied=thread.received_at if classification.label == "applied" else None,
    )
    db.add(app)
    db.flush()
    thread.application_id = app.id
    db.add(
        AuditLog(
            application_id=app.id,
            action="email.parsed",
            extra={
                "company": company,
                "role": role,
                "classification": classification.label,
                "confidence": classification.confidence,
            },
        )
    )
    return app


_RANK = {
    ApplicationStatus.QUEUED: 0,
    ApplicationStatus.APPLIED: 1,
    ApplicationStatus.SCREENING: 2,
    ApplicationStatus.INTERVIEW: 3,
    ApplicationStatus.OFFER: 4,
    ApplicationStatus.REJECTED: 5,
    ApplicationStatus.GHOSTED: 5,
}


def _should_advance(current: ApplicationStatus, candidate: str) -> bool:
    """Don't regress status. e.g. don't drop INTERVIEW back to APPLIED on a duplicate receipt."""
    cand = ApplicationStatus(candidate)
    if cand in (ApplicationStatus.REJECTED, ApplicationStatus.OFFER):
        return True  # terminal states always win
    return _RANK[cand] > _RANK[current]
