from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class QuestionContext:
    """The information an LLM needs to answer a single application question."""

    question: str
    field_type: str  # "text", "textarea", "select", "checkbox", "radio", "number"
    options: list[str] = field(default_factory=list)
    max_length: int | None = None
    company: str = ""
    role_title: str = ""
    job_description: str = ""


@dataclass
class AnswerResult:
    """An LLM's answer with self-reported confidence and rationale."""

    answer: str
    confidence: float  # 0.0 - 1.0
    rationale: str = ""
    needs_review: bool = False


class LLMProvider(Protocol):
    """All providers expose the same two methods. Add ones if you need them."""

    name: str

    def answer_question(
        self,
        ctx: QuestionContext,
        profile: dict[str, Any],
    ) -> AnswerResult:
        """Answer a single application question using the master profile as ground truth."""
        ...

    def tailor_resume_summary(
        self,
        base_summary: str,
        profile: dict[str, Any],
        job_description: str,
        max_chars: int = 800,
    ) -> str:
        """Lightly tailor a resume summary paragraph for a specific posting.

        MUST NOT fabricate skills or experience. Only re-order/re-emphasize what
        is already in `profile`. Implementations should enforce this in the prompt
        and validate output.
        """
        ...


# --- PII scrubbing ---

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# Common street/city addresses (very loose)
_ADDR_RE = re.compile(r"\b\d{1,6}\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:St|Ave|Rd|Blvd|Dr|Ln|Way)\b")


def scrub_pii(text: str) -> str:
    """Replace email/phone/SSN/street with redaction tokens.

    Used before sending profile bits to a remote LLM. Use `bypass_scrub=True` only
    when the user has whitelisted a provider (e.g., a local Ollama instance).
    """
    if not text:
        return text
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    text = _SSN_RE.sub("[SSN]", text)
    text = _ADDR_RE.sub("[ADDRESS]", text)
    return text


def build_answer_prompt(ctx: QuestionContext, profile: dict[str, Any]) -> str:
    """Build the deterministic prompt every provider uses.

    Centralized so we can A/B prompts without touching provider-specific code.
    """
    profile_blob = {
        "summary": profile.get("summary", ""),
        "skills": profile.get("skills", {}),
        "certifications": profile.get("certifications", []),
        "work_history": profile.get("work_history", []),
        "education": profile.get("education", []),
        "work_authorization": profile.get("work_authorization"),
        "requires_sponsorship": profile.get("requires_sponsorship"),
        "willing_to_relocate": profile.get("willing_to_relocate"),
        "security_clearance": profile.get("security_clearance"),
        "salary_min": profile.get("salary_min"),
        "salary_max": profile.get("salary_max"),
        "standard_answers": profile.get("standard_answers", {}),
    }

    options_block = ""
    if ctx.options:
        options_block = (
            f"\nThe form expects one of these options exactly: {ctx.options}"
        )

    length_block = ""
    if ctx.max_length:
        length_block = f"\nResponse MUST be <= {ctx.max_length} characters."

    return f"""You are filling out a job application on behalf of a candidate.
You MUST answer using ONLY facts present in the candidate's profile below.
If the profile does not contain enough information to answer truthfully, set
confidence to a low value and explain in rationale what is missing.
NEVER fabricate years of experience, certifications, or employers.

# Candidate profile
{profile_blob}

# Question
Field type: {ctx.field_type}
Company: {ctx.company}
Role: {ctx.role_title}
Question: {ctx.question}{options_block}{length_block}

Reply as a JSON object with these keys exactly:
{{"answer": str, "confidence": float between 0 and 1, "rationale": str}}
"""


RESUME_TAILOR_SYSTEM = """You re-emphasize an existing resume summary paragraph for a specific job.
You MUST NOT add skills, certifications, or experience that are not already in the candidate's profile.
You MAY: re-order phrases, swap close synonyms (e.g. K8s -> Kubernetes), trim irrelevant details.
You MAY NOT: claim new years of experience, add new tools, change quantitative claims.
"""
