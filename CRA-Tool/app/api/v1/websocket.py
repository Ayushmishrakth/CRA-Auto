"""
Authenticated Redis-backed WebSocket endpoints.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.config import settings
from app.services.event_bus import assessment_channel, tenant_channel
from app.services.websocket_service import (
    get_assessment_channel_context,
    get_recent_assessment_events,
    get_tenant_job_channel_context,
)

router = APIRouter(tags=["WebSocket"])


async def _relay_pubsub(websocket: WebSocket, channel: str) -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload = message.get("data")
            try:
                payload = json.loads(payload)
            except (TypeError, json.JSONDecodeError):
                payload = {"type": "message", "event": "message", "payload": payload}
            await websocket.send_json(payload)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await redis.aclose()


async def _receive_client_messages(websocket: WebSocket) -> None:
    while True:
        try:
            raw = await websocket.receive_text()
        except WebSocketDisconnect:
            raise

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"type": raw}

        if payload.get("type") in {"heartbeat", "ping"}:
            await websocket.send_json(
                {"type": "heartbeat.ack", "event": "heartbeat.ack", "timestamp": payload.get("timestamp")}
            )


async def _run_socket(websocket: WebSocket, *, channel: str, connected_payload: dict) -> None:
    await websocket.accept()
    await websocket.send_json(connected_payload)

    relay_task = asyncio.create_task(_relay_pubsub(websocket, channel))
    receive_task = asyncio.create_task(_receive_client_messages(websocket))
    try:
        done, pending = await asyncio.wait(
            {relay_task, receive_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    finally:
        for task in (relay_task, receive_task):
            if not task.done():
                task.cancel()


@router.websocket("/ws/assessment/{assessment_id}")
async def assessment_socket(websocket: WebSocket, assessment_id: str) -> None:
    context = await get_assessment_channel_context(
        websocket.query_params.get("token"),
        assessment_id,
    )
    if context is None:
        await websocket.close(code=1008, reason="Assessment channel is not available")
        return

    await websocket.accept()
    await websocket.send_json(
        {
            "type": "connected",
            "event": "connected",
            "assessment_id": assessment_id,
            "tenant_id": context["tenant_id"],
        }
    )
    for event in await get_recent_assessment_events(
        assessment_id=assessment_id,
        tenant_id=context["tenant_id"],
    ):
        await websocket.send_json({**event, "replay": True})

    relay_task = asyncio.create_task(
        _relay_pubsub(websocket, assessment_channel(assessment_id))
    )
    receive_task = asyncio.create_task(_receive_client_messages(websocket))
    try:
        done, pending = await asyncio.wait(
            {relay_task, receive_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    finally:
        for task in (relay_task, receive_task):
            if not task.done():
                task.cancel()


@router.websocket("/ws/tenant/{job_id}")
async def tenant_job_socket(websocket: WebSocket, job_id: str) -> None:
    context = await get_tenant_job_channel_context(websocket.query_params.get("token"), job_id)
    if context is None:
        await websocket.close(code=1008, reason="Job channel is not available")
        return

    await _run_socket(
        websocket,
        channel=tenant_channel(context["tenant_id"]),
        connected_payload={
            "type": "connected",
            "event": "connected",
            "job_id": job_id,
            "assessment_id": context["assessment_id"],
            "tenant_id": context["tenant_id"],
        },
    )
