import os
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "job_portal_automation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.scrape_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_concurrency=4,
)

# Automated Celery Beat Schedule
celery_app.conf.beat_schedule = {
    "scrape-private-sources-hourly": {
        "task": "app.tasks.scrape_tasks.scheduled_scrape_private_sources",
        "schedule": crontab(minute="0"),  # Every hour
    },
    "scrape-government-sources-two-hours": {
        "task": "app.tasks.scrape_tasks.scheduled_scrape_govt_sources",
        "schedule": crontab(minute="0", hour="*/2"),  # Every 2 hours
    },
    "verify-job-expiry-daily": {
        "task": "app.tasks.scrape_tasks.verify_job_expiry_task",
        "schedule": crontab(minute="0", hour="0"),  # Daily at midnight
    },
}
