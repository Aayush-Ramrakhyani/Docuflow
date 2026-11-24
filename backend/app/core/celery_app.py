"""Celery application configuration."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "docuflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.document_processor"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,         # Ack after completion, not on receipt (safer for retries)
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,    # 5 min soft limit — raises SoftTimeLimitExceeded
    task_time_limit=360,         # 6 min hard limit — kills the worker process
    result_expires=86400,        # Keep results 1 day
    # Restart worker process every 50 tasks to prevent PyMuPDF + AI memory accumulation
    worker_max_tasks_per_child=50,
)
