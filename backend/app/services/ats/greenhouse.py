"""Greenhouse handler — MVP target.

Greenhouse hosted job boards live at boards.greenhouse.io/<company>/jobs/<id> and
the application form is at the same URL with #app or /jobs/<id>#app, or via the
embedded form on the company's career page. The form is a single-page submit
with predictable field IDs.

Fields commonly present:
    first_name, last_name, email, phone (always)
    resume (file upload)
    cover_letter (file upload, optional)
    custom questions  (radio/select/checkbox/text/textarea)
    EEO questions     (gender, race, veteran, disability) -- always optional

Submit button: button[type=submit] inside form#application_form, or
text "Submit Application".
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import structlog
from playwright.async_api import (
    Locator,
    Page,
    TimeoutError as PWTimeout,
    async_playwright,
)

from app.config import get_settings
from app.services.ats.base import (
    ApplyContext,
    ApplyOutcome,
    ApplyResult,
    ATSHandler,
    PausedException,
)
from app.services.ats.registry import register
from app.services.llm import QuestionContext, get_llm

log = structlog.get_logger()


@register("greenhouse")
class GreenhouseHandler(ATSHandler):
    domain_patterns = ["boards.greenhouse.io", "job-boards.greenhouse.io", "greenhouse.io"]

    async def apply(self, ctx: ApplyContext) -> ApplyResult:
        screenshots: list[str] = []
        answers: dict[str, Any] = {}

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(ctx.job_url, wait_until="domcontentloaded", timeout=30_000)

                # Some Greenhouse pages render the form inline; others have an "Apply" button.
                await self._click_apply_if_present(page)
                await page.wait_for_selector(
                    "form#application_form, form[action*='greenhouse']", timeout=15_000
                )

                if await self.detect_captcha(page):
                    shot = await self.screenshot(page, ctx, "captcha")
                    screenshots.append(shot)
                    raise PausedException(
                        reason="captcha",
                        message="Greenhouse loaded a CAPTCHA — solve it and resume.",
                        state={"job_url": ctx.job_url, "screenshot": shot},
                    )

                await self._fill_basic_fields(page, ctx, answers)
                await self._upload_resume(page, ctx, answers)
                await self._upload_cover_letter(page, ctx, answers)

                paused_questions = await self._answer_custom_questions(page, ctx, answers)
                if paused_questions:
                    shot = await self.screenshot(page, ctx, "low-confidence")
                    screenshots.append(shot)
                    raise PausedException(
                        reason="low_confidence_question",
                        message="One or more custom questions had low LLM confidence.",
                        pending_questions=paused_questions,
                        state={"job_url": ctx.job_url, "screenshot": shot},
                    )

                await self._answer_eeo_questions(page, ctx, answers)

                # Final pre-submit screenshot is part of the audit log either way.
                shot_final = await self.screenshot(page, ctx, "pre-submit")
                screenshots.append(shot_final)

                if ctx.dry_run:
                    log.info("greenhouse.dry_run", url=ctx.job_url)
                    return ApplyResult(
                        outcome=ApplyOutcome.DRY_RUN,
                        message="Dry run — form filled but not submitted.",
                        answers=answers,
                        screenshots=screenshots,
                    )

                await self._submit(page)
                shot_after = await self.screenshot(page, ctx, "post-submit")
                screenshots.append(shot_after)

                return ApplyResult(
                    outcome=ApplyOutcome.SUBMITTED,
                    message="Application submitted via Greenhouse.",
                    answers=answers,
                    screenshots=screenshots,
                )

            except PausedException as p:
                return ApplyResult(
                    outcome=ApplyOutcome.PAUSED,
                    message=p.message,
                    paused_reason=p.reason,
                    paused_questions=p.pending_questions,
                    paused_state=p.state,
                    answers=answers,
                    screenshots=screenshots,
                )
            except Exception as e:
                log.exception("greenhouse.failed", url=ctx.job_url, error=str(e))
                return ApplyResult(
                    outcome=ApplyOutcome.FAILED,
                    error=str(e),
                    answers=answers,
                    screenshots=screenshots,
                )
            finally:
                await browser.close()

    # --- helpers ---

    async def _click_apply_if_present(self, page: Page) -> None:
        for sel in [
            "a:has-text('Apply for this Job')",
            "a:has-text('Apply Now')",
            "button:has-text('Apply')",
            "a#apply_button",
        ]:
            try:
                el = page.locator(sel).first
                if await el.count() and await el.is_visible():
                    await el.click(timeout=3_000)
                    await page.wait_for_load_state("domcontentloaded")
                    return
            except (PWTimeout, Exception):
                continue

    async def _fill_basic_fields(self, page: Page, ctx: ApplyContext, answers: dict) -> None:
        p = ctx.profile
        first, last = _split_name(p.get("full_name", ""))
        await self._fill_input(page, "input#first_name", first, answers, "first_name")
        await self._fill_input(page, "input#last_name", last, answers, "last_name")
        await self._fill_input(page, "input#email", p.get("email", ""), answers, "email")
        if p.get("phone"):
            await self._fill_input(page, "input#phone", p["phone"], answers, "phone")
        if p.get("location"):
            await self._fill_input(
                page,
                "input#job_application_location, input[name*='location']",
                p["location"],
                answers,
                "location",
            )
        if p.get("linkedin_url"):
            await self._fill_input(
                page,
                "input[id*='urls'][id*='LinkedIn']",
                p["linkedin_url"],
                answers,
                "linkedin",
            )

    async def _fill_input(
        self, page: Page, selector: str, value: str, answers: dict, key: str
    ) -> None:
        if not value:
            return
        try:
            loc = page.locator(selector).first
            if await loc.count() == 0:
                return
            await loc.fill(value, timeout=3_000)
            answers[key] = value
        except Exception as e:
            log.warning("greenhouse.fill_skip", selector=selector, error=str(e))

    async def _upload_resume(self, page: Page, ctx: ApplyContext, answers: dict) -> None:
        if not ctx.resume_pdf_path:
            return
        for sel in [
            "input[type='file'][name*='resume']",
            "input#resume",
            "input[type='file'][id*='resume']",
        ]:
            try:
                loc = page.locator(sel).first
                if await loc.count():
                    await loc.set_input_files(ctx.resume_pdf_path, timeout=10_000)
                    answers["resume_file"] = ctx.resume_pdf_path
                    await asyncio.sleep(1.5)  # Greenhouse parses asynchronously
                    return
            except Exception as e:
                log.warning("greenhouse.resume_upload_skip", selector=sel, error=str(e))

    async def _upload_cover_letter(self, page: Page, ctx: ApplyContext, answers: dict) -> None:
        if not ctx.cover_letter_text:
            return
        # Greenhouse offers either a textarea or a file input for cover_letter.
        try:
            ta = page.locator(
                "textarea[name*='cover_letter'], textarea[id*='cover_letter']"
            ).first
            if await ta.count():
                await ta.fill(ctx.cover_letter_text, timeout=3_000)
                answers["cover_letter"] = ctx.cover_letter_text
                return
        except Exception:
            pass

    async def _answer_custom_questions(
        self, page: Page, ctx: ApplyContext, answers: dict
    ) -> list[dict]:
        """Iterate over Greenhouse's custom question fieldsets.

        Returns a list of low-confidence questions (paused).
        """
        s = get_settings()
        llm = get_llm()

        paused: list[dict] = []
        # Greenhouse wraps each custom q in a div with a label + an input/select/textarea.
        question_blocks = page.locator(
            "div.field--question, div[class*='question'], div.application_question"
        )
        count = await question_blocks.count()
        for i in range(count):
            block = question_blocks.nth(i)
            label_text = await self._read_label(block)
            if not label_text:
                continue
            field_type, options, max_length = await self._inspect_inputs(block)
            # Try a profile shortcut answer first.
            short = _profile_shortcut(label_text, ctx.profile)
            if short is not None:
                await self._set_answer(block, field_type, short)
                answers[label_text] = short
                continue

            # Otherwise, ask the LLM.
            qctx = QuestionContext(
                question=label_text,
                field_type=field_type,
                options=options,
                max_length=max_length,
                company=ctx.company,
                role_title=ctx.role_title,
                job_description=ctx.job_description,
            )
            result = llm.answer_question(qctx, ctx.profile)
            if result.confidence < s.llm_confidence_threshold:
                paused.append(
                    {
                        "question": label_text,
                        "field_type": field_type,
                        "options": options,
                        "llm_answer": result.answer,
                        "llm_confidence": result.confidence,
                        "llm_rationale": result.rationale,
                    }
                )
                continue
            await self._set_answer(block, field_type, result.answer)
            answers[label_text] = {
                "value": result.answer,
                "confidence": result.confidence,
                "source": "llm",
            }
        return paused

    async def _answer_eeo_questions(self, page: Page, ctx: ApplyContext, answers: dict) -> None:
        """Greenhouse EEO is always optional. Default to 'Decline to self-identify'
        unless the profile explicitly opts in."""
        eeo = (ctx.profile or {}).get("eeo_answers", {}) or {}
        for label, value in eeo.items():
            try:
                loc = page.locator(f"select[id*='{_label_token(label)}']").first
                if await loc.count():
                    await loc.select_option(label=value)
                    answers[f"eeo:{label}"] = value
            except Exception:
                continue

    async def _submit(self, page: Page) -> None:
        for sel in [
            "form#application_form button[type='submit']",
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.count() and await btn.is_visible():
                    await btn.click(timeout=10_000)
                    # Wait for either redirect or thank-you element.
                    try:
                        await page.wait_for_selector(
                            "text=/thank you|application received|we have received/i",
                            timeout=20_000,
                        )
                    except PWTimeout:
                        pass
                    return
            except Exception as e:
                log.warning("greenhouse.submit_skip", selector=sel, error=str(e))
        raise RuntimeError("Could not find a Greenhouse submit button.")

    async def _read_label(self, block: Locator) -> str:
        for sel in ["label", "legend", "div.label"]:
            loc = block.locator(sel).first
            if await loc.count():
                try:
                    return (await loc.inner_text(timeout=1_000)).strip()
                except Exception:
                    continue
        return ""

    async def _inspect_inputs(
        self, block: Locator
    ) -> tuple[str, list[str], int | None]:
        if await block.locator("textarea").count():
            ta = block.locator("textarea").first
            ml = await ta.get_attribute("maxlength")
            return "textarea", [], int(ml) if ml and ml.isdigit() else None
        if await block.locator("select").count():
            options: list[str] = []
            for opt in await block.locator("select option").all():
                t = (await opt.inner_text()).strip()
                if t:
                    options.append(t)
            return "select", options, None
        radios = block.locator("input[type='radio']")
        if await radios.count():
            options = []
            for r in await radios.all():
                rid = await r.get_attribute("id")
                if rid:
                    label = block.locator(f"label[for='{rid}']").first
                    if await label.count():
                        options.append((await label.inner_text()).strip())
            return "radio", options, None
        if await block.locator("input[type='checkbox']").count():
            return "checkbox", [], None
        if await block.locator("input[type='number']").count():
            return "number", [], None
        return "text", [], None

    async def _set_answer(self, block: Locator, field_type: str, value: str) -> None:
        if field_type == "textarea":
            await block.locator("textarea").first.fill(value)
        elif field_type == "select":
            try:
                await block.locator("select").first.select_option(label=value)
            except Exception:
                await block.locator("select").first.select_option(value=value)
        elif field_type == "radio":
            radios = await block.locator("input[type='radio']").all()
            for r in radios:
                rid = await r.get_attribute("id")
                if not rid:
                    continue
                label = block.locator(f"label[for='{rid}']").first
                if await label.count() and value.lower() in (
                    (await label.inner_text()).strip().lower()
                ):
                    await r.check()
                    return
        elif field_type == "checkbox":
            cb = block.locator("input[type='checkbox']").first
            should_check = value.strip().lower() in ("yes", "true", "1", "on")
            if should_check:
                await cb.check()
            else:
                await cb.uncheck()
        else:
            await block.locator("input").first.fill(value)


# --- helpers ---


def _split_name(full: str) -> tuple[str, str]:
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


_PROFILE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:authorized|legally allowed) to work\b", re.I), "work_authorization"),
    (re.compile(r"\bsponsorship\b", re.I), "requires_sponsorship"),
    (re.compile(r"\b(?:relocate|relocation)\b", re.I), "willing_to_relocate"),
    (re.compile(r"\b(?:security )?clearance\b", re.I), "security_clearance"),
    (re.compile(r"\bsalary (?:expectation|range|requirement)\b", re.I), "salary_expectation"),
    (re.compile(r"\byears? of experience with (.+)", re.I), "years_skill"),
]


def _profile_shortcut(question: str, profile: dict) -> str | None:
    """Map common questions directly to profile fields, no LLM round-trip."""
    if not profile:
        return None
    for pattern, key in _PROFILE_PATTERNS:
        m = pattern.search(question)
        if not m:
            continue
        if key == "work_authorization":
            return profile.get("work_authorization") or "Yes"
        if key == "requires_sponsorship":
            return "Yes" if profile.get("requires_sponsorship") else "No"
        if key == "willing_to_relocate":
            return "Yes" if profile.get("willing_to_relocate") else "No"
        if key == "security_clearance":
            return profile.get("security_clearance") or "None"
        if key == "salary_expectation":
            lo, hi = profile.get("salary_min"), profile.get("salary_max")
            if lo and hi:
                return f"${lo:,} - ${hi:,}"
        if key == "years_skill":
            skill = m.group(1).strip().rstrip("?.").lower()
            skills = profile.get("skills", {}) or {}
            for sk_name, years in skills.items():
                if sk_name.lower() in skill or skill in sk_name.lower():
                    return str(years)
    # standard_answers exact-ish match
    for sa_key, sa_val in (profile.get("standard_answers") or {}).items():
        if sa_key.lower() in question.lower():
            return str(sa_val)
    return None


def _label_token(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
