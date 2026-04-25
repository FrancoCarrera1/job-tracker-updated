from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PausedReason(str, enum.Enum):
    CAPTCHA = "captcha"
    LOW_CONFIDENCE_QUESTION = "low_confidence_question"
    ASSESSMENT_REQUIRED = "assessment_required"
    LOGIN_2FA = "login_2fa"
    UNRECOGNIZED_FORM = "unrecognized_form"
    REQUIREMENT_MISMATCH = "requirement_mismatch"
    APPROVAL_REQUIRED = "approval_required"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class PausedSession(Base):
    """An automation run that paused for human input.

    `state` is opaque to the framework but specific to the ATS handler that
    created it — typically contains the Playwright storage state path, the
    URL it stopped at, and the question(s) requiring answers.
    """

    __tablename__ = "paused_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_postings.id", ondelete="CASCADE")
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )

    ats: Mapped[str] = mapped_column(String(32))
    reason: Mapped[PausedReason] = mapped_column(
        Enum(PausedReason, name="paused_reason", values_callable=_enum_values)
    )
    message: Mapped[str] = mapped_column(Text)
    pending_questions: Mapped[list] = mapped_column(JSONB, default=list)
    state: Mapped[dict] = mapped_column(JSONB, default=dict)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    resolved: Mapped[bool] = mapped_column(default=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
