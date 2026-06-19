from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import jwt
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthException, BusinessLogicException, DeploymentValidationError, TenantAccessException
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User
from app.services.audit_service import AuditEvent, audit_service
from app.services.graph.graph_client import GraphClient
from app.services.graph_app_registration_service import (
    CRA_APPLICATION_DISPLAY_NAME,
    build_redirect_uri,
    build_spa_redirect_uri,
    create_application,
    create_client_secret,
    ensure_application_required_resource_access,
    ensure_application_redirect_uri,
    get_application,
    get_application_by_app_id,
)
from app.services.graph_consent_service import build_admin_consent_url
from app.services.graph_deployment_validation_service import validate_deployment_with_retry
from app.services.graph_permission_service import (
    REQUIRED_APPLICATION_PERMISSIONS,
    REQUIRED_DELEGATED_PERMISSIONS,
    build_required_resource_access,
)
from app.services.graph_service_principal_service import ensure_service_principal, get_service_principal, get_service_principal_by_app_id
from app.services.tenant_secret_service import store_client_secret
from app.utils.datetime_utils import parse_graph_datetime
from app.utils.logger import logger


DEPLOYMENT_SERVICE_VERSION = "2026-06-08.exchange-teams-app-auth.v4"

# Exchange Administrator built-in role template. The role assignment API needs the
# tenant-activated role id, not this template id.
EXCHANGE_ADMIN_ROLE_TEMPLATE_ID = "29232cdf-9323-42fd-ade2-1d097af3e4de"

TENANT_STATUS_NOT_DEPLOYED = "NOT_DEPLOYED"
TENANT_STATUS_DEPLOYING = "DEPLOYING"
TENANT_STATUS_CONSENT_REQUIRED = "CONSENT_REQUIRED"
TENANT_STATUS_VALIDATING = "VALIDATING"
TENANT_STATUS_ACTIVE = "ACTIVE"
TENANT_STATUS_FAILED = "FAILED"
TENANT_STATUS_INVALID = "INVALID"

STEP_GRAPH_TOKEN = "GRAPH_TOKEN"
STEP_APP_REGISTRATION = "APP_REGISTRATION"
STEP_SERVICE_PRINCIPAL = "SERVICE_PRINCIPAL"
STEP_SECRET_CREATION = "SECRET_CREATION"
STEP_PERMISSION_ASSIGNMENT = "PERMISSION_ASSIGNMENT"
STEP_CONSENT_GENERATION = "CONSENT_GENERATION"
STEP_DEPLOYMENT_VALIDATION = "DEPLOYMENT_VALIDATION"


def _mark_deployment(
    tenant: ConnectedTenant,
    *,
    step: str,
    status: str,
    error: str | None = None,
) -> None:
    tenant.deployment_step = step
    tenant.deployment_timestamp = datetime.utcnow()
    tenant.deployment_status = status
    tenant.status = status
    tenant.deployment_error = error


def _deployment_redirect_uri(request_redirect_uri: str | None) -> str:
    expected = build_redirect_uri(settings.cra_frontend_url)
    requested = (request_redirect_uri or "").strip()
    if requested and requested != expected:
        raise BusinessLogicException(
            "Deployment redirect URI does not match CRA_FRONTEND_URL",
            details={"redirect_uri_requested": requested, "redirect_uri_expected": expected},
        )
    return expected


def _deployment_spa_redirect_uri() -> str:
    return build_spa_redirect_uri(settings.cra_frontend_url)


def _update_diagnostics(tenant: ConnectedTenant, **values: Any) -> None:
    tenant.deployment_diagnostics = {**(tenant.deployment_diagnostics or {}), **values}


def _deployment_log(message: str, **context: Any) -> None:
    if context:
        logger.info("[DEPLOYMENT] %s %s", message, context)
    else:
        logger.info("[DEPLOYMENT] %s", message)


def _is_graph_not_found(exc: Exception) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404


def _validate_consent_client_id(consent_url: str, application_client_id: str | None) -> None:
    query = parse_qs(urlparse(consent_url).query)
    consent_client_id = (query.get("client_id") or [None])[0]
    if not application_client_id or consent_client_id != application_client_id:
        raise DeploymentValidationError(
            "Consent URL is using wrong Azure identifier",
            details={
                "consent_url_client_id": consent_client_id,
                "application_client_id": application_client_id,
            },
        )


def _consent_url_client_id(consent_url: str | None) -> str | None:
    if not consent_url:
        return None
    query = parse_qs(urlparse(consent_url).query)
    return (query.get("client_id") or [None])[0]


async def _verify_consent_application(
    client: GraphClient,
    *,
    application_object_id: str | None,
    application_client_id: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not application_object_id or not application_client_id:
        raise DeploymentValidationError(
            "Consent URL is using wrong Azure identifier",
            details={
                "application_object_id": application_object_id,
                "application_client_id": application_client_id,
            },
        )

    try:
        application_by_object_id = await get_application(client, application_object_id=application_object_id)
    except Exception as exc:
        if _is_graph_not_found(exc):
            _deployment_log(
                "APP_NOT_FOUND",
                application_object_id=application_object_id,
                application_client_id=application_client_id,
            )
            raise DeploymentValidationError(
                "Azure application was not found",
                details={
                    "application_object_id": application_object_id,
                    "application_client_id": application_client_id,
                },
            ) from exc
        raise
    object_lookup_app_id = application_by_object_id.get("appId")
    if object_lookup_app_id != application_client_id:
        raise DeploymentValidationError(
            "Consent URL is using wrong Azure identifier",
            details={
                "graph_application_appId": object_lookup_app_id,
                "application_client_id": application_client_id,
                "application_object_id": application_object_id,
            },
        )

    application_by_app_id = await get_application_by_app_id(client, application_client_id=application_client_id)
    if not application_by_app_id or application_by_app_id.get("id") != application_object_id:
        raise DeploymentValidationError(
            "Azure application lookup by client ID failed",
            details={
                "application_client_id": application_client_id,
                "application_object_id": application_object_id,
                "lookup_application_object_id": (application_by_app_id or {}).get("id"),
            },
        )

    return application_by_object_id, application_by_app_id


async def _resolve_verified_application(
    client: GraphClient,
    *,
    application_object_id: str | None,
    application_client_id: str | None,
) -> dict[str, Any] | None:
    if not application_object_id or not application_client_id:
        return None
    try:
        verified_app, _ = await _verify_consent_application(
            client,
            application_object_id=application_object_id,
            application_client_id=application_client_id,
        )
        return verified_app
    except DeploymentValidationError:
        return None
    except Exception as exc:
        if _is_graph_not_found(exc):
            _deployment_log(
                "APP_NOT_FOUND",
                application_object_id=application_object_id,
                application_client_id=application_client_id,
            )
            return None
        raise


async def _load_existing_application_for_repair(
    client: GraphClient,
    *,
    tenant: ConnectedTenant,
) -> dict[str, Any] | None:
    if not tenant.app_registration_id or not tenant.app_client_id:
        return None
    try:
        application = await get_application(client, application_object_id=tenant.app_registration_id)
        application_by_app_id = await get_application_by_app_id(client, application_client_id=tenant.app_client_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            _deployment_log(
                "APP_NOT_FOUND",
                application_client_id=tenant.app_client_id,
                application_object_id=tenant.app_registration_id,
            )
            _deployment_log(
                "Stale Application Registration Missing",
                application_client_id=tenant.app_client_id,
                application_object_id=tenant.app_registration_id,
            )
            return None
        raise

    if application.get("appId") != tenant.app_client_id:
        _deployment_log(
            "Stale Application Registration Client ID Mismatch",
            graph_app_id=application.get("appId"),
            application_client_id=tenant.app_client_id,
            application_object_id=tenant.app_registration_id,
        )
        return None
    if not application_by_app_id or application_by_app_id.get("id") != tenant.app_registration_id:
        _deployment_log(
            "Stale Application Registration AppId Lookup Failed",
            application_client_id=tenant.app_client_id,
            application_object_id=tenant.app_registration_id,
            lookup_application_object_id=(application_by_app_id or {}).get("id"),
        )
        return None
    return application


def _clear_stale_deployment_record(tenant: ConnectedTenant) -> None:
    tenant.app_registration_id = None
    tenant.app_client_id = None
    tenant.service_principal_id = None
    tenant.encrypted_client_secret = None
    tenant.secret_id = None
    tenant.secret_expires_at = None
    tenant.secret_version = None
    tenant.admin_consent_url = None
    tenant.granted_permissions = None


def _mark_invalid_deployment(tenant: ConnectedTenant, *, reason: str, **diagnostics: Any) -> None:
    _deployment_log(
        "STALE_DEPLOYMENT_DETECTED",
        tenant_id=tenant.tenant_id,
        reason=reason,
        application_client_id=tenant.app_client_id,
        application_object_id=tenant.app_registration_id,
        service_principal_id=tenant.service_principal_id,
    )
    _update_diagnostics(
        tenant,
        deployment_invalid_reason=reason,
        stale_application_client_id=tenant.app_client_id,
        stale_application_object_id=tenant.app_registration_id,
        stale_service_principal_id=tenant.service_principal_id,
        **diagnostics,
    )
    _clear_stale_deployment_record(tenant)
    _mark_deployment(tenant, step=STEP_DEPLOYMENT_VALIDATION, status=TENANT_STATUS_INVALID, error=reason)


def _decode_unverified_token(access_token: str) -> dict[str, Any]:
    token = (access_token or "").strip()
    if token.count(".") != 2:
        raise AuthException(
            "Graph access token is malformed; expected a Microsoft Graph JWT access token",
            details={
                "token_format": "not_jwt",
                "dot_count": token.count("."),
                "hint": "Frontend must send MSAL acquireTokenSilent/acquireTokenPopup accessToken for Microsoft Graph, not an ID token or placeholder string.",
            },
        )
    try:
        return jwt.decode(
            token,
            options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
        )
    except jwt.PyJWTError as exc:
        raise AuthException(
            "Graph access token is not a valid JWT",
            details={"jwt_error": str(exc)},
        ) from exc


def _token_diagnostics(claims: dict[str, Any]) -> dict[str, Any]:
    scopes = sorted(str(claims.get("scp") or "").split())
    expires_at = None
    if claims.get("exp"):
        try:
            expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            expires_at = None
    return {
        "issuer": claims.get("iss"),
        "audience": claims.get("aud"),
        "tenant": claims.get("tid"),
        "scopes": scopes,
        "expires_at": expires_at,
        "token_type": "id_token" if claims.get("nonce") and not claims.get("scp") else "access_token",
    }


async def _assert_graph_token(
    client: GraphClient,
    *,
    access_token: str,
    tenant_id: str,
) -> dict[str, Any]:
    claims = _decode_unverified_token(access_token)
    diagnostics = _token_diagnostics(claims)
    audience = claims.get("aud")
    if audience not in {"https://graph.microsoft.com", "00000003-0000-0000-c000-000000000000"}:
        raise AuthException(
            "Graph access token audience is not Microsoft Graph",
            details={**diagnostics, "expected_audience": "https://graph.microsoft.com"},
        )
    if not claims.get("scp"):
        raise AuthException(
            "Graph token is not a delegated Microsoft Graph access token",
            details={**diagnostics, "hint": "ID tokens cannot be used for deployment. Acquire a Graph access token with MSAL."},
        )
    if claims.get("exp"):
        try:
            if int(claims["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
                raise AuthException("Graph access token is expired", details=diagnostics)
        except ValueError as exc:
            raise AuthException("Graph access token expiration is invalid", details=diagnostics) from exc
    token_tid = claims.get("tid")
    if token_tid != tenant_id:
        raise TenantAccessException(
            "Graph access token tenant does not match the requested tenant",
            details={**diagnostics, "requested_tenant": tenant_id},
        )
    scopes = set(str(claims.get("scp") or "").split())
    missing = [scope for scope in REQUIRED_DELEGATED_PERMISSIONS if scope not in scopes]
    if missing:
        raise AuthException(
            "Graph access token is missing required delegated scopes",
            details={**diagnostics, "missing_scopes": missing},
        )
    me = await client.get("/me", params={"$select": "id,userPrincipalName,displayName"})
    org = await client.get("/organization", params={"$select": "id,displayName,verifiedDomains"})
    values = org.get("value") or []
    if not values or values[0].get("id") != tenant_id:
        raise TenantAccessException("Graph organization validation failed for requested tenant")
    return {"claims": claims, "diagnostics": diagnostics, "me": me, "organization": values[0], "scopes": sorted(scopes)}


async def _get_or_create_tenant(
    db: AsyncSession,
    *,
    tenant_id: str,
    tenant_name: str | None,
) -> ConnectedTenant:
    result = await db.execute(select(ConnectedTenant).where(ConnectedTenant.tenant_id == tenant_id))
    tenant = result.scalars().first()
    if tenant is None:
        tenant = ConnectedTenant(
            tenant_id=tenant_id,
            tenant_name=tenant_name or tenant_id,
            consent_status="pending",
            deployment_status=TENANT_STATUS_NOT_DEPLOYED,
            status=TENANT_STATUS_NOT_DEPLOYED,
        )
        db.add(tenant)
        await db.flush()
    return tenant


async def get_deployment_debug(
    db: AsyncSession,
    *,
    current_user: User,
) -> dict[str, Any]:
    result = await db.execute(select(ConnectedTenant).where(ConnectedTenant.tenant_id == current_user.microsoft_tid))
    tenant = result.scalars().first()
    if tenant is None:
        expected = build_redirect_uri(settings.cra_frontend_url)
        return {
            "tenant_id": current_user.microsoft_tid,
            "application_client_id": None,
            "application_object_id": None,
            "consent_url": None,
            "redirect_uri": expected,
            "application_id": None,
            "client_id": None,
            "redirect_uri_expected": expected,
            "redirect_uri_actual": [],
            "service_principal_id": None,
            "secret_id": None,
            "deployment_status": TENANT_STATUS_NOT_DEPLOYED,
            "deployment_step": None,
            "deployment_error": None,
        }

    diagnostics = tenant.deployment_diagnostics or {}
    read_response = diagnostics.get("graph_read_response") or {}
    actual = [
        *list((read_response.get("web") or {}).get("redirectUris") or []),
        *list((read_response.get("spa") or {}).get("redirectUris") or []),
    ]
    if not actual:
        actual = [
            *list(diagnostics.get("graph_verified_redirect_uris") or []),
            *list(diagnostics.get("graph_verified_spa_redirect_uris") or []),
        ]
    return {
        "tenant_id": tenant.tenant_id,
        "application_client_id": tenant.app_client_id,
        "application_object_id": tenant.app_registration_id,
        "consent_url": tenant.admin_consent_url,
        "redirect_uri": tenant.redirect_uri or build_redirect_uri(settings.cra_frontend_url),
        "application_id": tenant.app_registration_id,
        "client_id": tenant.app_client_id,
        "redirect_uri_expected": tenant.redirect_uri or build_redirect_uri(settings.cra_frontend_url),
        "redirect_uri_actual": actual,
        "service_principal_id": tenant.service_principal_id,
        "secret_id": tenant.secret_id,
        "deployment_status": tenant.deployment_status,
        "deployment_step": tenant.deployment_step,
        "deployment_error": tenant.deployment_error,
    }


async def get_deployment_runtime_debug(
    db: AsyncSession,
    *,
    current_user: User,
) -> dict[str, Any]:
    result = await db.execute(select(ConnectedTenant).where(ConnectedTenant.tenant_id == current_user.microsoft_tid))
    tenant = result.scalars().first()
    if tenant is None:
        return {
            "application_client_id": None,
            "application_object_id": None,
            "service_principal_id": None,
            "tenant_id": current_user.microsoft_tid,
            "redirect_uri": build_redirect_uri(settings.cra_frontend_url),
            "consent_url": None,
            "deployment_status": TENANT_STATUS_NOT_DEPLOYED,
            "consent_status": None,
            "consent_url_client_id": None,
            "consent_url_matches_application_client_id": False,
            "deployment_service_version": DEPLOYMENT_SERVICE_VERSION,
        }

    consent_url_client_id = _consent_url_client_id(tenant.admin_consent_url)
    return {
        "application_client_id": tenant.app_client_id,
        "application_object_id": tenant.app_registration_id,
        "service_principal_id": tenant.service_principal_id,
        "tenant_id": tenant.tenant_id,
        "redirect_uri": tenant.redirect_uri,
        "consent_url": tenant.admin_consent_url,
        "deployment_status": tenant.deployment_status,
        "consent_status": tenant.consent_status,
        "consent_url_client_id": consent_url_client_id,
        "consent_url_matches_application_client_id": bool(
            tenant.app_client_id and consent_url_client_id == tenant.app_client_id
        ),
        "deployment_service_version": DEPLOYMENT_SERVICE_VERSION,
        "deployment_diagnostics": tenant.deployment_diagnostics or {},
    }


def _extract_primary_domain(organization: dict[str, Any]) -> str | None:
    """Return the tenant's primary .onmicrosoft.com domain from the Graph /organization object."""
    domains = organization.get("verifiedDomains") or []
    # Prefer the isInitial domain (always the *.onmicrosoft.com one) — required by Connect-ExchangeOnline -Organization
    initial = next((d.get("name") for d in domains if d.get("isInitial") and d.get("name")), None)
    if initial:
        return initial
    # Fallback: any .onmicrosoft.com domain
    ms_domain = next((d.get("name") for d in domains if ".onmicrosoft.com" in (d.get("name") or "").lower()), None)
    if ms_domain:
        return ms_domain
    # Last resort: the default domain
    return next((d.get("name") for d in domains if d.get("isDefault") and d.get("name")), None)


def _graph_error_detail(exc: Exception) -> str:
    try:
        response = getattr(exc, "response", None)
        if response is not None:
            return response.text or str(exc)
    except Exception:
        pass
    return str(exc)


def _looks_like_duplicate_role_assignment(detail: str) -> bool:
    lowered = str(detail or "").lower()
    return any(
        token in lowered
        for token in (
            "already exists",
            "already assigned",
            "conflicting object",
            "permission being assigned already exists",
            "role assignment already exists",
        )
    )


async def _assign_exchange_admin_role(
    client: GraphClient,
    *,
    service_principal_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Assign the Exchange Administrator Azure AD directory role to the CRA service principal.
    Handles tenants without Exchange Online, inactive role templates, duplicates, and Graph
    propagation timing as non-fatal deployment states.
    """
    exchange_admin_role_id: str | None = None

    try:
        roles_response = await client.get(
            "/directoryRoles",
            params={
                "$filter": "displayName eq 'Exchange Administrator'",
                "$select": "id,displayName,roleTemplateId",
            },
        )
        roles = roles_response.get("value") or []

        if not roles:
            logger.info(
                "[DEPLOYMENT] Exchange Administrator role not active in tenant %s — attempting activation",
                tenant_id,
            )
            try:
                await client.post(
                    "/directoryRoles",
                    json={"roleTemplateId": EXCHANGE_ADMIN_ROLE_TEMPLATE_ID},
                )
                roles_response = await client.get(
                    "/directoryRoles",
                    params={
                        "$filter": "displayName eq 'Exchange Administrator'",
                        "$select": "id,displayName,roleTemplateId",
                    },
                )
                roles = roles_response.get("value") or []
            except Exception as activation_error:
                logger.info(
                    "[DEPLOYMENT] Exchange Online not licensed in tenant %s — Exchange parameters will use service availability detection. Detail: %s",
                    tenant_id,
                    _graph_error_detail(activation_error),
                )
                return {"status": "skipped_no_license", "reason": "no_exchange_license"}

        if not roles:
            logger.info(
                "[DEPLOYMENT] Exchange Administrator role not available in tenant %s — no Exchange Online subscription detected",
                tenant_id,
            )
            return {"status": "skipped_no_license", "reason": "role_not_available"}

        exchange_admin_role_id = roles[0]["id"]
    except Exception as exc:
        detail = _graph_error_detail(exc)
        logger.warning(
            "[DEPLOYMENT] Could not check Exchange Administrator role in tenant %s — unexpected error: %s",
            tenant_id,
            detail,
        )
        return {"status": "failed", "reason": "role_check_failed", "error": detail}

    try:
        existing = await client.get(
            "/roleManagement/directory/roleAssignments",
            params={
                "$filter": (
                    f"principalId eq '{service_principal_id}' and "
                    f"roleDefinitionId eq '{exchange_admin_role_id}'"
                ),
                "$select": "id",
            },
        )
        if existing.get("value"):
            logger.info("[DEPLOYMENT] Exchange Admin role already assigned — skipped")
            return {"status": "already_assigned", "role_definition_id": exchange_admin_role_id}
    except Exception as exc:
        logger.warning(
            "[DEPLOYMENT] Could not check existing Exchange role assignments: %s",
            _graph_error_detail(exc),
        )

    payload = {
        "@odata.type": "#microsoft.graph.unifiedRoleAssignment",
        "principalId": service_principal_id,
        "roleDefinitionId": exchange_admin_role_id,
        "directoryScopeId": "/",
    }
    try:
        result = await client.post("/roleManagement/directory/roleAssignments", json=payload)
        logger.info(
            "[DEPLOYMENT] Exchange Administrator role assigned successfully to service principal %s in tenant %s",
            service_principal_id,
            tenant_id,
        )
        return {"status": "assigned", "role_definition_id": exchange_admin_role_id, "result": result}
    except httpx.HTTPStatusError as exc:
        detail = _graph_error_detail(exc)
        if exc.response.status_code in {400, 409} and _looks_like_duplicate_role_assignment(detail):
            logger.info("[DEPLOYMENT] Exchange Admin role already assigned — skipped")
            return {"status": "already_assigned", "role_definition_id": exchange_admin_role_id}
        logger.warning(
            "[DEPLOYMENT] Exchange Admin role assignment failed — unexpected error: %s",
            detail,
        )
        return {"status": "failed", "role_definition_id": exchange_admin_role_id, "error": detail}
    except Exception as exc:
        detail = _graph_error_detail(exc)
        logger.warning(
            "[DEPLOYMENT] Exchange Admin role assignment failed — unexpected error: %s",
            detail,
        )
        return {"status": "failed", "role_definition_id": exchange_admin_role_id, "error": detail}


async def deploy_tenant_access(
    db: AsyncSession,
    *,
    current_user: User,
    tenant_id: str,
    graph_access_token: str,
    redirect_uri: str | None = None,
) -> dict[str, Any]:
    if tenant_id != current_user.microsoft_tid:
        raise TenantAccessException("Tenant is not available to the current user")
    resolved_redirect_uri = _deployment_redirect_uri(redirect_uri)
    spa_redirect_uri = _deployment_spa_redirect_uri()

    client = GraphClient(access_token=graph_access_token)
    tenant = await _get_or_create_tenant(db, tenant_id=tenant_id, tenant_name=tenant_id)
    tenant.redirect_uri = resolved_redirect_uri
    tenant.admin_consent_url = None
    _update_diagnostics(
        tenant,
        redirect_uri_requested=resolved_redirect_uri,
        spa_redirect_uri_requested=spa_redirect_uri,
        redirect_uri_verified=False,
        stale_consent_url_cleared=True,
        tenant_id_requested=tenant_id,
    )
    _mark_deployment(tenant, step=STEP_GRAPH_TOKEN, status=TENANT_STATUS_DEPLOYING)
    await db.commit()

    try:
        validation = await _assert_graph_token(client, access_token=graph_access_token, tenant_id=tenant_id)
        organization = validation["organization"]
        _update_diagnostics(tenant, tenant_id_graph_organization=organization.get("id"))
        tenant.tenant_name = organization.get("displayName") or tenant.tenant_name
        # Store primary .onmicrosoft.com domain — needed by Exchange PS app-only auth at assessment runtime.
        primary_domain = _extract_primary_domain(organization)
        if primary_domain:
            _update_diagnostics(tenant, primary_domain=primary_domain)
        _mark_deployment(tenant, step=STEP_PERMISSION_ASSIGNMENT, status=TENANT_STATUS_DEPLOYING)
        await db.commit()

        required_access = await build_required_resource_access(client)
        _mark_deployment(tenant, step=STEP_APP_REGISTRATION, status=TENANT_STATUS_DEPLOYING)
        await db.commit()
        if tenant.app_registration_id and tenant.app_client_id:
            existing_app = await _load_existing_application_for_repair(client, tenant=tenant)
            if existing_app:
                _deployment_log(
                    "Repairing Existing Application",
                    application_id=tenant.app_registration_id,
                    client_id=tenant.app_client_id,
                )
                app = existing_app
                _update_diagnostics(tenant, graph_create_payload=None, graph_create_response=None)
            else:
                stale_application_client_id = tenant.app_client_id
                stale_application_object_id = tenant.app_registration_id
                _mark_invalid_deployment(
                    tenant,
                    reason="Stored Azure application identifiers could not be verified in Microsoft Graph",
                    stale_deployment_record_cleared=True,
                )
                await db.commit()
                _mark_deployment(tenant, step=STEP_APP_REGISTRATION, status=TENANT_STATUS_DEPLOYING)
                _deployment_log(
                    "DEPLOYMENT_RECOVERED",
                    tenant_id=tenant_id,
                    recovery_action="create_new_application",
                    stale_application_client_id=stale_application_client_id,
                    stale_application_object_id=stale_application_object_id,
                )
                app = None
        else:
            app = None

        if app is None:
            app = await create_application(
                client,
                display_name=CRA_APPLICATION_DISPLAY_NAME,
                required_resource_access=required_access,
                redirect_uri=resolved_redirect_uri,
                spa_redirect_uri=spa_redirect_uri,
            )
            _deployment_log("Application Created", application_id=app.get("id"), client_id=app.get("appId"))
            _update_diagnostics(
                tenant,
                graph_create_payload=app.get("_graph_create_payload"),
                graph_create_response={key: value for key, value in app.items() if key != "_graph_create_payload"},
            )
            tenant.app_registration_id = app["id"]
            tenant.app_client_id = app["appId"]

        permissions_app, permission_patch_result = await ensure_application_required_resource_access(
            client,
            application_object_id=app["id"],
            required_resource_access=required_access,
        )
        app = {**app, **permissions_app}
        if permission_patch_result:
            _deployment_log("Patching Graph Permissions", application_id=app["id"])
        _update_diagnostics(
            tenant,
            graph_permission_patch_payload=(permission_patch_result or {}).get("payload"),
            graph_permission_patch_response=(permission_patch_result or {}).get("response"),
            graph_required_resource_access=app.get("requiredResourceAccess") or [],
        )

        verified_app, patch_result, redirect_attempts = await ensure_application_redirect_uri(
            client,
            application_object_id=app["id"],
            redirect_uri=resolved_redirect_uri,
            spa_redirect_uri=spa_redirect_uri,
        )
        if patch_result:
            _deployment_log("Patching Redirect URI", application_id=app["id"], redirect_uri=resolved_redirect_uri)
        _deployment_log("Redirect URI Verified", application_id=app["id"], redirect_uri=resolved_redirect_uri)
        _update_diagnostics(
            tenant,
            redirect_uri_verified=True,
            redirect_uri_verification_attempts=redirect_attempts,
            graph_patch_payload=(patch_result or {}).get("payload"),
            graph_patch_response=(patch_result or {}).get("response"),
            graph_read_response=verified_app,
            graph_verified_redirect_uris=(verified_app.get("web") or {}).get("redirectUris") or [],
            graph_verified_spa_redirect_uris=(verified_app.get("spa") or {}).get("redirectUris") or [],
        )
        _mark_deployment(tenant, step=STEP_SERVICE_PRINCIPAL, status=TENANT_STATUS_DEPLOYING)
        await db.commit()

        service_principal = await ensure_service_principal(client, app_id=app["appId"])
        tenant.service_principal_id = service_principal["id"]
        _mark_deployment(tenant, step=STEP_SECRET_CREATION, status=TENANT_STATUS_DEPLOYING)
        await db.commit()

        secret = await create_client_secret(client, application_object_id=app["id"])
        expires_at = parse_graph_datetime(secret.get("endDateTime"))
        store_client_secret(
            tenant,
            secret_text=secret["secretText"],
            secret_id=secret.get("keyId"),
            expires_at=expires_at,
        )

        tenant.granted_permissions = {
            "required_application_permissions": REQUIRED_APPLICATION_PERMISSIONS,
            "assignment_status": "required_resource_access_configured",
            "delegated_scopes_validated": validation["scopes"],
            "graph_service_principal_permissions_discovered": True,
        }
        consent_app, consent_app_by_app_id = await _verify_consent_application(
            client,
            application_object_id=tenant.app_registration_id,
            application_client_id=tenant.app_client_id,
        )
        consent_application_client_id = consent_app["appId"]
        tenant.admin_consent_url = build_admin_consent_url(
            tenant_id=tenant_id,
            client_id=consent_application_client_id,
            redirect_uri=resolved_redirect_uri,
        )
        _validate_consent_client_id(tenant.admin_consent_url, tenant.app_client_id)
        _deployment_log(
            "CONSENT_URL_GENERATED",
            CONSENT_URL_GENERATED=tenant.admin_consent_url,
            CONSENT_CLIENT_ID=consent_application_client_id,
            CONSENT_TENANT_ID=tenant_id,
        )
        _deployment_log(
            "Generating Consent URL",
            CONSENT_CLIENT_ID=consent_application_client_id,
            CONSENT_APPLICATION_OBJECT_ID=tenant.app_registration_id,
            CONSENT_SERVICE_PRINCIPAL_ID=tenant.service_principal_id,
            CONSENT_URL=tenant.admin_consent_url,
            TENANT_ID=tenant_id,
            redirect_uri=resolved_redirect_uri,
        )
        _update_diagnostics(
            tenant,
            CONSENT_CLIENT_ID=consent_application_client_id,
            CONSENT_APPLICATION_OBJECT_ID=tenant.app_registration_id,
            CONSENT_SERVICE_PRINCIPAL_ID=tenant.service_principal_id,
            CONSENT_URL=tenant.admin_consent_url,
            TENANT_ID=tenant_id,
            consent_client_id=consent_application_client_id,
            consent_application_object_id=tenant.app_registration_id,
            consent_service_principal_id=tenant.service_principal_id,
            consent_url=tenant.admin_consent_url,
            consent_url_generated=True,
            graph_consent_application_read_response=consent_app,
            graph_consent_application_appid_lookup_response=consent_app_by_app_id,
        )
        tenant.consent_status = "pending_admin_consent"
        _mark_deployment(tenant, step=STEP_CONSENT_GENERATION, status=TENANT_STATUS_CONSENT_REQUIRED)
        await audit_service.log_event(
            db,
            tenant_id=tenant_id,
            event=AuditEvent.TENANT_CONNECTED,
            action="tenant.deploy_access",
            user_id=current_user.id,
            resource="connected_tenants",
            metadata={
                "tenant_id": tenant_id,
                "app_registration_id": tenant.app_registration_id,
                "app_client_id": tenant.app_client_id,
                "service_principal_id": tenant.service_principal_id,
                "secret_id": tenant.secret_id,
                "secret_version": tenant.secret_version,
                "graph_token": validation["diagnostics"],
                "redirect_uri": tenant.redirect_uri,
                "deployment_diagnostics": tenant.deployment_diagnostics,
            },
        )
        await db.commit()
        await db.refresh(tenant)
        return deployment_payload(tenant)
    except Exception as exc:
        _mark_deployment(
            tenant,
            step=tenant.deployment_step or STEP_GRAPH_TOKEN,
            status=TENANT_STATUS_FAILED,
            error=str(exc),
        )
        await audit_service.log_event(
            db,
            tenant_id=tenant_id,
            event=AuditEvent.TENANT_DISCONNECTED,
            action="tenant.deploy_access_failed",
            user_id=current_user.id,
            resource="connected_tenants",
            metadata={"error": str(exc), "failure_id": str(uuid.uuid4())},
        )
        await db.commit()
        if isinstance(exc, (AuthException, TenantAccessException, BusinessLogicException)):
            raise
        raise BusinessLogicException("Tenant deployment failed", details={"error": str(exc)}) from exc


async def validate_tenant_deployment(
    db: AsyncSession,
    *,
    current_user: User,
    graph_access_token: str,
) -> dict[str, Any]:
    tenant_id = current_user.microsoft_tid
    result = await db.execute(select(ConnectedTenant).where(ConnectedTenant.tenant_id == tenant_id))
    tenant = result.scalars().first()
    if tenant is None:
        raise BusinessLogicException("Tenant deployment has not been started")

    client = GraphClient(access_token=graph_access_token)
    await _assert_graph_token(client, access_token=graph_access_token, tenant_id=tenant_id)
    _deployment_log(
        "DEPLOYMENT_VALIDATION_START",
        tenant_id=tenant_id,
        application_client_id=tenant.app_client_id,
        application_object_id=tenant.app_registration_id,
        service_principal_id=tenant.service_principal_id,
    )

    expected_redirect_uri = tenant.redirect_uri or build_redirect_uri(settings.cra_frontend_url)
    expected_spa_redirect_uri = _deployment_spa_redirect_uri()
    tenant.redirect_uri = expected_redirect_uri
    app = await _resolve_verified_application(
        client,
        application_object_id=tenant.app_registration_id,
        application_client_id=tenant.app_client_id,
    )
    stale_detected = app is None and bool(tenant.app_registration_id or tenant.app_client_id)
    required_access = await build_required_resource_access(client)

    if app is None:
        reason = "Azure application does not exist or stored identifiers do not match Microsoft Graph"
        _mark_invalid_deployment(tenant, reason=reason)
        await db.commit()

        app = await create_application(
            client,
            display_name=CRA_APPLICATION_DISPLAY_NAME,
            required_resource_access=required_access,
            redirect_uri=expected_redirect_uri,
            spa_redirect_uri=expected_spa_redirect_uri,
        )
        tenant.app_registration_id = app["id"]
        tenant.app_client_id = app["appId"]
        _update_diagnostics(
            tenant,
            recovery_created_application=True,
            graph_create_payload=app.get("_graph_create_payload"),
            graph_create_response={key: value for key, value in app.items() if key != "_graph_create_payload"},
        )
        _deployment_log(
            "DEPLOYMENT_RECOVERED",
            tenant_id=tenant_id,
            application_client_id=app.get("appId"),
            application_object_id=app.get("id"),
            recovery_reason=reason,
        )

    verified_app, patch_result, redirect_attempts = await ensure_application_redirect_uri(
        client,
        application_object_id=app["id"],
        redirect_uri=expected_redirect_uri,
        spa_redirect_uri=expected_spa_redirect_uri,
    )
    permissions_app, permission_patch_result = await ensure_application_required_resource_access(
        client,
        application_object_id=verified_app["id"],
        required_resource_access=required_access,
    )
    verified_app = {**verified_app, **permissions_app}
    tenant.app_registration_id = verified_app["id"]
    tenant.app_client_id = verified_app["appId"]
    redirect_uris = list((verified_app.get("web") or {}).get("redirectUris") or [])
    spa_redirect_uris = list((verified_app.get("spa") or {}).get("redirectUris") or [])
    web_redirect_valid = expected_spa_redirect_uri == expected_redirect_uri or expected_redirect_uri in redirect_uris
    spa_redirect_valid = expected_spa_redirect_uri in spa_redirect_uris
    redirect_uri_valid = web_redirect_valid and spa_redirect_valid
    _update_diagnostics(
        tenant,
        validation_redirect_uri=expected_redirect_uri,
        validation_spa_redirect_uri=expected_spa_redirect_uri,
        validation_redirect_uri_valid=redirect_uri_valid,
        validation_redirect_uri_attempts=redirect_attempts,
        validation_patch_result=patch_result,
        validation_permission_patch_result=permission_patch_result,
        validation_graph_application=verified_app,
        stale_deployment_detected=stale_detected,
    )

    service_principal = None
    if tenant.service_principal_id:
        try:
            service_principal = await get_service_principal(
                client,
                service_principal_id=tenant.service_principal_id,
            )
        except Exception as exc:
            if not _is_graph_not_found(exc):
                raise
            _update_diagnostics(tenant, deleted_service_principal_id=tenant.service_principal_id)
            tenant.service_principal_id = None

    if not service_principal or service_principal.get("appId") != verified_app["appId"]:
        service_principal = await ensure_service_principal(client, app_id=verified_app["appId"])
        tenant.service_principal_id = service_principal["id"]

    if not tenant.secret_id:
        secret = await create_client_secret(client, application_object_id=verified_app["id"])
        expires_at = parse_graph_datetime(secret.get("endDateTime"))
        store_client_secret(
            tenant,
            secret_text=secret["secretText"],
            secret_id=secret.get("keyId"),
            expires_at=expires_at,
        )

    consent_app, consent_app_by_app_id = await _verify_consent_application(
        client,
        application_object_id=verified_app["id"],
        application_client_id=verified_app["appId"],
    )
    tenant.admin_consent_url = build_admin_consent_url(
        tenant_id=tenant_id,
        client_id=consent_app["appId"],
        redirect_uri=expected_redirect_uri,
    )
    _validate_consent_client_id(tenant.admin_consent_url, verified_app["appId"])
    _deployment_log(
        "CONSENT_URL_GENERATED",
        tenant_id=tenant_id,
        CONSENT_CLIENT_ID=consent_app["appId"],
        CONSENT_URL_GENERATED=tenant.admin_consent_url,
    )
    _update_diagnostics(
        tenant,
        graph_consent_application_read_response=consent_app,
        graph_consent_application_appid_lookup_response=consent_app_by_app_id,
        consent_client_id=consent_app["appId"],
        consent_url=tenant.admin_consent_url,
        consent_url_generated=True,
    )

    tenant.consent_status = "pending_admin_consent"
    _mark_deployment(tenant, step=STEP_CONSENT_GENERATION, status=TENANT_STATUS_CONSENT_REQUIRED)
    await db.commit()
    await db.refresh(tenant)

    app_exists = bool(tenant.app_registration_id and tenant.app_client_id)
    service_principal_exists = bool(tenant.service_principal_id)
    return {
        "tenant_id": tenant.tenant_id,
        "deployment_valid": bool(app_exists and service_principal_exists and redirect_uri_valid),
        "app_exists": app_exists,
        "app_id": tenant.app_client_id,
        "object_id": tenant.app_registration_id,
        "service_principal_exists": service_principal_exists,
        "redirect_uri_valid": redirect_uri_valid,
        "consent_url": tenant.admin_consent_url,
    }


async def validate_admin_consent(
    db: AsyncSession,
    *,
    current_user: User,
    tenant_id: str,
    graph_access_token: str,
) -> dict[str, Any]:
    if tenant_id != current_user.microsoft_tid:
        raise TenantAccessException("Tenant is not available to the current user")
    result = await db.execute(select(ConnectedTenant).where(ConnectedTenant.tenant_id == tenant_id))
    tenant = result.scalars().first()
    if tenant is None or not tenant.service_principal_id:
        raise BusinessLogicException("Tenant deployment has not created a service principal")
    client = GraphClient(access_token=graph_access_token)
    await _assert_graph_token(client, access_token=graph_access_token, tenant_id=tenant_id)
    _mark_deployment(tenant, step=STEP_DEPLOYMENT_VALIDATION, status=TENANT_STATUS_VALIDATING)
    await db.commit()

    # Re-verify service principal exists and is correct before validation
    # This handles cases where the stored ID might be stale or incorrect
    if tenant.app_client_id:
        try:
            verified_sp = await get_service_principal(
                client,
                service_principal_id=tenant.service_principal_id,
            )
            if verified_sp.get("appId") != tenant.app_client_id:
                _deployment_log(
                    "SERVICE_PRINCIPAL_APP_ID_MISMATCH",
                    stored_sp_id=tenant.service_principal_id,
                    stored_app_client_id=tenant.app_client_id,
                    graph_sp_app_id=verified_sp.get("appId"),
                )
                sp_by_app_id = await get_service_principal_by_app_id(client, app_id=tenant.app_client_id)
                if sp_by_app_id and sp_by_app_id.get("id") != tenant.service_principal_id:
                    _deployment_log(
                        "CORRECTING_SERVICE_PRINCIPAL_ID",
                        old_sp_id=tenant.service_principal_id,
                        new_sp_id=sp_by_app_id.get("id"),
                        app_client_id=tenant.app_client_id,
                    )
                    tenant.service_principal_id = sp_by_app_id["id"]
                    await db.commit()
        except Exception as exc:
            if not _is_graph_not_found(exc):
                raise
            _deployment_log(
                "SERVICE_PRINCIPAL_NOT_FOUND_IN_TENANT",
                stored_sp_id=tenant.service_principal_id,
                app_client_id=tenant.app_client_id,
            )

    validation = await validate_deployment_with_retry(client, tenant, delay_seconds=10)
    tenant.granted_permissions = {
        **(tenant.granted_permissions or {}),
        "validation": validation.details,
        "checks": {
            "app_registration_exists": validation.app_registration_exists,
            "service_principal_exists": validation.service_principal_exists,
            "secret_exists": validation.secret_exists,
            "permissions_assigned": validation.permissions_assigned,
            "admin_consent_granted": validation.admin_consent_granted,
        },
    }

    if not validation.is_active:
        tenant.consent_status = "pending_admin_consent"
        _mark_deployment(
            tenant,
            step=STEP_DEPLOYMENT_VALIDATION,
            status=TENANT_STATUS_FAILED,
            error="Microsoft Graph deployment validation failed",
        )
        await db.commit()
        raise BusinessLogicException(
            "Microsoft Graph deployment validation failed",
            details=tenant.granted_permissions["checks"],
        )
    tenant.consent_status = "connected"
    _mark_deployment(tenant, step=STEP_DEPLOYMENT_VALIDATION, status=TENANT_STATUS_ACTIVE)
    tenant.consent_granted_by = current_user.email
    tenant.consent_granted_at = datetime.utcnow()

    # Assign the Exchange Administrator Azure AD directory role to the service principal so that
    # Exchange PS app-only auth (Connect-ExchangeOnline -AccessToken) can run Exchange cmdlets.
    # Non-fatal: if the admin's token lacks RoleManagement.ReadWrite.Directory this will 403 and we log only.
    if tenant.service_principal_id:
        try:
            role_result = await _assign_exchange_admin_role(
                client,
                service_principal_id=tenant.service_principal_id,
                tenant_id=tenant_id,
            )
            _update_diagnostics(tenant, exchange_admin_role_assignment=role_result)
        except Exception as role_exc:
            logger.warning(
                "[DEPLOYMENT] Exchange Admin role assignment failed — unexpected error: %s",
                _graph_error_detail(role_exc),
                extra={"tenant_id": tenant_id, "service_principal_id": tenant.service_principal_id},
            )
            _update_diagnostics(tenant, exchange_admin_role_assignment={"status": "failed", "error": _graph_error_detail(role_exc)})

    await audit_service.log_event(
        db,
        tenant_id=tenant_id,
        event=AuditEvent.TENANT_CONNECTED,
        action="tenant.admin_consent_validated",
        user_id=current_user.id,
        resource="connected_tenants",
        metadata=validation.details,
    )
    await db.commit()
    await db.refresh(tenant)
    return deployment_payload(tenant)


async def repair_tenant_deployment(
    db: AsyncSession,
    *,
    current_user: User,
    graph_access_token: str,
) -> dict[str, Any]:
    """
    Patch the existing app registration to include Exchange + Teams permissions,
    attempt to assign the Exchange Admin role, and return a fresh admin consent URL.
    Used by tenants that were connected before Exchange/Teams permissions were added.
    """
    tenant_id = current_user.microsoft_tid
    result = await db.execute(select(ConnectedTenant).where(ConnectedTenant.tenant_id == tenant_id))
    tenant = result.scalars().first()
    if tenant is None or not tenant.app_registration_id or not tenant.app_client_id:
        raise BusinessLogicException("Tenant deployment has not been completed — run the full deployment first")

    client = GraphClient(access_token=graph_access_token)
    validation = await _assert_graph_token(client, access_token=graph_access_token, tenant_id=tenant_id)
    organization = validation["organization"]

    # Refresh primary domain in case it was missing from an older deployment
    primary_domain = _extract_primary_domain(organization)
    if primary_domain:
        _update_diagnostics(tenant, primary_domain=primary_domain)

    required_access = await build_required_resource_access(client)
    _permissions_app, patch_result = await ensure_application_required_resource_access(
        client,
        application_object_id=tenant.app_registration_id,
        required_resource_access=required_access,
    )
    if patch_result:
        _deployment_log("REPAIR_PERMISSIONS_PATCHED", application_id=tenant.app_registration_id)
        _update_diagnostics(tenant, repair_permission_patch=True)
    else:
        _deployment_log("REPAIR_PERMISSIONS_ALREADY_CURRENT", application_id=tenant.app_registration_id)

    # Try role assignment with the admin's delegated token
    if tenant.service_principal_id:
        try:
            role_result = await _assign_exchange_admin_role(
                client,
                service_principal_id=tenant.service_principal_id,
                tenant_id=tenant_id,
            )
            _update_diagnostics(tenant, exchange_admin_role_assignment=role_result)
        except Exception as role_exc:
            logger.warning("[DEPLOYMENT] Repair: Exchange Admin role assignment failed — unexpected error: %s", _graph_error_detail(role_exc))
            _update_diagnostics(tenant, exchange_admin_role_assignment={"status": "failed", "error": _graph_error_detail(role_exc)})

    expected_redirect_uri = tenant.redirect_uri or build_redirect_uri(settings.cra_frontend_url)
    consent_url = build_admin_consent_url(
        tenant_id=tenant_id,
        client_id=tenant.app_client_id,
        redirect_uri=expected_redirect_uri,
    )
    tenant.admin_consent_url = consent_url
    tenant.consent_status = "pending_admin_consent"
    _update_diagnostics(tenant, repair_consent_url_regenerated=True)
    await db.commit()
    await db.refresh(tenant)
    return {
        "needs_reconsent": True,
        "consent_url": consent_url,
        "tenant_id": tenant_id,
        "app_client_id": tenant.app_client_id,
        "permissions_patched": bool(patch_result),
        "primary_domain": primary_domain,
        "exchange_admin_role": _exchange_admin_role_payload_status(tenant),
    }


def _exchange_admin_role_payload_status(tenant: ConnectedTenant) -> str | None:
    diagnostics = tenant.deployment_diagnostics if isinstance(tenant.deployment_diagnostics, dict) else {}
    assignment = diagnostics.get("exchange_admin_role_assignment")
    if not isinstance(assignment, dict):
        return None
    status = str(assignment.get("status") or "").strip().lower()
    reason = str(assignment.get("reason") or "").strip().lower()
    if status in {"assigned", "already_assigned", "failed"}:
        return status
    if status == "skipped_no_license" or reason in {"no_exchange_license", "role_not_available"}:
        return "skipped_no_license"
    if status in {"skipped", "role_not_available"}:
        return "skipped_no_license"
    return status or None


def deployment_payload(tenant: ConnectedTenant) -> dict[str, Any]:
    return {
        "exchange_admin_role": _exchange_admin_role_payload_status(tenant),
        "tenant_id": tenant.tenant_id,
        "tenant_name": tenant.tenant_name,
        "status": tenant.status,
        "deployment_status": tenant.deployment_status,
        "consent_status": tenant.consent_status,
        "app_registration_id": tenant.app_registration_id,
        "app_client_id": tenant.app_client_id,
        "application_object_id": tenant.app_registration_id,
        "application_client_id": tenant.app_client_id,
        "service_principal_id": tenant.service_principal_id,
        "admin_consent_url": tenant.admin_consent_url,
        "consent_url": tenant.admin_consent_url,
        "redirect_uri": tenant.redirect_uri,
        "deployment_diagnostics": tenant.deployment_diagnostics,
        "granted_permissions": tenant.granted_permissions,
        "secret_id": tenant.secret_id,
        "secret_expires_at": tenant.secret_expires_at,
        "secret_expiration": tenant.secret_expires_at,
        "deployment_step": tenant.deployment_step,
        "deployment_timestamp": tenant.deployment_timestamp,
        "deployment_error": tenant.deployment_error,
    }
