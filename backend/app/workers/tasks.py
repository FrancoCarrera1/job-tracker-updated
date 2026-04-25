from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Application,
    ApplicationStatus,
    JobPosting,
    JobSource,
    PostingStatus,
    Profile,
)
from app.services.email.scanner import scan_inbox
from app.services.sources import get_source_class
from app.services.sources.scorer import score_posting
from app.workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.scan_email_inbox")
def scan_email_inbox() -> dict:
    db = SessionLocal()
    try:
        result = scan_inbox(db)
        return result.__dict__
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.poll_sources")
def poll_sources() -> dict:
    s = get_settings()
    db = SessionLocal()
    summary = {"polled": 0, "discovered": 0, "queued": 0, "review": 0}
    try:
        if s.kill_switch:
            return {"skipped": "kill_switch"}
        sources = db.query(JobSource).filter(JobSource.enabled.is_(True)).all()
        profile = db.query(Profile).first()
        if profile is None:
            return {"skipped": "no_profile"}

        for src in sources:
            if not _source_enabled(src.kind, s):
                continue
            if src.kind in ("linkedin", "indeed") and not src.tos_acknowledged:
                continue
            cls = get_source_class(src.kind)
            if cls is None:
                continue
            try:
                postings = cls().fetch(src.identifier, src.config or {})
            except Exception as e:
                src.last_error = str(e)
                db.commit()
                log.warning("source.fetch_failed", kind=src.kind, error=str(e))
                continue
            src.last_polled_at = datetime.now(timezone.utc)
            src.last_error = None
            summary["polled"] += 1
            for d in postings:
                existing = (
                    db.query(JobPosting)
                    .filter_by(source=d.source, source_id=d.source_id)
                    .one_or_none()
                )
                if existing is not None:
                    continue
                summary["discovered"] += 1
                p = JobPosting(
                    source=d.source,
                    source_id=d.source_id,
                    ats=d.ats,
                    company=d.company,
                    role_title=d.role_title,
                    job_url=d.job_url,
                    location=d.location,
                    location_type=d.location_type,
                    salary_min=d.salary_min,
                    salary_max=d.salary_max,
                    requires_clearance=d.requires_clearance,
                    clearance_level=d.clearance_level,
                    description=d.description,
                    skills=d.skills,
                )
                score, breakdown = score_posting(d, profile)
                p.score = score
                p.score_breakdown = breakdown
                if score >= s.score_threshold_apply:
                    p.status = PostingStatus.QUEUED
                    summary["queued"] += 1
                elif score >= s.score_threshold_review:
                    p.status = PostingStatus.REVIEW
                    summary["review"] += 1
                else:
                    p.status = PostingStatus.SKIPPED
                db.add(p)
            db.commit()
    finally:
        db.close()
    return summary


@celery_app.task(name="app.workers.tasks.drain_apply_queue")
def drain_apply_queue(limit: int = 5) -> dict:
    s = get_settings()
    if s.kill_switch:
        return {"skipped": "kill_switch"}
    db = SessionLocal()
    try:
        queued = (
            db.query(JobPosting)
            .filter(JobPosting.status == PostingStatus.QUEUED)
            .order_by(JobPosting.score.desc().nullslast())
            .limit(limit)
            .all()
        )
        ids = [str(p.id) for p in queued]
    finally:
        db.close()
    fired = []
    for posting_id in ids:
        run_apply_for_posting.delay(posting_id)
        fired.append(posting_id)
    return {"queued": fired}


@celery_app.task(name="app.workers.tasks.run_apply_for_posting", bind=True, max_retries=2)
def run_apply_for_posting(self, posting_id: str) -> dict:
    from app.services.automation.runner import run_apply

    try:
        return run_apply(UUID(posting_id))
    except Exception as e:
        log.exception("apply.task_failed", posting_id=posting_id, error=str(e))
        raise self.retry(exc=e, countdown=60)


@celery_app.task(name="app.workers.tasks.sweep_stale_applications")
def sweep_stale_applications() -> dict:
    """Mark APPLIED apps with no response after 14 days as GHOSTED. Flag for follow-up."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        stale = (
            db.query(Application)
            .filter(
                Application.status == ApplicationStatus.APPLIED,
                Application.date_applied != None,  # noqa: E711
                Application.date_applied < cutoff,
                Application.last_response_at == None,  # noqa: E711
            )
            .all()
        )
        for app in stale:
            app.status = ApplicationStatus.GHOSTED
        db.commit()
        return {"ghosted": len(stale)}
    finally:
        db.close()


def _source_enabled(kind: str, s) -> bool:
    return {
        "greenhouse_board": s.enable_greenhouse,
        "lever_board": s.enable_lever,
        "clearancejobs": s.enable_clearancejobs,
        "linkedin": s.enable_linkedin,
        "indeed": s.enable_indeed,
        "rss": True,
    }.get(kind, True)
