"""
CRA Celery application.

Worker:
    celery -A app.core.celery_app.celery_app worker --loglevel=info

Beat (future-ready):
    celery -A app.core.celery_app.celery_app beat --loglevel=info
"""

from celery import Celery

from app.core.config import settings
from app.db import base as _model_registry  # noqa: F401


celery_app = Celery(
    "cra_runtime",
    broker=settings.resolved_celery_broker_url,
    backend=settings.resolved_celery_result_backend,
    include=["app.tasks.assessment_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings.celery_task_time_limit_seconds,
    task_soft_time_limit=settings.celery_task_soft_time_limit_seconds,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
        "retry_on_timeout": False,
        "max_retries": 1,
    },
    task_publish_retry=True,
    task_publish_retry_policy={
        "max_retries": 1,
        "interval_start": 0,
        "interval_step": 0.2,
        "interval_max": 0.5,
    },
    task_always_eager=settings.celery_task_always_eager,
)
