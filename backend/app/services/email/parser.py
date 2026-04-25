"""Email classification + status detection.

Two-pass approach:

1.  Domain match: the sender domain tells us which ATS (greenhouse.io, lever.co,
    myworkday.com, icims.com, ashbyhq.com, smartrecruiters.com, taleo.net,
    bamboohr.com). A domain match alone classifies a thread as "applied" by
    default. ATS senders are robotic; subject + body keywords refine it.

2.  Keyword scan: if the domain doesn't match a known ATS, we still check the
    subject + first 500 chars of the body for high-signal keywords.

Classification labels:
    - applied              "Thanks for applying", confirmation receipt
    - interview            "schedule a call", "next step", "interview"
    - rejection            "moved forward with other candidates", "not moving forward"
    - offer                "offer letter", "we are pleased to extend"
    - recruiter_outreach   inbound from recruiter, no prior application
    - other                couldn't classify

Each rule has a weight; final confidence is normalized.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

# (domain_pattern, ats_name)
ATS_DOMAINS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?greenhouse\.io$", re.I), "greenhouse"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?lever\.co$", re.I), "lever"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?myworkday(?:jobs)?\.com$", re.I), "workday"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?workday\.com$", re.I), "workday"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?icims\.com$", re.I), "icims"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?ashbyhq\.com$", re.I), "ashby"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?smartrecruiters\.com$", re.I), "smartrecruiters"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?taleo\.net$", re.I), "taleo"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?bamboohr\.com$", re.I), "bamboohr"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?jobvite\.com$", re.I), "jobvite"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?breezy\.hr$", re.I), "breezy"),
    (re.compile(r"(?:^|@)(?:[\w-]+\.)?recruitee\.com$", re.I), "recruitee"),
]


@dataclass
class Rule:
    label: str
    pattern: re.Pattern[str]
    weight: float
    fields: tuple[str, ...]  # which haystacks to scan: "subject", "body"


# Order matters only for tie-breaks; weights determine winners
RULES: list[Rule] = [
    # OFFER
    Rule("offer", re.compile(r"\boffer letter\b", re.I), 0.95, ("subject", "body")),
    Rule("offer", re.compile(r"\bpleased to (?:extend|offer)\b", re.I), 0.9, ("body",)),
    Rule("offer", re.compile(r"\bcompensation package\b", re.I), 0.5, ("body",)),

    # REJECTION
    Rule("rejection", re.compile(r"\b(?:moving forward with other|other candidates)\b", re.I), 0.95, ("body",)),
    Rule("rejection", re.compile(r"\bnot (?:moving forward|selected|able to (?:move|proceed))\b", re.I), 0.9, ("body",)),
    Rule("rejection", re.compile(r"\bunfortunately\b.*\b(?:role|position|application)\b", re.I), 0.7, ("body",)),
    Rule("rejection", re.compile(r"\bdecided to pursue\b", re.I), 0.85, ("body",)),
    Rule("rejection", re.compile(r"\bwill not be (?:proceeding|continuing)\b", re.I), 0.9, ("body",)),
    Rule("rejection", re.compile(r"\bregret(?:fully)? (?:to )?(?:inform|let)\b", re.I), 0.85, ("body",)),

    # INTERVIEW
    Rule("interview", re.compile(r"\b(?:phone|video|onsite|technical) (?:interview|screen)\b", re.I), 0.95, ("subject", "body")),
    Rule("interview", re.compile(r"\bschedule (?:a )?(?:call|chat|interview|conversation)\b", re.I), 0.9, ("subject", "body")),
    Rule("interview", re.compile(r"\bnext (?:step|round|stage)\b", re.I), 0.7, ("subject", "body")),
    Rule("interview", re.compile(r"\b(?:would|like) to (?:speak|chat|talk|meet)\b", re.I), 0.6, ("body",)),
    Rule("interview", re.compile(r"\b(?:availability|available times?)\b", re.I), 0.5, ("subject", "body")),
    Rule("interview", re.compile(r"\bcalendly\.com|\bcal\.com\b", re.I), 0.7, ("body",)),

    # APPLIED (ATS receipt)
    Rule("applied", re.compile(r"\bthank(?:s| you) for applying\b", re.I), 0.95, ("subject", "body")),
    Rule("applied", re.compile(r"\bapplication (?:was )?(?:received|submitted)\b", re.I), 0.9, ("subject", "body")),
    Rule("applied", re.compile(r"\bwe(?:'ve| have) received your application\b", re.I), 0.95, ("body",)),
    Rule("applied", re.compile(r"\byour application (?:to|for)\b", re.I), 0.6, ("subject",)),

    # RECRUITER OUTREACH (cold)
    Rule("recruiter_outreach", re.compile(r"\b(?:came across|stumbled upon|reaching out (?:about|regarding)) your (?:profile|background|linkedin)\b", re.I), 0.9, ("body",)),
    Rule("recruiter_outreach", re.compile(r"\b(?:opportunity|opening|role) (?:at|with) (?:my (?:client|company)|us)\b", re.I), 0.7, ("body",)),
    Rule("recruiter_outreach", re.compile(r"\bI(?:'m| am) a (?:senior )?(?:technical )?recruiter\b", re.I), 0.85, ("body",)),
]


@dataclass
class Classification:
    label: str
    confidence: float
    matched: dict[str, list[str]]


def detect_ats(sender: str) -> str | None:
    domain = _extract_domain(sender)
    if not domain:
        return None
    for pattern, ats in ATS_DOMAINS:
        if pattern.search(domain):
            return ats
    return None


def _extract_domain(sender: str) -> str:
    m = re.search(r"@([\w.-]+)", sender)
    return m.group(1).lower() if m else sender.lower()


def classify(subject: str, body_text: str, sender: str) -> Classification:
    """Return the label with the highest aggregate weight."""
    body_head = (body_text or "")[:4000]
    haystacks = {"subject": subject or "", "body": body_head}
    matched: dict[str, list[str]] = {}
    scores: dict[str, float] = {}

    for rule in RULES:
        for field in rule.fields:
            if rule.pattern.search(haystacks[field]):
                scores[rule.label] = scores.get(rule.label, 0.0) + rule.weight
                matched.setdefault(rule.label, []).append(rule.pattern.pattern)
                break  # don't double-count a rule across fields

    ats = detect_ats(sender)
    # If the email is from an ATS sender but no rule fired, treat as 'applied' weakly.
    if ats and not scores:
        scores["applied"] = 0.4
        matched["applied"] = [f"ats:{ats}"]

    if not scores:
        return Classification(label="other", confidence=0.0, matched={})

    label, raw = max(scores.items(), key=lambda kv: kv[1])
    confidence = min(raw, 1.0)
    return Classification(label=label, confidence=confidence, matched=matched)


# --- Mapping classification -> Application status update ---

CLASSIFICATION_TO_STATUS: dict[str, str] = {
    "applied": "applied",
    "interview": "interview",
    "rejection": "rejected",
    "offer": "offer",
    # recruiter_outreach and 'other' don't move status on their own
}


def status_for(classification: str) -> str | None:
    return CLASSIFICATION_TO_STATUS.get(classification)


# --- Company / role extraction ---

_ROLE_HINT = re.compile(
    r"(?:application (?:to|for)|interview for|regarding (?:your )?application for|opening for|the role of)\s+"
    r"(?:the\s+)?([A-Z][\w/&\-,. ]{2,80})",
    re.I,
)


def extract_company_role(subject: str, body_text: str, sender: str) -> tuple[str | None, str | None]:
    """Best-effort. Returns (company, role)."""
    company = _extract_company(sender, body_text)
    role = _extract_role(subject, body_text)
    return company, role


def _extract_company(sender: str, body_text: str) -> str | None:
    # 1) From "Recruiting <recruiting@acme.com>" the visible name often is "Acme Recruiting"
    name_match = re.match(r"^\s*\"?([^<\"]+?)\"?\s*<", sender)
    if name_match:
        candidate = name_match.group(1).strip()
        candidate = re.sub(r"\b(recruiting|talent|careers|noreply|no-reply|jobs|hr)\b", "", candidate, flags=re.I).strip()
        if candidate and len(candidate) > 1:
            return candidate

    # 2) From the "@<company>.com" domain when it isn't a known ATS
    domain = _extract_domain(sender)
    if domain and not any(p.search(domain) for p, _ in ATS_DOMAINS):
        head = domain.split(".")[0]
        if head not in ("mail", "noreply", "no-reply"):
            return head.replace("-", " ").title()

    # 3) From body "Thanks for applying to Acme!"
    m = re.search(r"applying (?:to|for a (?:role|position) at) ([A-Z][\w&\-. ]{2,40})", body_text or "")
    if m:
        return m.group(1).strip().rstrip("!.,")
    return None


def _extract_role(subject: str, body_text: str) -> str | None:
    for hay in (subject or "", (body_text or "")[:1500]):
        m = _ROLE_HINT.search(hay)
        if m:
            return m.group(1).strip().rstrip(".,!")
    return None


# --- Dedupe ---


def is_likely_duplicate(
    company: str,
    role: str,
    existing: Iterable[tuple[str, str]],
    similarity_threshold: int = 85,
) -> bool:
    from rapidfuzz import fuzz

    company = (company or "").strip().lower()
    role = (role or "").strip().lower()
    for existing_company, existing_role in existing:
        ec = (existing_company or "").strip().lower()
        er = (existing_role or "").strip().lower()
        if not ec or not er:
            continue
        if fuzz.token_set_ratio(company, ec) >= similarity_threshold and fuzz.token_set_ratio(role, er) >= similarity_threshold:
            return True
    return False
