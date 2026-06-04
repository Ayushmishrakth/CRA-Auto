"""
Tenant API business logic.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicException, NotFoundException, TenantAccessException
from app.core.pagination import PaginationParams
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User
from app.db.repositories.base_repository import BaseRepository
from app.schemas.tenant import TenantConnectRequest
from app.services.audit_service import AuditEvent, audit_service
from app.services.tenant_deployment_service import TENANT_STATUS_NOT_DEPLOYED

tenant_repository = BaseRepository(ConnectedTenant)


async def connect_tenant(
    db: AsyncSession,
    *,
    current_user: User,
    payload: TenantConnectRequest,
) -> ConnectedTenant:
    if payload.tenant_id != current_user.microsoft_tid:
        raise TenantAccessException("Tenant is not available to the current user")
    if payload.granted_permissions:
        raise BusinessLogicException("Tenant permissions can only be granted by Microsoft Graph deployment validation")

    result = await db.execute(
        select(ConnectedTenant).where(ConnectedTenant.tenant_id == payload.tenant_id)
    )
    tenant = result.scalars().first()
    if tenant is None:
        tenant = ConnectedTenant(
            tenant_id=payload.tenant_id,
            tenant_name=payload.tenant_name or payload.tenant_id,
            consent_status="pending",
            granted_permissions=[],
            deployment_status=TENANT_STATUS_NOT_DEPLOYED,
            status=TENANT_STATUS_NOT_DEPLOYED,
        )
        db.add(tenant)
    else:
        tenant.tenant_name = payload.tenant_name or tenant.tenant_name

    await audit_service.log_event(
        db,
        tenant_id=payload.tenant_id,
        event=AuditEvent.TENANT_CONNECTED,
        action="tenant.connect",
        user_id=current_user.id,
        resource="connected_tenants",
    )
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def list_tenants(
    db: AsyncSession,
    *,
    current_user: User,
    pagination: PaginationParams,
) -> list[ConnectedTenant]:
    result = await db.execute(
        select(ConnectedTenant)
        .where(ConnectedTenant.tenant_id == current_user.microsoft_tid)
        .offset(pagination.resolved_offset)
        .limit(pagination.limit)
    )
    return list(result.scalars().all())


async def get_tenant(
    db: AsyncSession,
    *,
    current_user: User,
    tenant_id: str,
) -> ConnectedTenant:
    if tenant_id != current_user.microsoft_tid:
        raise TenantAccessException("Tenant is not available to the current user")
    result = await db.execute(
        select(ConnectedTenant).where(ConnectedTenant.tenant_id == tenant_id)
    )
    tenant = result.scalars().first()
    if tenant is None:
        raise NotFoundException("Tenant not found")
    return tenant


async def disconnect_tenant(
    db: AsyncSession,
    *,
    current_user: User,
    tenant_id: str,
) -> ConnectedTenant:
    tenant = await get_tenant(db, current_user=current_user, tenant_id=tenant_id)
    tenant.status = TENANT_STATUS_NOT_DEPLOYED
    tenant.deployment_status = TENANT_STATUS_NOT_DEPLOYED
    tenant.consent_status = "pending"
    await audit_service.log_event(
        db,
        tenant_id=tenant_id,
        event=AuditEvent.TENANT_DISCONNECTED,
        action="tenant.disconnect",
        user_id=current_user.id,
        resource="connected_tenants",
    )
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def get_permissions(
    db: AsyncSession,
    *,
    current_user: User,
    tenant_id: str,
) -> ConnectedTenant:
    return await get_tenant(db, current_user=current_user, tenant_id=tenant_id)
