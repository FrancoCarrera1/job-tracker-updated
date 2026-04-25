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

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        client_kwargs = {
            # Local OpenAI-compatible servers often ignore auth but the SDK still
            # expects a token-shaped value.
            "api_key": api_key or "local-inference",
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = OpenAI(**client_kwargs)
        self.model = model

    def answer_question(self, ctx: QuestionContext, profile: dict[str, Any]) -> AnswerResult:
        prompt = build_answer_prompt(ctx, profile)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You output strict JSON only."},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            resp = self.client.chat.completions.create(
                response_format={"type": "json_object"},
                **payload,
            )
        except Exception:
            if not self.base_url:
                raise
            resp = self.client.chat.completions.create(
                **payload,
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
