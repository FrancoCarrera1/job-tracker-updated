"""Lever handler — v2 stub.

Lever's hosted boards live at jobs.lever.co/<company>/<job-id> and the apply
form is at /<job-id>/apply. Field naming is similar to Greenhouse but with
'name', 'email', 'phone', 'org' (LinkedIn), 'urls[other]', etc.

Implementation strategy when promoting from stub:
    1. Navigate to {job_url}/apply
    2. Fill input[name=name], input[name=email], input[name=phone], input[name=org]
    3. Upload via input[type=file][name=resume]
    4. Iterate li.application-question fieldsets (Lever's analogue of Greenhouse's question blocks)
    5. Submit via button.template-btn-submit
"""

from __future__ import annotations

from app.services.ats.base import ApplyContext, ApplyOutcome, ApplyResult, ATSHandler
from app.services.ats.registry import register


@register("lever")
class LeverHandler(ATSHandler):
    domain_patterns = ["jobs.lever.co", "lever.co"]

    async def apply(self, ctx: ApplyContext) -> ApplyResult:
        return ApplyResult(
            outcome=ApplyOutcome.SKIPPED,
            message="Lever handler not implemented yet (v2). Falling through to manual review.",
        )
