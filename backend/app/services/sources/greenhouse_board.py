"""Greenhouse public board scraper.

Each company on Greenhouse exposes a JSON board endpoint:

    https://boards-api.greenhouse.io/v1/boards/<company>/jobs?content=true

This is officially documented and ToS-permitted, no scraping. Each job has:
    {
      "id": 1234567,
      "title": "Site Reliability Engineer",
      "absolute_url": "https://boards.greenhouse.io/<company>/jobs/1234567",
      "location": {"name": "Remote, US"},
      "content": "<HTML description>",
      "metadata": [{"name": "Salary", "value": "$140k-$180k"}, ...]
    }
"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from app.services.sources.base import DiscoveredPosting, JobSourcePlugin
from app.services.sources.registry import register_source

log = structlog.get_logger()


@register_source("greenhouse_board")
class GreenhouseBoardSource(JobSourcePlugin):
    def fetch(self, identifier: str, config: dict) -> list[DiscoveredPosting]:
        board_id = _normalize_identifier(identifier)
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs?content=true"
        with httpx.Client(timeout=15.0, headers={"User-Agent": "jobtracker/1.0"}) as client:
            r = client.get(url)
        if r.status_code != 200:
            log.warning(
                "source.greenhouse.error",
                status=r.status_code,
                company=identifier,
                board_id=board_id,
            )
            return []
        data = r.json()
        out: list[DiscoveredPosting] = []
        for job in data.get("jobs", []):
            description = _strip_html(unescape(job.get("content") or ""))
            location = (job.get("location") or {}).get("name", "")
            location_type = _location_type(location)
            salary_min, salary_max = _extract_salary(description, job.get("metadata") or [])
            out.append(
                DiscoveredPosting(
                    source="greenhouse_board",
                    source_id=str(job.get("id")),
                    company=board_id,
                    role_title=job.get("title", ""),
                    job_url=job.get("absolute_url", ""),
                    ats="greenhouse",
                    location=location,
                    location_type=location_type,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    requires_clearance=_requires_clearance(description),
                    clearance_level=_clearance_level(description),
                    description=description,
                    skills=_extract_skills(description),
                )
            )
        return out


# --- helpers ---

_SKILL_VOCAB = [
    "kubernetes", "docker", "terraform", "ansible", "aws", "azure", "gcp",
    "python", "go", "rust", "java", "typescript", "javascript",
    "linux", "rhel", "ubuntu", "ci/cd", "jenkins", "gitlab", "github actions",
    "prometheus", "grafana", "datadog", "splunk",
    "openshift", "helm", "argocd", "istio",
    "postgres", "postgresql", "mysql", "redis", "kafka",
    "rhcsa", "rhce", "ckad", "cka", "security+", "aws saa", "aws sa",
]


def _normalize_identifier(identifier: str) -> str:
    raw = (identifier or "").strip()
    if not raw:
        return raw

    trimmed = raw.split("?", 1)[0].split("#", 1)[0]
    if "://" in trimmed:
        parsed = urlparse(trimmed)
        parts = [part for part in parsed.path.split("/") if part]
        if parts:
            return parts[0]
        return parsed.netloc

    parts = [part for part in trimmed.strip("/").split("/") if part]
    if not parts:
        return ""
    if len(parts) >= 2 and "." in parts[0]:
        return parts[1]
    return parts[0]


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text("\n", strip=True)


def _location_type(location: str) -> str | None:
    lc = location.lower()
    if "remote" in lc:
        return "remote"
    if "hybrid" in lc:
        return "hybrid"
    if location:
        return "onsite"
    return None


def _extract_salary(description: str, metadata: list[dict]) -> tuple[int | None, int | None]:
    text = description + " " + " ".join(str(m.get("value", "")) for m in metadata)
    m = re.search(r"\$([\d.]+)k?\s*(?:-|to|—|–)\s*\$?([\d.]+)k", text, re.I)
    if m:
        lo, hi = m.group(1), m.group(2)
        return int(float(lo) * 1000), int(float(hi) * 1000)
    m2 = re.search(r"\$(\d{2,3}),?(\d{3})\s*(?:-|to)\s*\$?(\d{2,3}),?(\d{3})", text)
    if m2:
        lo = int(m2.group(1) + m2.group(2))
        hi = int(m2.group(3) + m2.group(4))
        return lo, hi
    return None, None


def _requires_clearance(description: str) -> bool:
    return bool(
        re.search(
            r"\b(?:active )?(?:security )?clearance(?:\s+(?:required|preferred))?\b",
            description,
            re.I,
        )
        or re.search(r"\b(?:public trust|secret|top secret|ts/sci|t4)\b", description, re.I)
    )


def _clearance_level(description: str) -> str | None:
    text = description.lower()
    for level in ("ts/sci", "top secret", "secret", "public trust", "t4"):
        if level in text:
            return level
    return None


def _extract_skills(description: str) -> list[str]:
    text = description.lower()
    return [s for s in _SKILL_VOCAB if s in text]
