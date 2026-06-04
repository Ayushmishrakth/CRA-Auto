from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.db.models.tenant import ConnectedTenant
from app.services.graph.graph_client import GraphClient
from app.services.graph_app_registration_service import get_application
from app.services.graph_permission_service import (
    MICROSOFT_GRAPH_APP_ID,
    get_graph_service_principal,
    get_required_app_roles,
    required_permission_ids,
)
from app.services.graph_service_principal_service import get_service_principal
from app.utils.datetime_utils import parse_graph_datetime


@dataclass(frozen=True)
class DeploymentValidationResult:
    app_registration_exists: bool
    service_principal_exists: bool
    secret_exists: bool
    permissions_assigned: bool
    admin_consent_granted: bool
    details: dict[str, Any]

    @property
    def is_active(self) -> bool:
        return all(
            [
                self.app_registration_exists,
                self.service_principal_exists,
                self.secret_exists,
                self.permissions_assigned,
                self.admin_consent_granted,
            ]
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _has_secret(application: dict[str, Any], tenant: ConnectedTenant) -> bool:
    if not tenant.secret_id:
        return False
    now = _utcnow()
    for credential in application.get("passwordCredentials") or []:
        if str(credential.get("keyId")) != tenant.secret_id:
            continue
        end = credential.get("endDateTime")
        if not end:
            return True
        expires_at = parse_graph_datetime(end)
        if expires_at is None:
            return False
        return expires_at > now
    return False


def _has_required_resource_access(application: dict[str, Any], required_ids: set[str]) -> bool:
    for resource in application.get("requiredResourceAccess") or []:
        if resource.get("resourceAppId") != MICROSOFT_GRAPH_APP_ID:
            continue
        assigned_ids = {str(item.get("id")) for item in resource.get("resourceAccess") or []}
        return required_ids.issubset(assigned_ids)
    return False


async def _get_app_role_assignments(client: GraphClient, *, service_principal_id: str) -> list[dict[str, Any]]:
    response = await client.get(
        f"/servicePrincipals/{service_principal_id}/appRoleAssignments",
        params={"$select": "id,appRoleId,resourceId,resourceDisplayName"},
    )
    return response.get("value") or []


def _has_admin_consent(assignments: list[dict[str, Any]], graph_sp: dict[str, Any], required_ids: set[str]) -> bool:
    graph_sp_id = str(graph_sp.get("id"))
    granted_ids = {
        str(item.get("appRoleId"))
        for item in assignments
        if str(item.get("resourceId")) == graph_sp_id
        or item.get("resourceDisplayName") == "Microsoft Graph"
    }
    return required_ids.issubset(granted_ids)


async def validate_deployment_once(client: GraphClient, tenant: ConnectedTenant) -> DeploymentValidationResult:
    details: dict[str, Any] = {}
    application: dict[str, Any] | None = None
    service_principal: dict[str, Any] | None = None
    graph_sp: dict[str, Any] | None = None
    app_roles: dict[str, dict[str, Any]] = {}
    assignments: list[dict[str, Any]] = []

    if tenant.app_registration_id:
        try:
            application = await get_application(client, application_object_id=tenant.app_registration_id)
        except Exception as exc:
            details["application_error"] = str(exc)

    if tenant.service_principal_id:
        try:
            service_principal = await get_service_principal(
                client,
                service_principal_id=tenant.service_principal_id,
            )
        except Exception as exc:
            details["service_principal_error"] = str(exc)

    try:
        graph_sp = await get_graph_service_principal(client)
        app_roles = await get_required_app_roles(client)
    except Exception as exc:
        details["graph_permissions_error"] = str(exc)

    required_ids = required_permission_ids(app_roles) if app_roles else set()
    if tenant.service_principal_id:
        try:
            assignments = await _get_app_role_assignments(
                client,
                service_principal_id=tenant.service_principal_id,
            )
        except Exception as exc:
            details["app_role_assignments_error"] = str(exc)

    result = DeploymentValidationResult(
        app_registration_exists=bool(application and application.get("appId") == tenant.app_client_id),
        service_principal_exists=bool(
            service_principal and service_principal.get("appId") == tenant.app_client_id
        ),
        secret_exists=bool(application and _has_secret(application, tenant)),
        permissions_assigned=bool(application and required_ids and _has_required_resource_access(application, required_ids)),
        admin_consent_granted=bool(graph_sp and required_ids and _has_admin_consent(assignments, graph_sp, required_ids)),
        details={
            **details,
            "required_permissions": list(app_roles.keys()),
            "app_role_assignment_count": len(assignments),
        },
    )
    return result


async def validate_deployment_with_retry(
    client: GraphClient,
    tenant: ConnectedTenant,
    *,
    delay_seconds: int = 10,
) -> DeploymentValidationResult:
    first = await validate_deployment_once(client, tenant)
    if first.is_active:
        return first
    await asyncio.sleep(delay_seconds)
    return await validate_deployment_once(client, tenant)
