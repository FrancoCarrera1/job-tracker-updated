from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.application import Application


class AuditLog(Base):
    """Append-only record of every automated action.

    Stores the exact resume/cover letter content sent, every answer given,
    and screenshot paths of the final form before submit.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=True
    )

    # e.g. "apply.submitted", "apply.dry_run", "apply.paused", "apply.failed",
    #      "email.parsed", "status.detected", "kill_switch.tripped"
    action: Mapped[str] = mapped_column(String(64), index=True)

    ats: Mapped[str | None] = mapped_column(String(32), nullable=True)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    resume_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    cover_letter_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answers: Mapped[dict] = mapped_column(JSONB, default=dict)
    screenshot_paths: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    success: Mapped[bool] = mapped_column(default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    application: Mapped["Application | None"] = relationship(back_populates="audit_logs")
