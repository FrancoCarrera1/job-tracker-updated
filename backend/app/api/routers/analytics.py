from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas import AnalyticsOut
from app.db import get_db
from app.models import (
    Application,
    ApplicationMethod,
    ApplicationStatus,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
def analytics(db: Session = Depends(get_db)):
    apps = db.query(Application).all()

    totals: dict[str, int] = defaultdict(int)
    for a in apps:
        totals[a.status.value] += 1

    total_applied = sum(
        totals[k]
        for k in (
            "applied",
            "screening",
            "interview",
            "offer",
            "rejected",
            "ghosted",
        )
    ) or 1
    responded = totals["screening"] + totals["interview"] + totals["offer"] + totals["rejected"]
    response_rate = responded / total_applied
    interview_conversion = (totals["interview"] + totals["offer"]) / total_applied

    response_deltas: list[float] = []
    for a in apps:
        if a.date_applied and a.last_response_at:
            response_deltas.append((a.last_response_at - a.date_applied).total_seconds() / 86400.0)

    median_t = median(response_deltas) if response_deltas else None

    apps_per_week = []
    twelve_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=12)
    week_q = (
        db.query(
            func.date_trunc("week", Application.date_applied).label("week"),
            func.count(Application.id),
        )
        .filter(Application.date_applied != None, Application.date_applied >= twelve_weeks_ago)  # noqa: E711
        .group_by("week")
        .order_by("week")
        .all()
    )
    for week, count in week_q:
        apps_per_week.append({"week": week.isoformat(), "count": int(count)})

    auto_vs_manual: dict[str, dict[str, int]] = {
        "auto": {"applied": 0, "interview": 0, "offer": 0, "rejected": 0, "ghosted": 0},
        "manual": {"applied": 0, "interview": 0, "offer": 0, "rejected": 0, "ghosted": 0},
    }
    for a in apps:
        bucket = "auto" if a.method == ApplicationMethod.AUTO else "manual"
        if a.status in (
            ApplicationStatus.APPLIED,
            ApplicationStatus.SCREENING,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.GHOSTED,
        ):
            key = a.status.value
            if a.status == ApplicationStatus.SCREENING:
                key = "applied"
            auto_vs_manual[bucket][key] = auto_vs_manual[bucket].get(key, 0) + 1

    return AnalyticsOut(
        totals_by_status=dict(totals),
        response_rate=round(response_rate, 3),
        interview_conversion=round(interview_conversion, 3),
        median_time_to_response_days=round(median_t, 2) if median_t is not None else None,
        apps_per_week=apps_per_week,
        auto_vs_manual_success=auto_vs_manual,
    )
