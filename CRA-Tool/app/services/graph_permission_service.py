from __future__ import annotations

from typing import Any

from app.core.exceptions import BusinessLogicException
from app.services.graph.graph_client import GraphClient


MICROSOFT_GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"

# Exchange Online resource — used to grant Exchange.ManageAsApp for PS app-only auth
EXCHANGE_RESOURCE_APP_ID = "00000002-0000-0ff1-ce00-000000000000"
EXCHANGE_APP_PERMISSIONS = [
    # Exchange.ManageAsApp — allows service principal to run Exchange Online cmdlets
    {"id": "dc50a0fb-09a3-484d-be87-e023b12c6440", "type": "Role"},
]

# Skype and Teams Tenant Admin API — used to grant application_access for Teams PS app-only auth
TEAMS_RESOURCE_APP_ID = "48ac35b8-9aa8-4d74-927d-1f4a14a0b239"
TEAMS_APP_PERMISSIONS = [
    # application_access — allows service principal to run Teams admin cmdlets without a signed-in user
    {"id": "dc3d2358-0f5d-4ddc-b47e-bf73ef99acfd", "type": "Role"},
]

REQUIRED_APPLICATION_PERMISSIONS = [
    "Application.Read.All",
    "Directory.Read.All",
    "Group.Read.All",
    "User.Read.All",
    "Organization.Read.All",
    "Reports.Read.All",
    "AuditLog.Read.All",
    "Policy.Read.All",
    "RoleManagement.Read.Directory",
    "SecurityEvents.Read.All",
    "IdentityRiskyUser.Read.All",
    "DeviceManagementManagedDevices.Read.All",
    "UserAuthenticationMethod.Read.All",
    "Team.ReadBasic.All",
    "Sites.Read.All",
    "Sites.FullControl.All",
    "Files.Read.All",
    "SharePointTenantSettings.Read.All",
    "InformationProtectionPolicy.Read.All",
    "SecurityActions.Read.All",
]

REQUIRED_DELEGATED_PERMISSIONS = [
    "User.Read",
    "Application.ReadWrite.All",
    "AppRoleAssignment.ReadWrite.All",
    "Directory.Read.All",
]


async def get_graph_service_principal(client: GraphClient) -> dict[str, Any]:
    response = await client.get(
        "/servicePrincipals",
        params={"$filter": f"appId eq '{MICROSOFT_GRAPH_APP_ID}'", "$select": "id,appId,appRoles,oauth2PermissionScopes"},
    )
    values = response.get("value") or []
    if not values:
        raise BusinessLogicException("Microsoft Graph service principal was not found in tenant")
    return values[0]


async def build_required_resource_access(client: GraphClient) -> list[dict[str, Any]]:
    app_roles = await get_required_app_roles(client)
    return [
        {
            "resourceAppId": MICROSOFT_GRAPH_APP_ID,
            "resourceAccess": [
                {"id": app_roles[name]["id"], "type": "Role"}
                for name in REQUIRED_APPLICATION_PERMISSIONS
            ],
        },
        {
            "resourceAppId": EXCHANGE_RESOURCE_APP_ID,
            "resourceAccess": EXCHANGE_APP_PERMISSIONS,
        },
    ]


async def get_required_app_roles(client: GraphClient) -> dict[str, dict[str, Any]]:
    graph_sp = await get_graph_service_principal(client)
    app_roles = {
        role.get("value"): role
        for role in graph_sp.get("appRoles") or []
        if role.get("isEnabled") and role.get("value")
    }
    missing = [name for name in REQUIRED_APPLICATION_PERMISSIONS if name not in app_roles]
    if missing:
        raise BusinessLogicException(
            "Microsoft Graph application permissions unavailable",
            details={"missing_permissions": missing},
        )
    return {name: app_roles[name] for name in REQUIRED_APPLICATION_PERMISSIONS}


def required_permission_ids(app_roles: dict[str, dict[str, Any]]) -> set[str]:
    return {str(app_roles[name]["id"]) for name in REQUIRED_APPLICATION_PERMISSIONS}
