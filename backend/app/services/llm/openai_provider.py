from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.services.llm.anthropic_provider import _parse_answer
from app.services.llm.base import (
    RESUME_TAILOR_SYSTEM,
    AnswerResult,
    QuestionContext,
    build_answer_prompt,
    scrub_pii,
)


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def answer_question(self, ctx: QuestionContext, profile: dict[str, Any]) -> AnswerResult:
        prompt = build_answer_prompt(ctx, profile)
        resp = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You output strict JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        return _parse_answer(resp.choices[0].message.content or "")

    def tailor_resume_summary(
        self,
        base_summary: str,
        profile: dict[str, Any],
        job_description: str,
        max_chars: int = 800,
    ) -> str:
        scrubbed_jd = scrub_pii(job_description)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RESUME_TAILOR_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"# Original summary\n{base_summary}\n\n"
                        f"# Profile facts\n{profile}\n\n"
                        f"# Job description\n{scrubbed_jd}\n\n"
                        f"Return only the rewritten summary, max {max_chars} chars."
                    ),
                },
            ],
        )
        return (resp.choices[0].message.content or "").strip()
