from __future__ import annotations

from typing import Any

from app.services.graph.graph_client import GraphClient


async def create_service_principal(client: GraphClient, *, app_id: str) -> dict[str, Any]:
    return await client.post("/servicePrincipals", json={"appId": app_id})


async def get_service_principal_by_app_id(client: GraphClient, *, app_id: str) -> dict[str, Any] | None:
    response = await client.get(
        "/servicePrincipals",
        params={"$filter": f"appId eq '{app_id}'", "$select": "id,appId,displayName,appRoleAssignments"},
    )
    values = response.get("value") or []
    if not values:
        return None
    return values[0]


async def ensure_service_principal(client: GraphClient, *, app_id: str) -> dict[str, Any]:
    service_principal = await get_service_principal_by_app_id(client, app_id=app_id)
    if service_principal:
        return service_principal
    return await create_service_principal(client, app_id=app_id)


async def get_service_principal(client: GraphClient, *, service_principal_id: str) -> dict[str, Any]:
    return await client.get(
        f"/servicePrincipals/{service_principal_id}",
        params={"$select": "id,appId,displayName,appRoleAssignments"},
    )
