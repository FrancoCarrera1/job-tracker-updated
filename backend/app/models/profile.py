from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Profile(Base):
    """Master profile. Single-row in MVP but keyed by id for multi-user later."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    full_name: Mapped[str] = mapped_column(String(256))
    email: Mapped[str] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    salary_min: Mapped[int | None] = mapped_column(nullable=True)
    salary_max: Mapped[int | None] = mapped_column(nullable=True)

    work_authorization: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requires_sponsorship: Mapped[bool] = mapped_column(default=False)
    willing_to_relocate: Mapped[bool] = mapped_column(default=False)
    security_clearance: Mapped[str | None] = mapped_column(String(64), nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Standard answers keyed by question pattern
    # e.g. {"years_python": "5", "years_kubernetes": "4", "willing_to_travel": "yes"}
    standard_answers: Mapped[dict] = mapped_column(JSONB, default=dict)

    # EEO / demographic answers (separate so we can decline-to-state by default)
    eeo_answers: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Skills with years of experience: {"kubernetes": 4, "terraform": 3, ...}
    skills: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Certifications: [{"name": "RHCSA", "issued": "2023-05", "expires": null}, ...]
    certifications: Mapped[list] = mapped_column(JSONB, default=list)

    # Work history: [{"company": "...", "role": "...", "start": "...", "end": "...",
    #                 "bullets": ["...", "..."]}]
    work_history: Mapped[list] = mapped_column(JSONB, default=list)

    # Education: [{"school": "...", "degree": "...", "year": "..."}]
    education: Mapped[list] = mapped_column(JSONB, default=list)

    # References: [{"name": "...", "relationship": "...", "email": "...", "phone": "..."}]
    references: Mapped[list] = mapped_column(JSONB, default=list)

    # Cover letter templates by tag {"devops": "Dear {hiring_manager}, ..."}
    cover_letter_templates: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
