"""
Assessment event persistence and Redis-backed fanout.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.assessment_event import AssessmentEvent


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_default(value):
    if isinstance(value, (datetime, UUID)):
        return str(value)
    return value


def assessment_channel(assessment_id: str | UUID) -> str:
    return f"assessment:{assessment_id}"


def tenant_channel(tenant_id: str) -> str:
    return f"tenant:{tenant_id}:assessments"


def event_to_payload(event: AssessmentEvent) -> dict[str, Any]:
    return {
        "event": event.event_type,
        "type": event.event_type,
        "assessment_id": str(event.assessment_id),
        "tenant_id": event.tenant_id,
        "timestamp": event.created_at.isoformat(),
        "severity": event.severity,
        "payload": event.event_payload or {},
    }


async def get_recent_events(
    db: AsyncSession,
    *,
    assessment_id: UUID,
    tenant_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(AssessmentEvent)
        .where(
            AssessmentEvent.assessment_id == assessment_id,
            AssessmentEvent.tenant_id == tenant_id,
        )
        .order_by(AssessmentEvent.created_at.desc())
        .limit(limit)
    )
    events = list(reversed(result.scalars().all()))
    return [event_to_payload(event) for event in events]


async def persist_event(
    db: AsyncSession,
    *,
    assessment_id: UUID,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    severity: str = "info",
    commit: bool = False,
) -> AssessmentEvent:
    event = AssessmentEvent(
        assessment_id=assessment_id,
        tenant_id=tenant_id,
        event_type=event_type,
        severity=severity,
        event_payload=payload or {},
        created_at=_now(),
    )
    db.add(event)
    await db.flush()
    if commit:
        await db.commit()
        await db.refresh(event)
    return event


async def publish_event(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, default=_json_default)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.publish(assessment_channel(payload["assessment_id"]), encoded)
        await redis.publish(tenant_channel(payload["tenant_id"]), encoded)
    finally:
        await redis.aclose()


async def emit_event(
    db: AsyncSession,
    *,
    assessment_id: UUID,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    severity: str = "info",
    commit: bool = False,
) -> dict[str, Any]:
    event = await persist_event(
        db,
        assessment_id=assessment_id,
        tenant_id=tenant_id,
        event_type=event_type,
        payload=payload,
        severity=severity,
        commit=commit,
    )
    event_payload = event_to_payload(event)
    try:
        await publish_event(event_payload)
    except Exception:
        # Persistence is authoritative; Redis fanout is best-effort for local/dev availability.
        pass
    return event_payload
