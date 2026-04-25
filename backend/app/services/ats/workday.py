"""Workday handler — v2 stub.

Workday is the hardest target:
    - Most postings live at <tenant>.myworkdayjobs.com or <tenant>.wd5.myworkdayjobs.com
    - Apply requires creating an account (email+password) or signing in.
    - Forms are React-driven with dynamic fields and aria-labelledby relationships.
    - File upload is a multi-step modal.
    - Phone, address, work history, education, voluntary disclosures are separate pages.

Implementation strategy when promoting from stub:
    1. Maintain a per-tenant credential store; reuse the same account.
    2. Use page.evaluate() to query React-driven fields by data-automation-id.
    3. Save Playwright storage_state per tenant so we don't re-login each time.
    4. Pause for 2FA via PausedException(reason=login_2fa).
"""

from __future__ import annotations

from app.services.ats.base import ApplyContext, ApplyOutcome, ApplyResult, ATSHandler
from app.services.ats.registry import register


@register("workday")
class WorkdayHandler(ATSHandler):
    domain_patterns = ["myworkdayjobs.com", "workday.com"]

    async def apply(self, ctx: ApplyContext) -> ApplyResult:
        return ApplyResult(
            outcome=ApplyOutcome.SKIPPED,
            message="Workday handler not implemented yet (v2). Account creation + multi-page forms are non-trivial.",
        )
