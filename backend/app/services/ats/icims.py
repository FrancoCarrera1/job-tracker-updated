"""iCIMS handler — v2 stub.

iCIMS hosts vary by tenant: careers-<tenant>.icims.com. Forms are older-style
HTML with iframes. Often requires account creation.
"""

from __future__ import annotations

from app.services.ats.base import ApplyContext, ApplyOutcome, ApplyResult, ATSHandler
from app.services.ats.registry import register


@register("icims")
class ICIMSHandler(ATSHandler):
    domain_patterns = ["icims.com"]

    async def apply(self, ctx: ApplyContext) -> ApplyResult:
        return ApplyResult(
            outcome=ApplyOutcome.SKIPPED,
            message="iCIMS handler not implemented yet (v2).",
        )
