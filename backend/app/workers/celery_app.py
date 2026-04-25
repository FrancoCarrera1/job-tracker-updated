from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

_s = get_settings()

celery_app = Celery(
    "jobtracker",
    broker=_s.celery_broker_url,
    backend=_s.celery_result_backend,
    include=[
        "app.workers.tasks",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_max_tasks_per_child=50,
    timezone="UTC",
    beat_schedule={
        "scan-inbox-every-15-min": {
            "task": "app.workers.tasks.scan_email_inbox",
            "schedule": crontab(minute="*/15"),
        },
        "poll-sources-hourly": {
            "task": "app.workers.tasks.poll_sources",
            "schedule": crontab(minute="0", hour="*"),
        },
        "drain-apply-queue-every-3-min": {
            "task": "app.workers.tasks.drain_apply_queue",
            "schedule": crontab(minute="*/3"),
        },
        "sweep-stale-applications-daily": {
            "task": "app.workers.tasks.sweep_stale_applications",
            "schedule": crontab(minute="0", hour="9"),
        },
    },
)
