"""
Enterprise audit logging service.
"""

import enum
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog


class AuditEvent(str, enum.Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    LOGOUT = "LOGOUT"
    SESSION_REVOKED = "SESSION_REVOKED"
    TENANT_CONNECTED = "TENANT_CONNECTED"
    TENANT_DISCONNECTED = "TENANT_DISCONNECTED"
    ASSESSMENT_STARTED = "ASSESSMENT_STARTED"
    ASSESSMENT_FAILED = "ASSESSMENT_FAILED"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        *,
        tenant_id: str,
        event: AuditEvent,
        action: str,
        user_id: uuid.UUID | None = None,
        resource: str | None = None,
        metadata: dict[str, Any] | list[Any] | None = None,
        ip_address: str | None = None,
        commit: bool = False,
    ) -> AuditLog:
        audit_log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event.value,
            action=action,
            resource=resource,
            metadata_payload=metadata,
            ip_address=ip_address,
        )
        db.add(audit_log)
        if commit:
            await db.commit()
            await db.refresh(audit_log)
        else:
            await db.flush()
        return audit_log


audit_service = AuditService()
