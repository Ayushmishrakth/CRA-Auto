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
    spa_redirect_uri: str | None = None,
) -> dict[str, Any]:
    redirect_uri = _validate_redirect_uri(redirect_uri)
    payload = build_application_create_payload(
        display_name=display_name,
        required_resource_access=required_resource_access,
        redirect_uri=redirect_uri,
        spa_redirect_uri=spa_redirect_uri,
    )
    response = await client.post("/applications", json=payload)
    response["_graph_create_payload"] = payload
    return response


def build_application_create_payload(
    *,
    display_name: str,
    required_resource_access: list[dict[str, Any]],
    redirect_uri: str,
    spa_redirect_uri: str | None = None,
) -> dict[str, Any]:
    redirect_uri = _validate_redirect_uri(redirect_uri)
    spa_redirect_uri = _validate_redirect_uri(spa_redirect_uri) if spa_redirect_uri else None
    payload = {
        "displayName": display_name,
        "signInAudience": "AzureADMyOrg",
        "requiredResourceAccess": required_resource_access,
    }
    if spa_redirect_uri:
        payload["spa"] = {"redirectUris": [spa_redirect_uri]}
        if spa_redirect_uri != redirect_uri:
            payload["web"] = {"redirectUris": [redirect_uri]}
    else:
        payload["web"] = {"redirectUris": [redirect_uri]}
    return payload


def build_redirect_uri(frontend_url: str) -> str:
    frontend_url = _validate_frontend_url(frontend_url)
    return f"{frontend_url.rstrip('/')}/tenant/deployment-success"


def build_spa_redirect_uri(frontend_url: str) -> str:
    return build_redirect_uri(frontend_url)


def build_consent_redirect_uri(frontend_url: str) -> str:
    """Dedicated Web-platform redirect URI for the /adminconsent server-side redirect."""
    frontend_url = _validate_frontend_url(frontend_url)
    return f"{frontend_url.rstrip('/')}/tenant/consent-callback"


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
    spa_redirect_uri: str | None = None,
) -> dict[str, Any]:
    redirect_uri = _validate_redirect_uri(redirect_uri)
    spa_redirect_uri = _validate_redirect_uri(spa_redirect_uri) if spa_redirect_uri else None
    application = await get_application(client, application_object_id=application_object_id)
    configured_web = list((application.get("web") or {}).get("redirectUris") or [])
    if spa_redirect_uri == redirect_uri:
        web_redirect_uris = _remove_redirect_uri(configured_web, redirect_uri)
    else:
        web_redirect_uris = _append_redirect_uri(configured_web, redirect_uri)

    payload = {"web": {"redirectUris": web_redirect_uris}}
    if spa_redirect_uri:
        payload["spa"] = {
            "redirectUris": _append_redirect_uri(
                list((application.get("spa") or {}).get("redirectUris") or []),
                spa_redirect_uri,
            )
        }
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


def application_resource_access_matches_exactly(
    application: dict[str, Any],
    required_resource_access: list[dict[str, Any]],
) -> bool:
    """True only when the app's requiredResourceAccess is EXACTLY the canonical set
    (nothing missing AND nothing extra). Used to keep the CRA-managed app in sync so
    stale/invalid resource entitlements (e.g. a permission id that fails admin consent
    with AADSTS65006) are removed on the next deploy, not just added to."""

    def flatten(rra: list[dict[str, Any]] | None) -> set[tuple[str, str]]:
        return {
            (str(resource.get("resourceAppId")), str(item.get("id")))
            for resource in (rra or [])
            for item in (resource.get("resourceAccess") or [])
        }

    return flatten(application.get("requiredResourceAccess")) == flatten(required_resource_access)


async def ensure_application_required_resource_access(
    client: GraphClient,
    *,
    application_object_id: str,
    required_resource_access: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    application = await get_application(client, application_object_id=application_object_id)
    # Reconcile EXACTLY (not just "superset present") so stale/invalid resource
    # entitlements — e.g. the Teams Tenant Admin API block that made admin consent
    # fail with AADSTS65006 — are removed on the next deploy, not left behind.
    if application_resource_access_matches_exactly(application, required_resource_access):
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
    spa_redirect_uri: str | None = None,
    max_attempts: int = 10,
    initial_delay_seconds: float = 0.25,
) -> tuple[dict[str, Any], dict[str, Any] | None, int]:
    expected = _validate_redirect_uri(redirect_uri)
    expected_spa = _validate_redirect_uri(spa_redirect_uri) if spa_redirect_uri else None
    patch_result: dict[str, Any] | None = None
    delay = initial_delay_seconds

    for attempt in range(1, max_attempts + 1):
        application = await get_application(client, application_object_id=application_object_id)
        configured_web = list((application.get("web") or {}).get("redirectUris") or [])
        configured_spa = list((application.get("spa") or {}).get("redirectUris") or [])
        web_valid = expected_spa == expected or expected in configured_web
        spa_valid = expected_spa is None or expected_spa in configured_spa
        if web_valid and spa_valid:
            logger.info(
                "[DEPLOYMENT] Redirect URI Verified %s",
                {"application_id": application_object_id, "redirect_uri": expected, "spa_redirect_uri": expected_spa},
            )
            return application, patch_result, attempt

        if patch_result is None:
            logger.info(
                "[DEPLOYMENT] Redirect URI Missing %s",
                {
                    "application_id": application_object_id,
                    "redirect_uri": expected,
                    "spa_redirect_uri": expected_spa,
                    "configured_web_redirect_uris": configured_web,
                    "configured_spa_redirect_uris": configured_spa,
                },
            )
            logger.info(
                "[DEPLOYMENT] Patching Redirect URI %s",
                {"application_id": application_object_id, "redirect_uri": expected, "spa_redirect_uri": expected_spa},
            )
            patch_result = await patch_application_redirect_uri(
                client,
                application_object_id=application_object_id,
                redirect_uri=expected,
                spa_redirect_uri=expected_spa,
            )

        if attempt < max_attempts:
            await asyncio.sleep(delay)
            delay = min(delay * 2, 5.0)

    application = await get_application(client, application_object_id=application_object_id)
    configured_web = list((application.get("web") or {}).get("redirectUris") or [])
    configured_spa = list((application.get("spa") or {}).get("redirectUris") or [])
    web_valid = expected_spa == expected or expected in configured_web
    spa_valid = expected_spa is None or expected_spa in configured_spa
    if not web_valid or not spa_valid:
        raise BusinessLogicException(
            "Azure App Registration redirect URI configuration failed",
            details={
                "redirect_uri": expected,
                "spa_redirect_uri": expected_spa,
                "configured_web_redirect_uris": configured_web,
                "configured_spa_redirect_uris": configured_spa,
            },
        )
    return application, patch_result, max_attempts


async def ensure_application_web_redirect_uri(
    client: GraphClient,
    *,
    application_object_id: str,
    web_redirect_uri: str,
) -> dict[str, Any]:
    """
    Additively register a Web-platform redirect URI on the app registration. The
    /adminconsent endpoint performs a server-side redirect that must land on a Web
    redirect URI (SPA redirect URIs are not accepted there), so admin consent needs
    this even though the frontend uses a SPA redirect for token acquisition. Existing
    web and spa redirect URIs are preserved.
    """
    web_redirect_uri = _validate_redirect_uri(web_redirect_uri)
    application = await get_application(client, application_object_id=application_object_id)
    configured_web = list((application.get("web") or {}).get("redirectUris") or [])
    if web_redirect_uri in configured_web:
        return {"already_present": True, "web_redirect_uris": configured_web}
    updated = _append_redirect_uri(configured_web, web_redirect_uri)
    payload = {"web": {"redirectUris": updated}}
    response = await client.patch(f"/applications/{application_object_id}", json=payload)
    logger.info(
        "[DEPLOYMENT] Registered Web consent redirect URI %s",
        {"application_id": application_object_id, "web_redirect_uri": web_redirect_uri},
    )
    return {"already_present": False, "web_redirect_uris": updated, "response": response}


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
        params={"$select": "id,appId,displayName,requiredResourceAccess,passwordCredentials,web,spa"},
    )


async def get_application_by_app_id(client: GraphClient, *, application_client_id: str) -> dict[str, Any] | None:
    response = await client.get(
        "/applications",
        params={
            "$filter": f"appId eq '{application_client_id}'",
            "$select": "id,appId,displayName,requiredResourceAccess,passwordCredentials,web,spa",
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


def _append_redirect_uri(configured: list[str], redirect_uri: str) -> list[str]:
    values = [value for value in configured if value]
    if redirect_uri not in values:
        values.append(redirect_uri)
    return values


def _remove_redirect_uri(configured: list[str], redirect_uri: str) -> list[str]:
    return [value for value in configured if value and value != redirect_uri]


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
