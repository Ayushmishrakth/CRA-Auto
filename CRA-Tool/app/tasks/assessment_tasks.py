"""
Assessment runtime Celery tasks.
"""

import asyncio

from app.core.celery_app import celery_app
from app.services.runtime_assessment_service import run_assessment_job


@celery_app.task(
    name="assessment.run",
    bind=True,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_assessment_task(self, job_id: str) -> dict:
    return asyncio.run(run_assessment_job(job_id, worker_id=self.request.id))
