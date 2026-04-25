from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import (
    JobPostingOut,
    JobSourceIn,
    JobSourceOut,
    KillSwitchOut,
    PausedResolution,
    PausedSessionOut,
)
from app.config import get_settings
from app.db import get_db
from app.models import (
    JobPosting,
    JobSource,
    PausedSession,
    PostingStatus,
)
from app.services.sources.greenhouse_board import _normalize_identifier as normalize_greenhouse_identifier

router = APIRouter(prefix="/api/automation", tags=["automation"])


# --- kill switch ---


@router.get("/kill-switch", response_model=KillSwitchOut)
def get_kill_switch():
    s = get_settings()
    return KillSwitchOut(
        kill_switch=s.kill_switch, dry_run=s.dry_run, per_job_approval=s.per_job_approval
    )


@router.post("/kill-switch")
def set_kill_switch(value: bool):
    """Trip the kill switch by setting an env override.

    NOTE: this updates in-memory settings only; persist by editing .env or a Redis flag
    in production. The flag is read by every worker tick so changes propagate fast.
    """
    s = get_settings()
    s.kill_switch = value
    if value:
        from app.services.notifications.telegram import notify_kill_switch

        notify_kill_switch()
    return {"kill_switch": s.kill_switch}


# --- sources ---


@router.get("/sources", response_model=list[JobSourceOut])
def list_job_sources(db: Session = Depends(get_db)) -> list[JobSource]:
    return db.query(JobSource).all()


@router.post("/sources", response_model=JobSourceOut, status_code=201)
def create_job_source(payload: JobSourceIn, db: Session = Depends(get_db)) -> JobSource:
    if payload.kind in ("linkedin", "indeed") and not payload.tos_acknowledged:
        raise HTTPException(
            400,
            f"Source kind '{payload.kind}' requires explicit ToS acknowledgement.",
        )
    data = payload.model_dump()
    if payload.kind == "greenhouse_board":
        data["identifier"] = normalize_greenhouse_identifier(payload.identifier)
    src = JobSource(**data)
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


@router.delete("/sources/{source_id}", status_code=204)
def delete_job_source(source_id: UUID, db: Session = Depends(get_db)) -> None:
    src = db.get(JobSource, source_id)
    if src is None:
        return
    db.delete(src)
    db.commit()


@router.post("/sources/poll-now")
def trigger_poll():
    from app.workers.tasks import poll_sources

    poll_sources.delay()
    return {"queued": True}


# --- email scan ---


@router.post("/email/scan-now")
def trigger_email_scan():
    from app.workers.tasks import scan_email_inbox

    scan_email_inbox.delay()
    return {"queued": True}


# --- postings ---


@router.get("/postings", response_model=list[JobPostingOut])
def list_postings(
    status: PostingStatus | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[JobPosting]:
    q = db.query(JobPosting)
    if status:
        q = q.filter(JobPosting.status == status)
    return q.order_by(JobPosting.score.desc().nullslast()).limit(limit).all()


@router.post("/postings/{posting_id}/approve")
def approve_posting(posting_id: UUID, db: Session = Depends(get_db)):
    p = db.get(JobPosting, posting_id)
    if p is None:
        raise HTTPException(404, "not found")
    p.status = PostingStatus.QUEUED
    db.commit()
    from app.workers.tasks import run_apply_for_posting

    run_apply_for_posting.delay(str(posting_id))
    return {"queued": True}


@router.post("/postings/{posting_id}/skip")
def skip_posting(posting_id: UUID, db: Session = Depends(get_db)):
    p = db.get(JobPosting, posting_id)
    if p is None:
        raise HTTPException(404, "not found")
    p.status = PostingStatus.SKIPPED
    db.commit()
    return {"skipped": True}


# --- paused sessions ---


@router.get("/paused", response_model=list[PausedSessionOut])
def list_paused(db: Session = Depends(get_db)) -> list[PausedSession]:
    return (
        db.query(PausedSession)
        .filter(PausedSession.resolved.is_(False))
        .order_by(PausedSession.created_at.desc())
        .all()
    )


@router.get("/paused/{session_id}", response_model=PausedSessionOut)
def get_paused(session_id: UUID, db: Session = Depends(get_db)) -> PausedSession:
    p = db.get(PausedSession, session_id)
    if p is None:
        raise HTTPException(404, "not found")
    return p


@router.post("/paused/{session_id}/resolve")
def resolve_paused(
    session_id: UUID, payload: PausedResolution, db: Session = Depends(get_db)
):
    p = db.get(PausedSession, session_id)
    if p is None:
        raise HTTPException(404, "not found")
    p.resolved = True
    p.resolved_at = datetime.now(timezone.utc)
    p.resolution = payload.model_dump()
    db.commit()

    if payload.proceed:
        # Merge user's answers into profile.standard_answers so we don't ask again.
        from app.models import Profile

        prof = db.query(Profile).first()
        if prof is not None:
            sa = dict(prof.standard_answers or {})
            for q, ans in payload.answers.items():
                sa[q] = ans
            prof.standard_answers = sa
            db.commit()

        # Re-queue the posting for another attempt now that we have answers.
        posting = db.get(JobPosting, p.job_posting_id)
        if posting is not None:
            posting.status = PostingStatus.QUEUED
            db.commit()
            from app.workers.tasks import run_apply_for_posting

            run_apply_for_posting.delay(str(posting.id))

    return {"resolved": True, "proceed": payload.proceed}
