from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DiscoveredPosting:
    source: str
    source_id: str
    company: str
    role_title: str
    job_url: str
    ats: str | None = None
    location: str | None = None
    location_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    requires_clearance: bool = False
    clearance_level: str | None = None
    description: str = ""
    skills: list[str] = field(default_factory=list)


class JobSourcePlugin(ABC):
    source_kind: str = ""

    @abstractmethod
    def fetch(self, identifier: str, config: dict) -> list[DiscoveredPosting]:
        ...
