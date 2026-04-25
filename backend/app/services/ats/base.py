"""ATSHandler base class + plugin registry.

Adding a new ATS:

    from app.services.ats.base import ATSHandler, register

    @register("myats")
    class MyATSHandler(ATSHandler):
        ats_name = "myats"
        domain_patterns = ["myats.com"]

        async def apply(self, ctx):
            ...
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from playwright.async_api import Page


class ApplyOutcome(str, enum.Enum):
    SUBMITTED = "submitted"
    DRY_RUN = "dry_run"
    PAUSED = "paused"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class ApplyContext:
    """Everything a handler needs to attempt an application."""

    job_posting_id: UUID
    job_url: str
    company: str
    role_title: str
    job_description: str = ""
    profile: dict[str, Any] = field(default_factory=dict)
    resume_pdf_path: str = ""
    cover_letter_text: str = ""
    dry_run: bool = True
    storage_dir: Path = field(default_factory=lambda: Path("/app/storage"))


@dataclass
class ApplyResult:
    outcome: ApplyOutcome
    message: str = ""
    answers: dict[str, Any] = field(default_factory=dict)
    screenshots: list[str] = field(default_factory=list)
    paused_reason: str | None = None
    paused_questions: list[dict] = field(default_factory=list)
    paused_state: dict = field(default_factory=dict)
    error: str | None = None


class PausedException(Exception):
    """Raised by a handler when it needs human input. Caught by the runner."""

    def __init__(
        self,
        reason: str,
        message: str,
        pending_questions: list[dict] | None = None,
        state: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.pending_questions = pending_questions or []
        self.state = state or {}


class ATSHandler(ABC):
    """Subclass and register with @register('name')."""

    ats_name: str = ""
    domain_patterns: list[str] = []

    @abstractmethod
    async def apply(self, ctx: ApplyContext) -> ApplyResult:  # pragma: no cover
        ...

    # --- shared helpers ---

    async def screenshot(self, page: "Page", ctx: ApplyContext, label: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out_dir = ctx.storage_dir / "screenshots" / str(ctx.job_posting_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{ts}-{label}.png"
        await page.screenshot(path=str(path), full_page=True)
        return str(path)

    @staticmethod
    async def detect_captcha(page: "Page") -> bool:
        """Heuristic — true if any common CAPTCHA frame/element is present."""
        try:
            for selector in [
                "iframe[src*='recaptcha']",
                "iframe[src*='hcaptcha']",
                "div.g-recaptcha",
                "div.h-captcha",
                "[id*='captcha']",
                "[class*='captcha']",
            ]:
                if await page.locator(selector).count():
                    return True
        except Exception:
            pass
        return False
