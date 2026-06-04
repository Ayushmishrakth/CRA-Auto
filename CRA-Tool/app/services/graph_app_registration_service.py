from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import BusinessLogicException
from app.services.graph.graph_client import GraphClient
from app.utils.logger import logger


CRA_APPLICATION_DISPLAY_NAME = "CRA Assessment Platform"
GRAPH_APP_REGISTRATION_SERVICE_VERSION = "2026-05-30.runtime-consent-audit.v2-stale-record-repair"


async def create_application(
    client: GraphClient,
    *,
    display_name: str = CRA_APPLICATION_DISPLAY_NAME,
    required_resource_access: list[dict[str, Any]],
    redirect_uri: str,
) -> dict[str, Any]:
    redirect_uri = _validate_redirect_uri(redirect_uri)
    payload = build_application_create_payload(
        display_name=display_name,
        required_resource_access=required_resource_access,
        redirect_uri=redirect_uri,
    )
    response = await client.post("/applications", json=payload)
    response["_graph_create_payload"] = payload
    return response


def build_application_create_payload(
    *,
    display_name: str,
    required_resource_access: list[dict[str, Any]],
    redirect_uri: str,
) -> dict[str, Any]:
    redirect_uri = _validate_redirect_uri(redirect_uri)
    return {
        "displayName": display_name,
        "signInAudience": "AzureADMyOrg",
        "requiredResourceAccess": required_resource_access,
        "web": {"redirectUris": [redirect_uri]},
    }


def build_redirect_uri(frontend_url: str) -> str:
    frontend_url = _validate_frontend_url(frontend_url)
    return f"{frontend_url.rstrip('/')}/tenant/deployment-success"


def _validate_frontend_url(frontend_url: str | None) -> str:
    value = (frontend_url or "").strip().rstrip("/")
    if not value:
        raise BusinessLogicException("CRA_FRONTEND_URL is required for deployment redirect URI configuration")
    _validate_redirect_uri(f"{value}/tenant/deployment-success")
    return value


async def patch_application_redirect_uri(
    client: GraphClient,
    *,
    application_object_id: str,
    redirect_uri: str,
) -> dict[str, Any]:
    redirect_uri = _validate_redirect_uri(redirect_uri)
    payload = {"web": {"redirectUris": [redirect_uri]}}
    response = await client.patch(f"/applications/{application_object_id}", json=payload)
    return {"payload": payload, "response": response}


async def patch_application_required_resource_access(
    client: GraphClient,
    *,
    application_object_id: str,
    required_resource_access: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {"requiredResourceAccess": required_resource_access}
    response = await client.patch(f"/applications/{application_object_id}", json=payload)
    return {"payload": payload, "response": response}


def application_has_required_resource_access(
    application: dict[str, Any],
    required_resource_access: list[dict[str, Any]],
) -> bool:
    configured = {
        resource.get("resourceAppId"): {
            str(item.get("id")) for item in resource.get("resourceAccess") or []
        }
        for resource in application.get("requiredResourceAccess") or []
    }
    for resource in required_resource_access:
        resource_app_id = resource.get("resourceAppId")
        required_ids = {str(item.get("id")) for item in resource.get("resourceAccess") or []}
        if not required_ids.issubset(configured.get(resource_app_id, set())):
            return False
    return True


async def ensure_application_required_resource_access(
    client: GraphClient,
    *,
    application_object_id: str,
    required_resource_access: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    application = await get_application(client, application_object_id=application_object_id)
    if application_has_required_resource_access(application, required_resource_access):
        return application, None

    patch_result = await patch_application_required_resource_access(
        client,
        application_object_id=application_object_id,
        required_resource_access=required_resource_access,
    )
    application = await get_application(client, application_object_id=application_object_id)
    if not application_has_required_resource_access(application, required_resource_access):
        raise BusinessLogicException(
            "Azure App Registration Graph permission configuration failed",
            details={"application_object_id": application_object_id},
        )
    return application, patch_result


async def ensure_application_redirect_uri(
    client: GraphClient,
    *,
    application_object_id: str,
    redirect_uri: str,
    max_attempts: int = 10,
    initial_delay_seconds: float = 0.25,
) -> tuple[dict[str, Any], dict[str, Any] | None, int]:
    expected = _validate_redirect_uri(redirect_uri)
    patch_result: dict[str, Any] | None = None
    delay = initial_delay_seconds

    for attempt in range(1, max_attempts + 1):
        application = await get_application(client, application_object_id=application_object_id)
        configured = list((application.get("web") or {}).get("redirectUris") or [])
        if expected in configured:
            logger.info("[DEPLOYMENT] Redirect URI Verified %s", {"application_id": application_object_id, "redirect_uri": expected})
            return application, patch_result, attempt

        if patch_result is None:
            logger.info(
                "[DEPLOYMENT] Redirect URI Missing %s",
                {"application_id": application_object_id, "redirect_uri": expected, "configured_redirect_uris": configured},
            )
            logger.info("[DEPLOYMENT] Patching Redirect URI %s", {"application_id": application_object_id, "redirect_uri": expected})
            patch_result = await patch_application_redirect_uri(
                client,
                application_object_id=application_object_id,
                redirect_uri=expected,
            )

        if attempt < max_attempts:
            await asyncio.sleep(delay)
            delay = min(delay * 2, 5.0)

    application = await get_application(client, application_object_id=application_object_id)
    configured = list((application.get("web") or {}).get("redirectUris") or [])
    if expected not in configured:
        raise BusinessLogicException(
            "Azure App Registration redirect URI configuration failed",
            details={"redirect_uri": expected, "configured_redirect_uris": configured},
        )
    return application, patch_result, max_attempts


async def verify_application_redirect_uri(
    client: GraphClient,
    *,
    application_object_id: str,
    redirect_uri: str,
) -> dict[str, Any]:
    application, _, _ = await ensure_application_redirect_uri(
        client,
        application_object_id=application_object_id,
        redirect_uri=redirect_uri,
    )
    return application


async def get_application(client: GraphClient, *, application_object_id: str) -> dict[str, Any]:
    return await client.get(
        f"/applications/{application_object_id}",
        params={"$select": "id,appId,displayName,requiredResourceAccess,passwordCredentials,web"},
    )


async def get_application_by_app_id(client: GraphClient, *, application_client_id: str) -> dict[str, Any] | None:
    response = await client.get(
        "/applications",
        params={
            "$filter": f"appId eq '{application_client_id}'",
            "$select": "id,appId,displayName,requiredResourceAccess,passwordCredentials,web",
        },
    )
    values = response.get("value") or []
    if not values:
        return None
    return values[0]


def _validate_redirect_uri(redirect_uri: str | None) -> str:
    value = (redirect_uri or "").strip()
    if not value:
        raise BusinessLogicException("Deployment redirect URI is required")
    if not (value.startswith("https://") or value.startswith("http://localhost") or value.startswith("http://127.0.0.1")):
        raise BusinessLogicException(
            "Deployment redirect URI must be HTTPS, localhost, or 127.0.0.1",
            details={"redirect_uri": value},
        )
    return value


async def create_client_secret(
    client: GraphClient,
    *,
    application_object_id: str,
    display_name: str = "CRA runtime collector secret",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return await client.post(
        f"/applications/{application_object_id}/addPassword",
        json={
            "passwordCredential": {
                "displayName": display_name,
                "startDateTime": now.isoformat(),
            }
        },
    )
