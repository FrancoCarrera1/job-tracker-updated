"""LinkedIn Easy Apply handler — opt-in.

LinkedIn's ToS prohibits automation. Enabled only when the user explicitly opts
in via JobSource.tos_acknowledged=true AND settings.enable_linkedin=true.
Use a dedicated Chrome profile and accept the ban risk.

Implementation strategy when promoting from stub:
    1. Reuse a Playwright storage_state from a manual login session.
    2. Detect Easy Apply button (button[aria-label*='Easy Apply']).
    3. Step through 1-N modal pages, filling profile fields and answering questions.
    4. Pause on phone verification, multi-question pages, or assessment requests.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.ats.base import ApplyContext, ApplyOutcome, ApplyResult, ATSHandler
from app.services.ats.registry import register


@register("linkedin")
class LinkedInHandler(ATSHandler):
    domain_patterns = ["linkedin.com"]

    async def apply(self, ctx: ApplyContext) -> ApplyResult:
        if not get_settings().enable_linkedin:
            return ApplyResult(
                outcome=ApplyOutcome.SKIPPED,
                message="LinkedIn automation disabled (ENABLE_LINKEDIN=false).",
            )
        return ApplyResult(
            outcome=ApplyOutcome.SKIPPED,
            message="LinkedIn handler not implemented yet (v2 opt-in).",
        )
