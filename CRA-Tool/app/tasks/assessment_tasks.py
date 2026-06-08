"""
Assessment runtime Celery tasks.
"""

import asyncio
import logging
import sys

from app.core.celery_app import celery_app
from app.services.runtime_assessment_service import run_assessment_job

logger = logging.getLogger(__name__)


def _event_loop_snapshot() -> dict[str, str | bool]:
    policy = asyncio.get_event_loop_policy()
    snapshot: dict[str, str | bool] = {
        "event_loop_policy": f"{type(policy).__module__}.{type(policy).__name__}",
        "loop_type": "none",
        "subprocess_supported": False,
    }
    loop = asyncio.new_event_loop()
    try:
        snapshot["loop_type"] = f"{type(loop).__module__}.{type(loop).__name__}"
        transport_impl = getattr(type(loop), "_make_subprocess_transport", None)
        base_impl = getattr(asyncio.BaseEventLoop, "_make_subprocess_transport", None)
        snapshot["subprocess_supported"] = transport_impl is not None and transport_impl is not base_impl
    finally:
        loop.close()
    return snapshot


def _configure_windows_subprocess_event_loop() -> None:
    if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        current_policy = asyncio.get_event_loop_policy()
        if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
            logger.warning(
                "Switching Windows asyncio policy for PowerShell subprocess support",
                extra={"previous_policy": f"{type(current_policy).__module__}.{type(current_policy).__name__}"},
            )
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@celery_app.task(
    name="assessment.run",
    bind=True,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_assessment_task(self, job_id: str) -> dict:
    logger.info(
        "Assessment task asyncio runtime before policy configuration",
        extra={"job_id": job_id, **_event_loop_snapshot()},
    )
    _configure_windows_subprocess_event_loop()
    logger.info(
        "Assessment task asyncio runtime before asyncio.run",
        extra={"job_id": job_id, **_event_loop_snapshot()},
    )
    return asyncio.run(run_assessment_job(job_id, worker_id=self.request.id))
