from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.application import Application


class PostingStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    SCORED = "scored"
    QUEUED = "queued"
    REVIEW = "review"
    APPLYING = "applying"
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class JobPosting(Base):
    """Discovered job posting before/at the time of application."""

    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    ats: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    company: Mapped[str] = mapped_column(String(256), index=True)
    role_title: Mapped[str] = mapped_column(String(256))
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_clearance: Mapped[bool] = mapped_column(default=False)
    clearance_level: Mapped[str | None] = mapped_column(String(64), nullable=True)

    job_url: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[PostingStatus] = mapped_column(
        Enum(PostingStatus, name="posting_status", values_callable=_enum_values),
        default=PostingStatus.DISCOVERED,
        index=True,
    )

    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    application: Mapped["Application | None"] = relationship(back_populates="job_posting", uselist=False)
