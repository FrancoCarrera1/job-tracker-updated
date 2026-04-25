"""Ashby handler — v2 stub.

Ashby boards live at jobs.ashbyhq.com/<company>/<id>. Forms are predictable
single-page with React component classes. Generally easier than Workday.
"""

from __future__ import annotations

from app.services.ats.base import ApplyContext, ApplyOutcome, ApplyResult, ATSHandler
from app.services.ats.registry import register


@register("ashby")
class AshbyHandler(ATSHandler):
    domain_patterns = ["jobs.ashbyhq.com", "ashbyhq.com"]

    async def apply(self, ctx: ApplyContext) -> ApplyResult:
        return ApplyResult(
            outcome=ApplyOutcome.SKIPPED,
            message="Ashby handler not implemented yet (v2).",
        )
