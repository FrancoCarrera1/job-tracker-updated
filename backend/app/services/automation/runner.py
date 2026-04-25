"""Apply runner — bridges DB models, ATS handlers, audit log, and notifications.

Public entry: run_apply(posting_id) called from the Celery worker.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Application,
    ApplicationMethod,
    ApplicationStatus,
    AuditLog,
    JobPosting,
    PausedReason,
    PausedSession,
    PostingStatus,
    Profile,
    ResumeVariant,
)
from app.services.ats import (
    ApplyContext,
    ApplyOutcome,
    PausedException,  # noqa: F401  - re-exported
    get_handler_class,
)
from app.services.notifications import notify_paused
from app.services.notifications.telegram import notify_applied

log = structlog.get_logger()


def run_apply(posting_id: UUID) -> dict:
    """Synchronous wrapper used from Celery."""
    return asyncio.run(_run_apply_async(posting_id))


async def _run_apply_async(posting_id: UUID) -> dict:
    s = get_settings()
    db: Session = SessionLocal()
    try:
        posting = db.get(JobPosting, posting_id)
        if posting is None:
            return {"outcome": "skipped", "reason": "posting_not_found"}

        # Kill switch
        if s.kill_switch:
            _audit(db, action="apply.kill_switch", posting=posting, success=False,
                   error="kill_switch_active")
            posting.status = PostingStatus.SKIPPED
            db.commit()
            return {"outcome": "skipped", "reason": "kill_switch"}

        if not _within_rate_limits(db, posting, s):
            _audit(db, action="apply.rate_limited", posting=posting, success=False,
                   error="rate_limit_exceeded")
            posting.status = PostingStatus.SKIPPED
            db.commit()
            return {"outcome": "skipped", "reason": "rate_limit"}

        # Per-job approval gate (default ON for first 2 weeks)
        if s.per_job_approval and posting.status != PostingStatus.QUEUED:
            return {"outcome": "skipped", "reason": "needs_approval"}

        handler_cls = get_handler_class(posting.ats or "")
        if handler_cls is None:
            posting.status = PostingStatus.REVIEW
            _audit(db, action="apply.no_handler", posting=posting, success=False,
                   error=f"no handler for ats={posting.ats}")
            db.commit()
            return {"outcome": "skipped", "reason": "no_handler"}

        profile = db.query(Profile).first()
        if profile is None:
            return {"outcome": "skipped", "reason": "profile_not_set"}

        resume = _pick_resume(db, profile.id, posting)
        if resume is None:
            posting.status = PostingStatus.REVIEW
            db.commit()
            return {"outcome": "skipped", "reason": "no_resume_variant"}

        ctx = ApplyContext(
            job_posting_id=posting.id,
            job_url=posting.job_url,
            company=posting.company,
            role_title=posting.role_title,
            job_description=posting.description or "",
            profile=_profile_to_dict(profile),
            resume_pdf_path=resume.pdf_path,
            cover_letter_text=_render_cover_letter(profile, posting),
            dry_run=s.dry_run,
            storage_dir=Path("/app/storage"),
        )

        posting.status = PostingStatus.APPLYING
        posting.last_attempted_at = datetime.now(timezone.utc)
        db.commit()

        handler = handler_cls()
        result = await handler.apply(ctx)

        # Persist outcome
        if result.outcome in (ApplyOutcome.SUBMITTED, ApplyOutcome.DRY_RUN):
            app = _create_application(db, posting, resume, ctx)
            _audit(
                db,
                action="apply.submitted" if result.outcome == ApplyOutcome.SUBMITTED else "apply.dry_run",
                posting=posting,
                application=app,
                resume_variant_id=resume.id,
                cover_letter_text=ctx.cover_letter_text,
                answers=result.answers,
                screenshots=result.screenshots,
            )
            posting.status = PostingStatus.APPLIED
            db.commit()
            notify_applied(
                company=posting.company,
                role=posting.role_title,
                dry_run=result.outcome == ApplyOutcome.DRY_RUN,
            )
            return {"outcome": result.outcome.value, "application_id": str(app.id)}

        if result.outcome == ApplyOutcome.PAUSED:
            paused = PausedSession(
                job_posting_id=posting.id,
                ats=posting.ats,
                reason=PausedReason(result.paused_reason or "unrecognized_form"),
                message=result.message,
                pending_questions=result.paused_questions,
                state=result.paused_state,
                screenshot_path=result.screenshots[-1] if result.screenshots else None,
            )
            db.add(paused)
            _audit(
                db,
                action="apply.paused",
                posting=posting,
                resume_variant_id=resume.id,
                answers=result.answers,
                screenshots=result.screenshots,
                extra={"reason": result.paused_reason, "message": result.message},
            )
            posting.status = PostingStatus.REVIEW
            db.commit()
            notify_paused(
                company=posting.company,
                role=posting.role_title,
                ats=posting.ats or "",
                reason=result.paused_reason or "",
                paused_session_id=str(paused.id),
                message=result.message,
            )
            return {"outcome": "paused", "paused_session_id": str(paused.id)}

        # FAILED or SKIPPED
        _audit(
            db,
            action=f"apply.{result.outcome.value}",
            posting=posting,
            resume_variant_id=resume.id,
            screenshots=result.screenshots,
            success=False,
            error=result.error or result.message,
        )
        posting.status = (
            PostingStatus.FAILED if result.outcome == ApplyOutcome.FAILED else PostingStatus.SKIPPED
        )
        db.commit()
        return {"outcome": result.outcome.value, "error": result.error}
    finally:
        db.close()


def _within_rate_limits(db: Session, posting: JobPosting, s) -> bool:
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    apps_today = db.query(func.count(AuditLog.id)).filter(
        AuditLog.action.in_(["apply.submitted", "apply.dry_run"]),
        AuditLog.created_at >= today_start,
    ).scalar() or 0
    if apps_today >= s.max_apps_per_day:
        log.info("rate_limit.global", apps_today=apps_today, max=s.max_apps_per_day)
        return False

    if posting.ats:
        ats_today = db.query(func.count(AuditLog.id)).filter(
            AuditLog.action.in_(["apply.submitted", "apply.dry_run"]),
            AuditLog.ats == posting.ats,
            AuditLog.created_at >= today_start,
        ).scalar() or 0
        if ats_today >= s.max_apps_per_platform_per_day:
            return False

    company_today = db.query(func.count(Application.id)).filter(
        Application.company.ilike(posting.company),
        Application.created_at >= today_start,
    ).scalar() or 0
    if company_today >= s.max_apps_per_company_per_day:
        return False

    return True


def _pick_resume(db: Session, profile_id: UUID, posting: JobPosting) -> ResumeVariant | None:
    variants = db.query(ResumeVariant).filter_by(profile_id=profile_id).all()
    if not variants:
        return None
    role_lc = (posting.role_title or "").lower()
    for v in variants:
        for tag in v.tags or []:
            if tag.lower() in role_lc:
                return v
    default = next((v for v in variants if v.is_default), None)
    return default or variants[0]


def _render_cover_letter(profile: Profile, posting: JobPosting) -> str:
    templates = profile.cover_letter_templates or {}
    role_lc = (posting.role_title or "").lower()
    template = ""
    for key, body in templates.items():
        if key.lower() in role_lc:
            template = body
            break
    if not template:
        template = templates.get("default", "")
    if not template:
        return ""
    return template.format(
        company=posting.company,
        role=posting.role_title,
        hiring_manager="Hiring Manager",
        location=posting.location or "",
        full_name=profile.full_name,
    )


def _profile_to_dict(profile: Profile) -> dict:
    return {
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "github_url": profile.github_url,
        "portfolio_url": profile.portfolio_url,
        "salary_min": profile.salary_min,
        "salary_max": profile.salary_max,
        "work_authorization": profile.work_authorization,
        "requires_sponsorship": profile.requires_sponsorship,
        "willing_to_relocate": profile.willing_to_relocate,
        "security_clearance": profile.security_clearance,
        "summary": profile.summary,
        "standard_answers": profile.standard_answers,
        "eeo_answers": profile.eeo_answers,
        "skills": profile.skills,
        "certifications": profile.certifications,
        "work_history": profile.work_history,
        "education": profile.education,
    }


def _create_application(
    db: Session, posting: JobPosting, resume: ResumeVariant, ctx: ApplyContext
) -> Application:
    app = Application(
        company=posting.company,
        role_title=posting.role_title,
        location=posting.location,
        location_type=posting.location_type,
        salary_min=posting.salary_min,
        salary_max=posting.salary_max,
        source=posting.source,
        job_url=posting.job_url,
        method=ApplicationMethod.AUTO,
        status=ApplicationStatus.APPLIED,
        date_applied=datetime.now(timezone.utc),
        job_posting_id=posting.id,
    )
    db.add(app)
    db.flush()
    return app


def _audit(
    db: Session,
    *,
    action: str,
    posting: JobPosting,
    application: Application | None = None,
    resume_variant_id: UUID | None = None,
    cover_letter_text: str | None = None,
    answers: dict | None = None,
    screenshots: list[str] | None = None,
    extra: dict | None = None,
    success: bool = True,
    error: str | None = None,
) -> None:
    db.add(
        AuditLog(
            application_id=application.id if application else None,
            action=action,
            ats=posting.ats,
            job_url=posting.job_url,
            resume_variant_id=resume_variant_id,
            cover_letter_text=cover_letter_text,
            answers=answers or {},
            screenshot_paths=screenshots or [],
            extra=extra or {},
            success=success,
            error=error,
        )
    )
