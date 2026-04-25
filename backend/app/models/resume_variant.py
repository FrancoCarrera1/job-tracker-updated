from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ResumeVariant(Base):
    """A resume tagged for a role family (DevOps, SRE, Platform, Cloud).

    Stores both the parsed structured form (for filling forms) and a path to the PDF
    on disk (for upload to ATS).
    """

    __tablename__ = "resume_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE")
    )

    name: Mapped[str] = mapped_column(String(128))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    pdf_path: Mapped[str] = mapped_column(Text)
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_default: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
