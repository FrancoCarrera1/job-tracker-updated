from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import ApplicationIn, ApplicationOut
from app.db import get_db
from app.models import Application, ApplicationStatus, ApplicationTag, Tag

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    status: ApplicationStatus | None = None,
    tag: str | None = None,
    company: str | None = None,
    db: Session = Depends(get_db),
) -> list[Application]:
    stmt = select(Application).options(selectinload(Application.tags).selectinload(ApplicationTag.tag))
    if status:
        stmt = stmt.where(Application.status == status)
    if company:
        stmt = stmt.where(Application.company.ilike(f"%{company}%"))
    if tag:
        stmt = stmt.join(ApplicationTag).join(Tag).where(Tag.name == tag)
    stmt = stmt.order_by(Application.updated_at.desc())
    return list(db.execute(stmt).scalars().unique())


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationIn, db: Session = Depends(get_db)) -> Application:
    app = Application(**payload.model_dump(exclude={"tags"}))
    db.add(app)
    db.flush()
    _set_tags(db, app, payload.tags)
    db.commit()
    db.refresh(app)
    return app


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: UUID, db: Session = Depends(get_db)) -> Application:
    app = db.get(Application, app_id)
    if app is None:
        raise HTTPException(404, "not found")
    return app


@router.patch("/{app_id}", response_model=ApplicationOut)
def update_application(
    app_id: UUID, payload: ApplicationIn, db: Session = Depends(get_db)
) -> Application:
    app = db.get(Application, app_id)
    if app is None:
        raise HTTPException(404, "not found")
    data = payload.model_dump(exclude={"tags"}, exclude_unset=True)
    for k, v in data.items():
        setattr(app, k, v)
    if app.status == ApplicationStatus.APPLIED and app.date_applied is None:
        app.date_applied = datetime.now(timezone.utc)
    _set_tags(db, app, payload.tags)
    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=204)
def delete_application(app_id: UUID, db: Session = Depends(get_db)) -> None:
    app = db.get(Application, app_id)
    if app is None:
        return
    db.delete(app)
    db.commit()


@router.get("/{app_id}/audit", response_model=list)
def application_audit(
    app_id: UUID,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    from app.models import AuditLog

    rows = (
        db.query(AuditLog)
        .filter(AuditLog.application_id == app_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "action": r.action,
            "ats": r.ats,
            "answers": r.answers,
            "screenshot_paths": r.screenshot_paths,
            "success": r.success,
            "error": r.error,
            "extra": r.extra,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{app_id}/emails")
def application_emails(app_id: UUID, db: Session = Depends(get_db)):
    from app.models import EmailThread

    rows = (
        db.query(EmailThread)
        .filter(EmailThread.application_id == app_id)
        .order_by(EmailThread.received_at.desc())
        .all()
    )
    return [
        {
            "id": str(r.id),
            "sender": r.sender,
            "subject": r.subject,
            "snippet": r.snippet,
            "received_at": r.received_at.isoformat(),
            "classification": r.classification,
            "classification_confidence": r.classification_confidence,
            "gmail_thread_id": r.gmail_thread_id,
        }
        for r in rows
    ]


def _set_tags(db: Session, app: Application, tag_names: list[str]) -> None:
    db.query(ApplicationTag).filter(ApplicationTag.application_id == app.id).delete()
    for name in tag_names:
        tag = db.query(Tag).filter_by(name=name).one_or_none()
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        db.add(ApplicationTag(application_id=app.id, tag_id=tag.id))
