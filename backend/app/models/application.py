from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.email import EmailThread
    from app.models.job_posting import JobPosting
    from app.models.tag import ApplicationTag


class ApplicationStatus(str, enum.Enum):
    QUEUED = "queued"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    GHOSTED = "ghosted"


class ApplicationMethod(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company: Mapped[str] = mapped_column(String(256), index=True)
    role_title: Mapped[str] = mapped_column(String(256))
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # remote/hybrid/onsite
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    method: Mapped[ApplicationMethod] = mapped_column(
        Enum(ApplicationMethod, name="application_method"),
        default=ApplicationMethod.MANUAL,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.QUEUED,
        index=True,
    )

    date_applied: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job_posting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True
    )

    job_posting: Mapped["JobPosting | None"] = relationship(back_populates="application")
    email_threads: Mapped[list["EmailThread"]] = relationship(back_populates="application")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="application")
    tags: Mapped[list["ApplicationTag"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
