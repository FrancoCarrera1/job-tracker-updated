from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.application import Application


class EmailThread(Base):
    """A Gmail thread linked to an application.

    Stores message metadata, parsed sender/subject pattern hits, and detected
    classification (applied / interview / rejection / recruiter_outreach).
    """

    __tablename__ = "email_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    gmail_thread_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    gmail_message_id: Mapped[str] = mapped_column(String(64))

    sender: Mapped[str] = mapped_column(String(512))
    sender_domain: Mapped[str] = mapped_column(String(256), index=True)
    subject: Mapped[str] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # ats inferred from sender domain (greenhouse, lever, workday, ...)
    detected_ats: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # one of: applied, interview, rejection, offer, recruiter_outreach, other
    classification: Mapped[str] = mapped_column(String(32), default="other", index=True)
    classification_confidence: Mapped[float] = mapped_column(default=0.0)
    matched_rules: Mapped[dict] = mapped_column(JSONB, default=dict)

    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["Application | None"] = relationship(back_populates="email_threads")
