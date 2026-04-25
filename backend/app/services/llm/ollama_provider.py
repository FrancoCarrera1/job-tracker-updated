from __future__ import annotations

from typing import Any

import httpx

from app.services.llm.anthropic_provider import _parse_answer
from app.services.llm.base import (
    RESUME_TAILOR_SYSTEM,
    AnswerResult,
    QuestionContext,
    build_answer_prompt,
)


class OllamaProvider:
    """Local inference via Ollama. Best privacy posture — no PII leaves the host."""

    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:70b") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _generate(self, system: str | None, prompt: str, fmt: str | None = None) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if fmt:
            payload["format"] = fmt
        with httpx.Client(timeout=120.0) as client:
            r = client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()
            return r.json().get("response", "")

    def answer_question(self, ctx: QuestionContext, profile: dict[str, Any]) -> AnswerResult:
        prompt = build_answer_prompt(ctx, profile)
        text = self._generate(system="You output strict JSON only.", prompt=prompt, fmt="json")
        return _parse_answer(text)

    def tailor_resume_summary(
        self,
        base_summary: str,
        profile: dict[str, Any],
        job_description: str,
        max_chars: int = 800,
    ) -> str:
        prompt = (
            f"# Original summary\n{base_summary}\n\n"
            f"# Profile facts\n{profile}\n\n"
            f"# Job description\n{job_description}\n\n"
            f"Return only the rewritten summary, max {max_chars} chars."
        )
        return self._generate(system=RESUME_TAILOR_SYSTEM, prompt=prompt).strip()
