from __future__ import annotations

import json
from typing import Any

import anthropic

from app.services.llm.base import (
    RESUME_TAILOR_SYSTEM,
    AnswerResult,
    QuestionContext,
    build_answer_prompt,
    scrub_pii,
)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def answer_question(self, ctx: QuestionContext, profile: dict[str, Any]) -> AnswerResult:
        prompt = build_answer_prompt(ctx, profile)
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        return _parse_answer(text)

    def tailor_resume_summary(
        self,
        base_summary: str,
        profile: dict[str, Any],
        job_description: str,
        max_chars: int = 800,
    ) -> str:
        scrubbed_jd = scrub_pii(job_description)
        prompt = (
            f"# Original summary\n{base_summary}\n\n"
            f"# Profile facts (only re-use these)\n{profile}\n\n"
            f"# Job description\n{scrubbed_jd}\n\n"
            f"Return ONLY the rewritten summary, no preface. Max {max_chars} characters."
        )
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=RESUME_TAILOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if block.type == "text").strip()


def _parse_answer(text: str) -> AnswerResult:
    text = text.strip()
    # tolerate ```json fences
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    try:
        parsed = json.loads(text)
        confidence = float(parsed.get("confidence", 0.0))
        return AnswerResult(
            answer=str(parsed.get("answer", "")),
            confidence=confidence,
            rationale=str(parsed.get("rationale", "")),
            needs_review=confidence < 0.75,
        )
    except (json.JSONDecodeError, ValueError, KeyError):
        return AnswerResult(answer=text, confidence=0.0, rationale="parse_failed", needs_review=True)
