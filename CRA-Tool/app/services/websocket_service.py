"""
WebSocket authorization helpers.
"""

from uuid import UUID

from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.models.assessment_job import AssessmentJob
from app.db.models.assessment import Assessment
from app.db.models.user_session import UserSession
from app.db.session import AsyncSessionLocal
from app.services.event_bus import get_recent_events


async def validate_ws_token(token: str | None) -> dict | None:
    payload = decode_access_token(token) if token else None
    if payload is None:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserSession).where(UserSession.jwt_jti == payload.get("jti"))
        )
        session = result.scalars().first()

    if session is not None and session.revoked_at is not None:
        return None
    return payload


async def can_access_assessment_channel(token: str | None, assessment_id: str) -> bool:
    return await get_assessment_channel_context(token, assessment_id) is not None


async def get_assessment_channel_context(
    token: str | None,
    assessment_id: str,
) -> dict | None:
    payload = await validate_ws_token(token)
    if payload is None:
        return None

    try:
        assessment_uuid = UUID(assessment_id)
    except ValueError:
        return None

    connected_tenants = set(payload.get("connected_tenants") or [])
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Assessment).where(Assessment.id == assessment_uuid))
        assessment = result.scalars().first()

    if assessment is None or assessment.tenant_id not in connected_tenants:
        return None
    return {
        "assessment_id": str(assessment.id),
        "tenant_id": assessment.tenant_id,
        "user_id": payload.get("sub"),
    }


async def get_tenant_job_channel_context(token: str | None, job_id: str) -> dict | None:
    payload = await validate_ws_token(token)
    if payload is None:
        return None

    try:
        job_uuid = UUID(job_id)
    except ValueError:
        return None

    connected_tenants = set(payload.get("connected_tenants") or [])
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AssessmentJob).where(AssessmentJob.id == job_uuid))
        job = result.scalars().first()

    if job is None or job.tenant_id not in connected_tenants:
        return None
    return {
        "job_id": str(job.id),
        "assessment_id": str(job.assessment_id),
        "tenant_id": job.tenant_id,
        "user_id": payload.get("sub"),
    }


async def get_recent_assessment_events(
    *,
    assessment_id: str,
    tenant_id: str,
    limit: int = 100,
) -> list[dict]:
    async with AsyncSessionLocal() as db:
        return await get_recent_events(
            db,
            assessment_id=UUID(assessment_id),
            tenant_id=tenant_id,
            limit=limit,
        )
