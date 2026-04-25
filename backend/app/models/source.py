from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class JobSource(Base):
    """Configured job source. Examples:

    - kind=greenhouse_board, identifier='stripe'  -> https://boards.greenhouse.io/stripe
    - kind=lever_board,      identifier='netflix'
    - kind=rss,              identifier='https://example.com/jobs.rss'
    - kind=clearancejobs,    identifier='devops'  (search query)
    - kind=linkedin,         identifier='devops engineer san antonio'  (opt-in)
    - kind=indeed,           identifier='sre remote'                    (opt-in)
    """

    __tablename__ = "job_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    kind: Mapped[str] = mapped_column(String(32), index=True)
    identifier: Mapped[str] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(default=True)
    tos_acknowledged: Mapped[bool] = mapped_column(default=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
