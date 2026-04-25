"""Indeed handler — opt-in.

Same ToS caveats as LinkedIn. Indeed's Apply flow varies; some postings redirect
to the company's actual ATS (which we'd handle via the appropriate handler).
"""

from __future__ import annotations

from app.config import get_settings
from app.services.ats.base import ApplyContext, ApplyOutcome, ApplyResult, ATSHandler
from app.services.ats.registry import register


@register("indeed")
class IndeedHandler(ATSHandler):
    domain_patterns = ["indeed.com"]

    async def apply(self, ctx: ApplyContext) -> ApplyResult:
        if not get_settings().enable_indeed:
            return ApplyResult(
                outcome=ApplyOutcome.SKIPPED,
                message="Indeed automation disabled (ENABLE_INDEED=false).",
            )
        return ApplyResult(
            outcome=ApplyOutcome.SKIPPED,
            message="Indeed handler not implemented yet (v2 opt-in).",
        )
