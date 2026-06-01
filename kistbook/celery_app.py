from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from kistbook.core.config import settings

celery_app = Celery(
    "kistbook",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["kistbook.engine.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "scan_due_reminders": {
        "task": "kistbook.engine.tasks.run_daily_scan",
        "schedule": crontab(hour=1, minute=0),
    },
}
