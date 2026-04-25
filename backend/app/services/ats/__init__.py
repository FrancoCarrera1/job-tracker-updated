"""ATS handler package.

Each handler subclasses ATSHandler and registers itself via @register("name").
Handlers are looked up by job_posting.ats and instantiated per run.
"""

from app.services.ats.base import (
    ATSHandler,
    ApplyContext,
    ApplyOutcome,
    ApplyResult,
    PausedException,
)
from app.services.ats.registry import get_handler_class, list_handlers, register
from app.services.ats import greenhouse  # noqa: F401  - register handler
from app.services.ats import lever  # noqa: F401
from app.services.ats import workday  # noqa: F401
from app.services.ats import ashby  # noqa: F401
from app.services.ats import icims  # noqa: F401
from app.services.ats import linkedin  # noqa: F401
from app.services.ats import indeed  # noqa: F401

__all__ = [
    "ATSHandler",
    "ApplyContext",
    "ApplyOutcome",
    "ApplyResult",
    "PausedException",
    "get_handler_class",
    "list_handlers",
    "register",
]
