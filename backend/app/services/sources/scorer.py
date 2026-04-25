"""Score a discovered posting against the candidate profile.

Returns a 0..1 score and a breakdown dict for explainability.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from app.models import Profile
from app.services.sources.base import DiscoveredPosting

# Tunable weights, must sum to 1.
WEIGHTS = {
    "title": 0.25,
    "skills": 0.30,
    "salary": 0.15,
    "location": 0.15,
    "clearance": 0.15,
}

DEVOPS_TITLE_TOKENS = [
    "devops",
    "site reliability",
    "sre",
    "platform",
    "infrastructure",
    "cloud engineer",
    "kubernetes",
    "linux",
    "systems engineer",
]


def score_posting(posting: DiscoveredPosting, profile: Profile) -> tuple[float, dict]:
    breakdown: dict = {}

    # Title match — fuzzy against role tokens
    title_lc = (posting.role_title or "").lower()
    title_score = 0.0
    for token in DEVOPS_TITLE_TOKENS:
        title_score = max(title_score, fuzz.partial_ratio(token, title_lc) / 100.0)
    breakdown["title"] = round(title_score, 2)

    # Skills overlap
    profile_skills = {s.lower() for s in (profile.skills or {}).keys()}
    posting_skills = {s.lower() for s in (posting.skills or [])}
    skill_score = (
        len(profile_skills & posting_skills) / max(len(posting_skills), 1)
        if posting_skills
        else 0.5  # no skills extracted is neutral
    )
    breakdown["skills"] = round(skill_score, 2)
    breakdown["skills_overlap"] = sorted(profile_skills & posting_skills)

    # Salary fit
    salary_score = _salary_score(posting, profile)
    breakdown["salary"] = round(salary_score, 2)

    # Location fit
    location_score = _location_score(posting, profile)
    breakdown["location"] = round(location_score, 2)

    # Clearance: posting requires clearance & user has comparable level -> +; else neutral
    clearance_score = _clearance_score(posting, profile)
    breakdown["clearance"] = round(clearance_score, 2)

    total = sum(WEIGHTS[k] * breakdown[k] for k in WEIGHTS)
    breakdown["total"] = round(total, 3)
    return total, breakdown


def _salary_score(posting: DiscoveredPosting, profile: Profile) -> float:
    if posting.salary_min is None or posting.salary_max is None:
        return 0.5
    p_min = profile.salary_min or 0
    p_max = profile.salary_max or 999_999
    midpoint = (posting.salary_min + posting.salary_max) / 2
    if midpoint < p_min * 0.9:
        return 0.0
    if midpoint > p_max * 1.05:
        return 0.7  # overshoots can be ok
    if p_min <= midpoint <= p_max:
        return 1.0
    return 0.4


def _location_score(posting: DiscoveredPosting, profile: Profile) -> float:
    p_loc = (profile.location or "").lower()
    posting_loc = (posting.location or "").lower()
    if posting.location_type == "remote":
        return 1.0
    if not posting_loc:
        return 0.5
    if p_loc and (p_loc in posting_loc or posting_loc in p_loc):
        return 1.0
    # Same state/region
    if p_loc and any(tok in posting_loc for tok in p_loc.split(",")):
        return 0.7
    if profile.willing_to_relocate:
        return 0.6
    return 0.2


_CLEARANCE_RANK = {
    None: 0,
    "": 0,
    "public trust": 1,
    "t4": 1,
    "secret": 2,
    "top secret": 3,
    "ts/sci": 4,
}


def _clearance_score(posting: DiscoveredPosting, profile: Profile) -> float:
    if not posting.requires_clearance:
        return 1.0  # no clearance needed -> full score
    user_level = (profile.security_clearance or "").lower()
    posting_level = (posting.clearance_level or "").lower()
    user_rank = _CLEARANCE_RANK.get(user_level, 0)
    posting_rank = _CLEARANCE_RANK.get(posting_level, 1)
    if user_rank == 0:
        return 0.0
    if user_rank >= posting_rank:
        return 1.0
    return 0.3
