from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analytics, applications, auth, automation, profile
from app.config import get_settings


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )


_configure_logging()
settings = get_settings()

app = FastAPI(title="Job Tracker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.dashboard_base_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router)
app.include_router(profile.router)
app.include_router(auth.router)
app.include_router(automation.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"service": "jobtracker", "version": "0.1.0"}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz():
    from app.db import engine

    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
