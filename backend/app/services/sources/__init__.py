"""Job source plugins. Each source returns a list of normalized JobPosting dicts."""

from app.services.sources.base import DiscoveredPosting, JobSourcePlugin
from app.services.sources.registry import get_source_class, list_sources, register_source
from app.services.sources import greenhouse_board  # noqa: F401

__all__ = [
    "DiscoveredPosting",
    "JobSourcePlugin",
    "get_source_class",
    "list_sources",
    "register_source",
]
