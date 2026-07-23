from __future__ import annotations

import asyncio
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.db.models.tenant import ConnectedTenant
from app.services.graph.graph_client import GraphClient
from app.services.tenant_secret_service import decrypt_client_secret
from app.utils.logger import logger


GRAPH_SCOPE = "https://graph.microsoft.com/.default"

_TOKEN_CACHE: dict[str, tuple[str, float]] = {}

COPILOT_PREREQUISITE_SKU_PARTS = {
    "ENTERPRISEPACK",
    "ENTERPRISEPREMIUM",
    "SPE_E3",
    "SPE_E5",
    "O365_BUSINESS_PREMIUM",
    "SPB",
    "STANDARDWOFFPACK",
    "M365EDU_A3_FACULTY",
    "M365EDU_A5_FACULTY",
}


class GraphCollectionError(RuntimeError):
    pass


def _log(message: str, **context: Any) -> None:
    logger.info("[ASSESSMENT] %s %s", message, context)


async def get_app_graph_token(tenant: ConnectedTenant) -> str:
    if not tenant.app_client_id or not tenant.encrypted_client_secret:
        raise GraphCollectionError("Tenant is missing CRA App Registration credentials")

    now_ts = datetime.now(timezone.utc).timestamp()
    cache_key = f"{tenant.tenant_id}:{tenant.app_client_id}"
    cached = _TOKEN_CACHE.get(cache_key)
    if cached and cached[1] > now_ts + 120:
        return cached[0]

    secret = decrypt_client_secret(tenant)
    token_url = f"https://login.microsoftonline.com/{tenant.tenant_id}/oauth2/v2.0/token"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            token_url,
            data={
                "client_id": tenant.app_client_id,
                "client_secret": secret,
                "scope": GRAPH_SCOPE,
                "grant_type": "client_credentials",
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                error_payload: dict[str, Any] = response.json()
            except ValueError:
                error_payload = {"error": response.text}
            raise GraphCollectionError(
                f"Microsoft Graph token request failed ({response.status_code}): {error_payload}"
            ) from exc
        payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise GraphCollectionError("Microsoft Graph token response did not include access_token")
    expires_in = int(payload.get("expires_in") or 3600)
    _TOKEN_CACHE[cache_key] = (token, now_ts + expires_in)
    return token


async def _graph_get_retry(
    client: GraphClient,
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
    attempts: int = 4,
) -> dict[str, Any]:
    """GET a Graph endpoint with retry/backoff on throttling (429), transient 5xx, and
    connection errors. Without this, a single throttled or transient call aborts an entire
    collector (e.g. the per-team enumeration used by the Teams controls), which surfaces as
    the generic 'could not be automatically retrieved' fallback."""
    delay = 2.0
    for attempt in range(attempts):
        try:
            return await client.get(endpoint, params=params)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                retry_after = (exc.response.headers.get("Retry-After") or "").strip()
                wait = float(retry_after) if retry_after.isdigit() else delay
                await asyncio.sleep(min(wait, 30.0))
                delay *= 2
                continue
            raise
        except httpx.RequestError:
            if attempt < attempts - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
    return await client.get(endpoint, params=params)


async def _get_all(client: GraphClient, endpoint: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    values: list[dict[str, Any]] = []
    page = await _graph_get_retry(client, endpoint, params=params)
    values.extend(page.get("value") or [])
    next_link = page.get("@odata.nextLink")
    while next_link:
        page = await _graph_get_retry(client, next_link)
        values.extend(page.get("value") or [])
        next_link = page.get("@odata.nextLink")
    return {"value": values}


async def _graph_get_text(tenant: ConnectedTenant, endpoint: str) -> dict[str, Any]:
    token = await get_app_graph_token(tenant)
    url = endpoint if endpoint.startswith("https://") else f"https://graph.microsoft.com/v1.0/{endpoint.lstrip('/')}"
    _log("GRAPH_REQUEST", endpoint=endpoint)
    delay = 2.0
    response = None
    for attempt in range(3):
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            except httpx.RequestError as exc:
                if attempt < 2:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                return {
                    "ok": False,
                    "status_code": None,
                    "error": {
                        "code": exc.__class__.__name__,
                        "message": str(exc),
                    },
                    "text": "",
                }
        if response.is_error and response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
            await asyncio.sleep(delay)
            delay *= 2
            continue
        break
    if response.is_error:
        try:
            error_payload: dict[str, Any] = response.json()
        except ValueError:
            error_payload = {"error": {"message": response.text}}
        return {
            "ok": False,
            "status_code": response.status_code,
            "error": error_payload.get("error") or error_payload,
            "text": response.text,
        }
    return {
        "ok": True,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "text": response.text,
    }


async def _graph_get_json_or_error(tenant: ConnectedTenant, endpoint: str) -> dict[str, Any]:
    client = await _graph_client(tenant)
    try:
        return {"ok": True, "response": await client.get(endpoint)}
    except httpx.HTTPStatusError as exc:
        try:
            error_payload: dict[str, Any] = exc.response.json()
        except ValueError:
            error_payload = {"error": {"message": exc.response.text}}
        return {
            "ok": False,
            "status_code": exc.response.status_code,
            "error": error_payload.get("error") or error_payload,
        }


def _error_message(response: dict[str, Any] | None) -> str:
    error = (response or {}).get("error") or {}
    if isinstance(error, dict):
        nested = error.get("error") if isinstance(error.get("error"), dict) else {}
        return str(error.get("message") or nested.get("message") or error.get("code") or response)
    return str(error or response or "Unknown collection error")


def _collection_error_result(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    endpoint: str,
    required_api: str,
    required_permissions: list[str],
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
    response: dict[str, Any] | None = None,
    command: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    message = reason or _error_message(response)
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=message,
        extra={
            "tenant_id": tenant.tenant_id,
            "collection_status": "COLLECTION_ERROR",
            "required_api": required_api,
            "required_permissions": required_permissions,
            "required_powershell_command": command,
            "graph_endpoint": endpoint,
            "graph_response": response,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="collection_error",
        severity=severity,
        actual_value={
            "collection_status": "COLLECTION_ERROR",
            "reason": message,
            "required_api": required_api,
            "required_permissions": required_permissions,
            "required_powershell_command": command,
        },
        expected_value=expected_value,
        finding=message,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"graph_response": response or {}, "collection_error": True},
        graph_calls=1 if endpoint else 0,
        scoring_weight=scoring_weight,
    )


def _csv_rows(report: dict[str, Any]) -> list[dict[str, str]]:
    text = str(report.get("text") or "").lstrip("\ufeff")
    if not text.strip():
        return []
    return list(csv.DictReader(StringIO(text)))


def _int_value(row: dict[str, Any], key: str) -> int:
    raw = row.get(key)
    if raw in {None, ""}:
        return 0
    try:
        return int(float(str(raw).replace(",", "")))
    except ValueError:
        return 0


def _float_value(row: dict[str, Any], key: str) -> float:
    raw = row.get(key)
    if raw in {None, ""}:
        return 0.0
    try:
        return float(str(raw).replace(",", ""))
    except ValueError:
        return 0.0


def _has_activity(row: dict[str, Any], *, date_field: str = "Last Activity Date") -> bool:
    if row.get(date_field):
        return True
    activity_fields = [
        key
        for key in row
        if key.endswith(" Count")
        or key in {
            "Active Users",
            "Active Channels",
            "Active File Count",
            "Page View Count",
            "Visited Page Count",
            "Viewed Or Edited File Count",
            "Synced File Count",
        }
    ]
    return any(_float_value(row, key) > 0 for key in activity_fields)


def _has_recent_activity(
    row: dict[str, Any], *, within_days: int, date_field: str = "Last Activity Date"
) -> bool:
    """A user/site is considered active only if its Last Activity Date is within
    the last ``within_days`` days from today. Rows with no parseable activity
    date are treated as inactive."""
    raw = str(row.get(date_field) or "").strip()
    if not raw:
        return False
    last_activity: datetime | None = None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            last_activity = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue
    if last_activity is None:
        return False
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=within_days)
    return last_activity >= cutoff


def _active_email_activity_rows(rows: list[dict[str, Any]], *, within_days: int = 60) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if str(row.get("Is Deleted") or "").lower() != "true"
        and _has_recent_activity(row, within_days=within_days)
    ]


def _collector_result(
    *,
    parameter_key: str,
    status: str,
    severity: str,
    actual_value: Any,
    expected_value: str,
    finding: str,
    graph_endpoint: str,
    evidence: dict[str, Any],
    raw_response: dict[str, Any],
    graph_calls: int,
    scoring_weight: float,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    remediation = evidence.get("remediation") or evidence.get("remediation_steps") or "Review the generated recommendation for remediation guidance."
    return {
        "parameter_key": parameter_key,
        "status": status,
        "severity": severity if status == "fail" else "info",
        "raw_value": {
            "parameter_key": parameter_key,
            "collector_type": "graph",
            "collector_name": f"graph.{parameter_key}",
            "graph_endpoint": graph_endpoint,
            "actual_value": actual_value,
            "expected_value": expected_value,
            "remediation": remediation,
            "evidence": evidence,
            "raw_response": raw_response,
            "collected_at": now,
        },
        "evaluated_value": finding,
        "score_contribution": 0.0 if status == "pass" else scoring_weight,
        "warnings": [],
        "errors": [],
        "telemetry": {
            "graph_calls": graph_calls,
            "graph_endpoint": graph_endpoint,
            "collector_name": f"graph.{parameter_key}",
            "actual_value": actual_value,
            "expected_value": expected_value,
            "remediation": remediation,
            "raw_evidence_json": evidence,
            "collected_at": now,
        },
    }


async def _graph_client(tenant: ConnectedTenant) -> GraphClient:
    token = await get_app_graph_token(tenant)
    return GraphClient(access_token=token)


def _evaluation_evidence(
    *,
    pass_criteria: str,
    fail_criteria: str,
    reasoning: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "pass_criteria": pass_criteria,
        "fail_criteria": fail_criteria,
        "reasoning": reasoning,
        **(extra or {}),
    }


def _percent(part: int, total: int) -> float:
    return round((part / total * 100), 2) if total else 0.0


def _auth_method_name(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("@odata.type") or item.get("displayName") or "unknown")


async def _conditional_access_policies(tenant: ConnectedTenant) -> dict[str, Any]:
    client = await _graph_client(tenant)
    endpoint = "/identity/conditionalAccess/policies"
    params = {"$select": "id,displayName,state,conditions,grantControls"}
    _log("GRAPH_REQUEST", endpoint=endpoint, params=params)
    response = await _get_all(client, endpoint, params=params)
    _log("GRAPH_RESPONSE", endpoint=endpoint, count=len(response.get("value") or []))
    return response


async def _subscribed_skus(tenant: ConnectedTenant) -> dict[str, Any]:
    client = await _graph_client(tenant)
    endpoint = "/subscribedSkus"
    params = {"$select": "skuId,skuPartNumber,prepaidUnits,consumedUnits,servicePlans"}
    _log("GRAPH_REQUEST", endpoint=endpoint, params=params)
    response = await _get_all(client, endpoint, params=params)
    _log("GRAPH_RESPONSE", endpoint=endpoint, count=len(response.get("value") or []))
    return response


async def _authentication_methods_policy(tenant: ConnectedTenant) -> dict[str, Any]:
    client = await _graph_client(tenant)
    endpoint = "https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy"
    _log("GRAPH_REQUEST", endpoint=endpoint)
    response = await client.get(endpoint)
    _log(
        "GRAPH_RESPONSE",
        endpoint=endpoint,
        count=len(response.get("authenticationMethodConfigurations") or []),
    )
    return response


async def _user_registration_details(tenant: ConnectedTenant) -> dict[str, Any]:
    client = await _graph_client(tenant)
    endpoint = "/reports/authenticationMethods/userRegistrationDetails"
    _log("GRAPH_REQUEST", endpoint=endpoint)
    try:
        response = await _get_all(client, endpoint)
    except httpx.HTTPStatusError as exc:
        try:
            error_payload: dict[str, Any] = exc.response.json()
        except ValueError:
            error_payload = {"error": {"message": exc.response.text}}
        response = {
            "value": [],
            "error": error_payload.get("error") or error_payload,
            "status_code": exc.response.status_code,
        }
    _log("GRAPH_RESPONSE", endpoint=endpoint, count=len(response.get("value") or []))
    return response


async def _user_authentication_methods(client: GraphClient, user_id: str) -> dict[str, Any]:
    endpoint = f"/users/{user_id}/authentication/methods"
    return await _get_all(client, endpoint)


async def collect_global_administrator_accounts(tenant: ConnectedTenant) -> dict[str, Any]:
    _log("COLLECTOR_STARTED", parameter_key="global_administrator_accounts", tenant_id=tenant.tenant_id)
    client = await _graph_client(tenant)

    role_endpoint = "/directoryRoles"
    role_params = {
        "$filter": "displayName eq 'Global Administrator'",
        "$select": "id,displayName,roleTemplateId",
    }
    _log("GRAPH_REQUEST", endpoint=role_endpoint, params=role_params)
    role_response = await client.get(role_endpoint, params=role_params)
    role_values = role_response.get("value") or []
    _log("GRAPH_RESPONSE", endpoint=role_endpoint, count=len(role_values))

    role = role_values[0] if role_values else None
    members: list[dict[str, Any]] = []
    member_response: dict[str, Any] = {"value": []}
    if role:
        member_endpoint = f"/directoryRoles/{role['id']}/members"
        member_params = {"$select": "id,displayName,userPrincipalName,mail"}
        _log("GRAPH_REQUEST", endpoint=member_endpoint, params=member_params)
        member_response = await client.get(member_endpoint, params=member_params)
        members = member_response.get("value") or []
        _log("GRAPH_RESPONSE", endpoint=member_endpoint, count=len(members))

    admin_count = len(members)
    status = "pass" if 2 <= admin_count <= 5 else "fail"
    severity = "critical" if status == "fail" else "info"
    evaluated_value = f"{admin_count} Global Administrator account(s) found"
    now = datetime.now(timezone.utc).isoformat()

    evidence = {
        "parameter_key": "global_administrator_accounts",
        "tenant_id": tenant.tenant_id,
        "role": role,
        "admin_count": admin_count,
        "members": members,
        "collected_at": now,
        "criteria": {
            "pass": "Global Administrator count is between 2 and 5 inclusive",
            "fail": "Global Administrator count is less than 2 or greater than 5",
        },
    }
    raw_response = {
        "directoryRoles": role_response,
        "members": member_response,
    }
    return _collector_result(
        parameter_key="global_administrator_accounts",
        status=status,
        severity=severity,
        actual_value=admin_count,
        expected_value="2-5 Global Administrator accounts",
        finding=evaluated_value,
        graph_endpoint="/directoryRoles + /directoryRoles/{id}/members",
        evidence=evidence,
        raw_response=raw_response,
        graph_calls=1 + (1 if role else 0),
        scoring_weight=5.0,
    )


async def _collect_users(tenant: ConnectedTenant) -> dict[str, Any]:
    client = await _graph_client(tenant)
    endpoint = "/users"
    params = {
        "$select": "id,displayName,userPrincipalName,mail,userType,accountEnabled,jobTitle,department,assignedLicenses,assignedPlans",
        "$top": "999",
    }
    _log("GRAPH_REQUEST", endpoint=endpoint, params=params)
    response = await _get_all(client, endpoint, params=params)
    users = response.get("value") or []
    _log("GRAPH_RESPONSE", endpoint=endpoint, count=len(users))
    return response


async def collect_guest_users_count(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "guest_users_count"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    raw_response = {"users": await _collect_users(tenant)}
    users = raw_response["users"].get("value") or []
    guests = [user for user in users if str(user.get("userType") or "").lower() == "guest"]
    total = len(users)
    guest_count = len(guests)
    ratio = round((guest_count / total * 100), 2) if total else 0.0
    status = "pass" if ratio < 15 else "fail"
    evidence = {
        "tenant_id": tenant.tenant_id,
        "guest_count": guest_count,
        "total_users": total,
        "guest_ratio_percent": ratio,
        "guests": guests,
    }
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="medium",
        actual_value={"guest_count": guest_count, "total_users": total, "guest_ratio_percent": ratio},
        expected_value="<15% guest users",
        finding=f"{guest_count} guest user(s) detected out of {total} total user(s) ({ratio}%)",
        graph_endpoint="/users?$select=id,displayName,userPrincipalName,mail,userType",
        evidence=evidence,
        raw_response=raw_response,
        graph_calls=1,
        scoring_weight=3.0,
    )


async def collect_account_enabled(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "account_enabled"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    raw_response = {"users": await _collect_users(tenant)}
    users = raw_response["users"].get("value") or []
    enabled = [user for user in users if user.get("accountEnabled") is True]
    total = len(users)
    enabled_count = len(enabled)
    percentage = round((enabled_count / total * 100), 2) if total else 0.0
    status = "pass" if percentage > 85 else "fail"
    evidence = {
        "tenant_id": tenant.tenant_id,
        "enabled_count": enabled_count,
        "total_users": total,
        "enabled_percent": percentage,
        "users": users,
    }
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="low",
        actual_value={"enabled_count": enabled_count, "total_users": total, "enabled_percent": percentage},
        expected_value=">85% enabled accounts",
        finding=f"{enabled_count} enabled account(s) detected out of {total} total account(s) ({percentage}%)",
        graph_endpoint="/users?$select=id,displayName,userPrincipalName,accountEnabled,userType",
        evidence=evidence,
        raw_response=raw_response,
        graph_calls=1,
        scoring_weight=2.0,
    )


async def collect_user_information(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "user_information"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    raw_response = {"users": await _collect_users(tenant)}
    users = raw_response["users"].get("value") or []
    required_fields = ["displayName", "userPrincipalName", "mail"]
    incomplete = [
        {
            "id": user.get("id"),
            "displayName": user.get("displayName"),
            "userPrincipalName": user.get("userPrincipalName"),
            "missingFields": [field for field in required_fields if not user.get(field)],
        }
        for user in users
        if any(not user.get(field) for field in required_fields)
    ]
    complete_count = len(users) - len(incomplete)
    status = "pass" if not incomplete else "fail"
    evidence = {
        "tenant_id": tenant.tenant_id,
        "required_fields": required_fields,
        "complete_users": complete_count,
        "total_users": len(users),
        "incomplete_users": incomplete,
    }
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="low",
        actual_value={"complete_users": complete_count, "total_users": len(users), "incomplete_users": len(incomplete)},
        expected_value="All users have displayName, userPrincipalName, and mail populated",
        finding=f"{len(incomplete)} user account(s) have incomplete required profile information",
        graph_endpoint="/users?$select=id,displayName,userPrincipalName,mail,jobTitle,department",
        evidence=evidence,
        raw_response=raw_response,
        graph_calls=1,
        scoring_weight=2.0,
    )


async def _authorization_policy(tenant: ConnectedTenant) -> dict[str, Any]:
    client = await _graph_client(tenant)
    endpoint = "/policies/authorizationPolicy"
    params = {
        "$select": "id,allowInvitesFrom,defaultUserRolePermissions",
    }
    _log("GRAPH_REQUEST", endpoint=endpoint, params=params)
    response = await client.get(endpoint, params=params)
    _log("GRAPH_RESPONSE", endpoint=endpoint, count=1)
    return response


async def collect_guest_invite_settings(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "guest_invite_settings"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    policy = await _authorization_policy(tenant)
    allow_invites_from = policy.get("allowInvitesFrom")
    status = "pass" if allow_invites_from in {"none", "adminsAndGuestInviters"} else "fail"
    evidence = {"tenant_id": tenant.tenant_id, "authorization_policy": policy}
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="medium",
        actual_value=allow_invites_from,
        expected_value="none or adminsAndGuestInviters",
        finding=f"Guest invite setting is {allow_invites_from}",
        graph_endpoint="/policies/authorizationPolicy?$select=allowInvitesFrom",
        evidence=evidence,
        raw_response={"authorizationPolicy": policy},
        graph_calls=1,
        scoring_weight=3.0,
    )


async def collect_entra_tenant_creation_by_non_admin(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "entra_tenant_creation_by_non_admin"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    policy = await _authorization_policy(tenant)
    permissions = policy.get("defaultUserRolePermissions") or {}
    allowed = permissions.get("allowedToCreateTenants")
    status = "pass" if allowed is False else "fail"
    evidence = {"tenant_id": tenant.tenant_id, "authorization_policy": policy}
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value=allowed,
        expected_value="allowedToCreateTenants=false",
        finding=f"Non-admin tenant creation allowed: {allowed}",
        graph_endpoint="/policies/authorizationPolicy?$select=defaultUserRolePermissions",
        evidence=evidence,
        raw_response={"authorizationPolicy": policy},
        graph_calls=1,
        scoring_weight=5.0,
    )


async def collect_entra_third_party_app_integrations(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "entra_third_party_app_integrations"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    endpoint = "/policies/authorizationPolicy?$select=defaultUserRolePermissions"
    try:
        policy = await _authorization_policy(tenant)
    except Exception as exc:
        reasoning = "Unable to validate the tenant configuration for third-party app integrations."
        error_detail = f"{type(exc).__name__}: {exc}"
        evidence = _evaluation_evidence(
            pass_criteria="A ManagePermissionGrantsForSelf user consent policy is assigned",
            fail_criteria="No ManagePermissionGrantsForSelf policy is assigned, or the tenant configuration cannot be validated",
            reasoning=reasoning,
            extra={"tenant_id": tenant.tenant_id, "configuration_validated": False, "error": error_detail},
        )
        return _collector_result(
            parameter_key=parameter_key,
            status="fail",
            severity="high",
            actual_value={"user_consent_enabled": None, "configuration_validated": False},
            expected_value="User consent for third-party applications is enabled",
            finding=reasoning,
            graph_endpoint=endpoint,
            evidence=evidence,
            raw_response={"error": error_detail},
            graph_calls=1,
            scoring_weight=4.0,
        )

    permissions = policy.get("defaultUserRolePermissions")
    if not isinstance(permissions, dict) or "permissionGrantPoliciesAssigned" not in permissions:
        reasoning = "Unable to validate the tenant configuration for third-party app integrations."
        evidence = _evaluation_evidence(
            pass_criteria="A ManagePermissionGrantsForSelf user consent policy is assigned",
            fail_criteria="No ManagePermissionGrantsForSelf policy is assigned, or the tenant configuration cannot be validated",
            reasoning=reasoning,
            extra={
                "tenant_id": tenant.tenant_id,
                "configuration_validated": False,
                "error": "permissionGrantPoliciesAssigned was absent from the authorization policy response",
                "authorization_policy": policy,
            },
        )
        return _collector_result(
            parameter_key=parameter_key,
            status="fail",
            severity="high",
            actual_value={"user_consent_enabled": None, "configuration_validated": False},
            expected_value="User consent for third-party applications is enabled",
            finding=reasoning,
            graph_endpoint=endpoint,
            evidence=evidence,
            raw_response={"authorizationPolicy": policy},
            graph_calls=1,
            scoring_weight=4.0,
        )

    assigned = [str(item) for item in (permissions.get("permissionGrantPoliciesAssigned") or [])]
    user_consent_assignments = [
        item
        for item in assigned
        if item.lower().startswith("managepermissiongrantsforself.")
    ]
    policy_ids = [item.split(".", 1)[1] for item in user_consent_assignments]
    normalized_policy_ids = {item.lower() for item in policy_ids}
    user_consent_enabled = bool(user_consent_assignments)
    supported_enabled_option_selected = bool(
        normalized_policy_ids
        & {"microsoft-user-default-low", "microsoft-user-default-recommended"}
    )
    # Business rule: any enabled built-in or custom ManagePermissionGrantsForSelf
    # user consent policy passes; disabled or unvalidated user consent fails.
    status = "pass" if user_consent_enabled else "fail"

    if not user_consent_enabled:
        portal_configuration = "Do not allow user consent"
        reasoning = "Third-party app integrations are disabled for users."
    elif "microsoft-user-default-recommended" in normalized_policy_ids:
        portal_configuration = "Let Microsoft manage your consent settings"
        reasoning = "Third-party app integrations are enabled through Microsoft-managed user consent settings."
    elif "microsoft-user-default-low" in normalized_policy_ids:
        portal_configuration = "Allow user consent for apps from verified publishers, for selected permissions"
        reasoning = "Third-party app integrations are enabled for verified publishers and selected permissions."
    else:
        portal_configuration = "No supported built-in portal option selected (custom user consent policy)"
        reasoning = f"Third-party app integrations are enabled through custom user consent policy: {', '.join(policy_ids)}."

    evidence = _evaluation_evidence(
        pass_criteria="Third-party app integrations are enabled for users through a built-in or custom user consent policy",
        fail_criteria="Third-party app integrations are disabled for users or the tenant configuration cannot be validated",
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "configuration_validated": True,
            "supported_enabled_option_selected": supported_enabled_option_selected,
            "portal_configuration": portal_configuration,
            "permissionGrantPoliciesAssigned": assigned,
            "user_consent_policy_assignments": user_consent_assignments,
            "user_consent_policy_ids": policy_ids,
            "authorization_policy": policy,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={
            "user_consent_enabled": user_consent_enabled,
            "configuration_validated": True,
            "supported_enabled_option_selected": supported_enabled_option_selected,
            "portal_configuration": portal_configuration,
            "user_consent_policy_ids": policy_ids,
        },
        expected_value="User consent for third-party applications is enabled",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"authorizationPolicy": policy},
        graph_calls=1,
        scoring_weight=4.0,
    )


async def collect_tenant_collaboration_invitations(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "tenant_collaboration_invitations"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    RESTRICTIVE_VALUES = {"none", "adminsAndGuestInviters", "adminsGuestInvitersAndMemberUsers"}
    client = await _graph_client(tenant)
    policy_endpoint = "/policies/crossTenantAccessPolicy"
    partners_endpoint = "/policies/crossTenantAccessPolicy/partners"
    policy = await client.get(policy_endpoint)
    partners = await _get_all(client, partners_endpoint)
    partner_values = partners.get("value") or []
    # Primary pass/fail gate: allowInvitesFrom from the authorization policy.
    authorization_policy = await _authorization_policy(tenant)
    allow_invites_from = authorization_policy.get("allowInvitesFrom")
    if allow_invites_from in RESTRICTIVE_VALUES:
        status = "pass"
        reasoning = f"Guest invitations restricted to: {allow_invites_from}"
    else:
        status = "fail"
        reasoning = f"Guest invitations allowed for: {allow_invites_from} (most permissive setting)"
    evidence = _evaluation_evidence(
        pass_criteria="allowInvitesFrom is none, adminsAndGuestInviters, or adminsGuestInvitersAndMemberUsers",
        fail_criteria="allowInvitesFrom is everyone or any non-restrictive value",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "allowInvitesFrom": allow_invites_from, "crossTenantAccessPolicy": policy, "partners": partner_values},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"allowInvitesFrom": allow_invites_from, "partner_count": len(partner_values)},
        expected_value="allowInvitesFrom restricted (not 'everyone')",
        finding=reasoning,
        graph_endpoint="/policies/authorizationPolicy + /policies/crossTenantAccessPolicy + /policies/crossTenantAccessPolicy/partners",
        evidence=evidence,
        raw_response={"authorizationPolicy": authorization_policy, "crossTenantAccessPolicy": policy, "partners": partners},
        graph_calls=3,
        scoring_weight=4.0,
    )


async def collect_authentication_methods_enabled(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "authentication_methods_enabled"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    policy = await _authentication_methods_policy(tenant)
    raw_response = {"authenticationMethodsPolicy": policy}
    methods = policy.get("authenticationMethodConfigurations") or []
    migration_state = str(policy.get("policyMigrationState") or "")
    method_labels = {
        "MicrosoftAuthenticator": "Microsoft Authenticator",
        "TemporaryAccessPass": "Temporary Access Pass",
        "Email": "Email OTP",
    }
    enabled = [
        {"method": method_labels.get(_auth_method_name(item), _auth_method_name(item)), "state": item.get("state")}
        for item in methods
        if str(item.get("state") or "").lower() == "enabled"
    ]
    all_states = [
        {"method": method_labels.get(_auth_method_name(item), _auth_method_name(item)), "state": item.get("state")}
        for item in methods
    ]
    disabled = [item for item in all_states if str(item.get("state") or "").lower() != "enabled"]
    enabled_names = ", ".join(item["method"] for item in enabled) or "none"
    status = "pass" if len(enabled) > 2 else "fail"
    reasoning = f"{len(enabled)} authentication method(s) enabled: {enabled_names}"
    evidence = _evaluation_evidence(
        pass_criteria="When authentication method has more than 2 authentication methods",
        fail_criteria="When authentication method has less than 2 authentication methods",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "policy_migration_state": migration_state, "methods": all_states},
    )
    result = _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value={
            "enabled_methods": len(enabled),
            "disabled_methods": len(disabled),
            "methods": all_states,
            "policy_migration_state": migration_state,
        },
        expected_value="More than 2 authentication methods enabled",
        finding=reasoning,
        graph_endpoint="https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy",
        evidence=evidence,
        raw_response=raw_response,
        graph_calls=1,
        scoring_weight=5.0,
    )
    # This control is classified as Critical / Security even when it passes.
    result["severity"] = "critical"
    return result


async def collect_admin_consent_workflow(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "admin_consent_workflow"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    client = await _graph_client(tenant)
    endpoint = "/policies/adminConsentRequestPolicy"
    policy = await client.get(endpoint)
    is_enabled = policy.get("isEnabled") is True
    status = "pass" if is_enabled else "fail"
    reasoning = "Admin consent workflow is configured" if is_enabled else "Admin consent workflow is not configured"
    evidence = _evaluation_evidence(
        pass_criteria="Admin Consent Workflow is configured",
        fail_criteria="Admin Consent Workflow is not configured",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "policy": policy},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"isEnabled": is_enabled, "status_text": reasoning},
        expected_value="Admin consent request workflow configured",
        finding=reasoning,
        graph_endpoint="/policies/adminConsentRequestPolicy",
        evidence=evidence,
        raw_response={"adminConsentRequestPolicy": policy},
        graph_calls=1,
        scoring_weight=4.0,
    )


async def collect_cap_policies_for_risky_sign_ins(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "cap_policies_for_risky_sign_ins"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    raw_response = {"conditionalAccessPolicies": await _conditional_access_policies(tenant)}
    policies = raw_response["conditionalAccessPolicies"].get("value") or []
    risky = []
    for policy in policies:
        conditions = policy.get("conditions") or {}
        sign_in_risk = conditions.get("signInRiskLevels") or []
        user_risk = conditions.get("userRiskLevels") or []
        if sign_in_risk or user_risk:
            risky.append({
                "id": policy.get("id"),
                "name": policy.get("displayName"),
                "state": policy.get("state"),
                "signInRiskLevels": sign_in_risk,
                "userRiskLevels": user_risk,
                "grantControls": policy.get("grantControls"),
            })
    configured = [item for item in risky if str(item.get("state") or "").lower() == "enabled"]
    status = "pass" if configured else "fail"
    reasoning = f"{len(configured)} enabled Conditional Access policy/policies target risky sign-ins"
    evidence = _evaluation_evidence(
        pass_criteria="CAP policy for risky sign-ins are configured",
        fail_criteria="CAP policy for risky sign-ins are not configured",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "policies": risky},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"risky_policy_count": len(configured), "policies": risky},
        expected_value="At least one enabled Conditional Access policy targets sign-in or user risk",
        finding=reasoning,
        graph_endpoint="/identity/conditionalAccess/policies?$select=id,displayName,state,conditions,grantControls",
        evidence=evidence,
        raw_response=raw_response,
        graph_calls=1,
        scoring_weight=4.0,
    )


async def collect_users_without_mfa(tenant: ConnectedTenant) -> dict[str, Any]:
    """Replicate the manual portal check using the Microsoft Entra User Registration Details report.

    Manual process this mirrors:
      Entra admin center > Identity > Authentication methods > User registration details >
      Download export. The export has a "Multifactor authentication capable" column
      (isMfaCapable) and a "Multifactor authentication registered" column (isMfaRegistered).
      A user "has MFA" when they are MFA-capable — i.e., they have registered a strong MFA
      method that the authentication methods policy allows. The tenant PASSES only when every
      in-scope user is MFA-capable; any user that is not MFA-capable is a "user without MFA".

    One supported, GA call replaces the previous per-user (N+1) approach:
      GET /reports/authenticationMethods/userRegistrationDetails   (Microsoft Graph v1.0)
      Permission: AuditLog.Read.All  ·  Requires Microsoft Entra ID P1/P2 (activity report).
      https://learn.microsoft.com/graph/api/authenticationmethodsroot-list-userregistrationdetails

    Scope: guest accounts are excluded (their MFA is governed by the resource tenant); disabled
    accounts are already excluded by the report API. Members are the "capable users" population.
    """
    parameter_key = "users_without_mfa"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    endpoint = "/reports/authenticationMethods/userRegistrationDetails"
    _PASS = "Every in-scope member user is MFA-capable (MFA registered for all capable users)"
    _FAIL = "One or more in-scope member users are not MFA-capable (no policy-allowed strong MFA method)"

    client = await _graph_client(tenant)
    try:
        response = await _get_all(client, endpoint, params={"$top": "999"})
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        error = payload.get("error") or payload
        status_code = exc.response.status_code
        graph_response = {"ok": False, "status_code": status_code, "error": error}

        # The registration report needs BOTH Entra ID P1/P2 AND the AuditLog.Read.All app
        # permission. A blanket "requires a license" message is misleading when the real cause
        # is a missing permission/consent, so classify the Graph error and report accordingly.
        if isinstance(error, dict):
            err_text = f"{error.get('code', '')} {error.get('message', '')}".lower()
        else:
            err_text = str(error).lower()
        license_signal = any(
            token in err_text
            for token in ["license", "licence", "premium", "not licensed", "p1", "p2", "aad premium", "entra id p"]
        )
        permission_signal = any(
            token in err_text
            for token in [
                "authorization_requestdenied",
                "insufficient privileges",
                "access denied",
                "accessdenied",
                "does not have permission",
                "forbidden",
            ]
        )

        # Genuine licensing gap: HTTP 402, or a 403 that explicitly cites licensing (and does
        # not look like a permission denial).
        if status_code == 402 or (status_code == 403 and license_signal and not permission_signal):
            return _licensing_required_result(
                tenant,
                parameter_key=parameter_key,
                endpoint=endpoint,
                required_sku="Microsoft Entra ID P1 or P2",
                required_service="Microsoft Entra authentication methods registration report",
                required_role="Reports Reader, Security Reader, or Global Reader",
                required_permissions=["AuditLog.Read.All"],
                expected_value="All capable users registered for MFA",
                pass_criteria=_PASS,
                fail_criteria=_FAIL,
                severity="high",
                scoring_weight=4.0,
                graph_response=graph_response,
            )

        # Permission / consent gap (the usual cause of a 401 or a bare 403): the app is missing
        # AuditLog.Read.All or admin consent — report that precisely, not as a licensing problem.
        if status_code in (401, 403):
            return _collection_error_result(
                tenant,
                parameter_key=parameter_key,
                endpoint=endpoint,
                required_api="Microsoft Graph /reports/authenticationMethods/userRegistrationDetails",
                required_permissions=["AuditLog.Read.All"],
                expected_value="All capable users registered for MFA",
                pass_criteria=_PASS,
                fail_criteria=_FAIL,
                severity="high",
                scoring_weight=4.0,
                response=graph_response,
                reason=(
                    "The Microsoft Entra 'User registration details' report could not be read: the CRA application "
                    "is missing the AuditLog.Read.All Microsoft Graph application permission, or admin consent has "
                    "not been granted. Grant AuditLog.Read.All (Application) and re-run. Note this report also "
                    "requires Microsoft Entra ID P1 or P2."
                ),
            )

        # Any other Graph error (5xx / 404 / 429) — transient or service failure.
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_api="Microsoft Graph /reports/authenticationMethods/userRegistrationDetails",
            required_permissions=["AuditLog.Read.All"],
            expected_value="All capable users registered for MFA",
            pass_criteria=_PASS,
            fail_criteria=_FAIL,
            severity="high",
            scoring_weight=4.0,
            response=graph_response,
        )

    rows = response.get("value") or []
    # "Capable users" population = member accounts. Guests are out of scope.
    members = [r for r in rows if str(r.get("userType") or "").lower() != "guest"]
    guests_excluded = len(rows) - len(members)

    def _is_capable(row: dict[str, Any]) -> bool:
        return row.get("isMfaCapable") is True

    without_mfa = [
        {
            "id": r.get("id"),
            "userPrincipalName": r.get("userPrincipalName"),
            "isMfaCapable": bool(r.get("isMfaCapable")),
            "isMfaRegistered": bool(r.get("isMfaRegistered")),
            "methodsRegistered": r.get("methodsRegistered") or [],
        }
        for r in members
        if not _is_capable(r)
    ]
    member_count = len(members)
    mfa_capable_count = sum(1 for r in members if _is_capable(r))
    mfa_registered_count = sum(1 for r in members if r.get("isMfaRegistered") is True)

    if member_count == 0:
        status = "fail"
        reasoning = "The authentication methods registration report returned no member users to evaluate."
    elif not without_mfa:
        status = "pass"
        reasoning = f"All {member_count} member user(s) are MFA-capable — every capable user is registered for MFA."
    else:
        status = "fail"
        upns = ", ".join((u["userPrincipalName"] or u["id"]) for u in without_mfa[:20])
        more = "" if len(without_mfa) <= 20 else f" (+{len(without_mfa) - 20} more)"
        reasoning = (
            f"{len(without_mfa)} of {member_count} member user(s) are not MFA-capable (no policy-allowed "
            f"strong MFA method registered): {upns}{more}"
        )

    remediation = (
        "Drive MFA registration for the users listed as not MFA-capable — start an authentication methods "
        "registration campaign (Entra admin center > Identity > Authentication methods > Registration campaign) "
        "and/or require MFA via Conditional Access. Review the same data at Authentication methods > User "
        "registration details."
    )
    evidence = _evaluation_evidence(
        pass_criteria=_PASS,
        fail_criteria=_FAIL,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "member_user_count": member_count,
            "mfa_capable_users": mfa_capable_count,
            "mfa_registered_users": mfa_registered_count,
            "users_without_mfa": without_mfa[:200],
            "guests_excluded": guests_excluded,
            "data_source": "Microsoft Graph /reports/authenticationMethods/userRegistrationDetails (User registration details export)",
            "definition": "A user 'has MFA' when isMfaCapable = true (registered a strong MFA method allowed by the authentication methods policy).",
            "remediation": remediation,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={
            "users_without_mfa": len(without_mfa),
            "member_users": member_count,
            "mfa_capable_users": mfa_capable_count,
            "mfa_registered_users": mfa_registered_count,
        },
        expected_value="All capable (member) users are MFA-capable / registered for MFA",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"userRegistrationDetails": response},
        graph_calls=1,
        scoring_weight=4.0,
    )


async def collect_user_consent_for_applications(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "user_consent_for_applications"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    policy = await _authorization_policy(tenant)
    permissions = policy.get("defaultUserRolePermissions") or {}
    assigned = permissions.get("permissionGrantPoliciesAssigned") or []
    if not assigned:
        # An empty permissionGrantPoliciesAssigned means user consent is DISABLED — users
        # cannot consent to any app (the most restrictive, secure state).
        status = "pass"
        reasoning = "No user consent policy assigned — users cannot consent to applications"
    elif any("microsoft-user-default" in str(item).lower() for item in assigned):
        # Substring match: any Microsoft-managed default consent policy (recommended /
        # low-risk / etc.) present, regardless of prefix or hyphenation variations.
        status = "pass"
        reasoning = "User consent managed by Microsoft policy: " + ", ".join(str(item) for item in assigned)
    else:
        status = "fail"
        reasoning = (
            "Custom permission grant policy assigned — verify users cannot consent freely: "
            + ", ".join(str(item) for item in assigned)
        )
    evidence = _evaluation_evidence(
        pass_criteria="User consent is not set to Users can consent",
        fail_criteria="User consent is set to Users can consent",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "permissionGrantPoliciesAssigned": assigned, "authorization_policy": policy},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"permissionGrantPoliciesAssigned": assigned},
        expected_value="Users cannot consent for applications",
        finding=reasoning,
        graph_endpoint="/policies/authorizationPolicy?$select=defaultUserRolePermissions",
        evidence=evidence,
        raw_response={"authorizationPolicy": policy},
        graph_calls=1,
        scoring_weight=4.0,
    )


async def collect_non_admin_users_can_register_applications(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "non_admin_users_can_register_applications"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    policy = await _authorization_policy(tenant)
    permissions = policy.get("defaultUserRolePermissions") or {}
    allowed = permissions.get("allowedToCreateApps")
    status = "pass" if allowed is False else "fail"
    reasoning = f"Non-admin application registration allowed: {allowed}"
    evidence = _evaluation_evidence(
        pass_criteria="Non-Admin Users cannot register Applications",
        fail_criteria="Non-Admin Users can register Applications",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "authorization_policy": policy},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="info",
        actual_value=allowed,
        expected_value="allowedToCreateApps=false",
        finding=reasoning,
        graph_endpoint="/policies/authorizationPolicy?$select=defaultUserRolePermissions",
        evidence=evidence,
        raw_response={"authorizationPolicy": policy},
        graph_calls=1,
        scoring_weight=1.0,
    )


async def collect_restricted_access_to_microsoft_entra_admin_centre(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "restricted_access_to_microsoft_entra_admin_centre"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    policy = await _authorization_policy(tenant)
    permissions = policy.get("defaultUserRolePermissions") or {}
    allowed = permissions.get("allowedToReadOtherUsers")
    status = "pass" if allowed is False else "fail"
    reasoning = (
        "Access to Microsoft Entra Admin Center is restricted."
        if status == "pass"
        else "Access to Microsoft Entra Admin Center is not restricted."
    )
    evidence = _evaluation_evidence(
        pass_criteria="Non-Admin Users should not have access to Microsoft Entra Admin Centre",
        fail_criteria="Non-Admin Users have access to Microsoft Entra Admin Centre",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "authorization_policy": policy},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value=allowed,
        expected_value="allowedToReadOtherUsers=false",
        finding=reasoning,
        graph_endpoint="/policies/authorizationPolicy?$select=defaultUserRolePermissions",
        evidence=evidence,
        raw_response={"authorizationPolicy": policy},
        graph_calls=1,
        scoring_weight=1.0,
    )


async def collect_self_service_password_reset_authentication_method(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "self_service_password_reset_authentication_method"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    methods_response = await _authentication_methods_policy(tenant)
    registration_response = await _user_registration_details(tenant)
    methods = methods_response.get("authenticationMethodConfigurations") or []
    enabled = [
        {"method": _auth_method_name(item), "state": item.get("state")}
        for item in methods
        if str(item.get("state") or "").lower() == "enabled"
    ]

    # Determine actual SSPR scope. NOTE: beta/policies/selfServicePasswordResetPolicy
    # is not a valid Graph segment (returns 400 BadRequest), so this call is expected
    # to fail and the registration-details fallback below is the effective source of
    # truth (counts users with isSsprRegistered AND isSsprEnabled).
    sspr_policy = await _graph_get_json_or_error(
        tenant, "https://graph.microsoft.com/beta/policies/selfServicePasswordResetPolicy"
    )
    registration_rows = registration_response.get("value") or []
    sspr_enabled_users = [
        row for row in registration_rows
        if row.get("isSsprRegistered") is True and row.get("isSsprEnabled") is True
    ]
    sspr_scope = None
    if sspr_policy.get("ok"):
        sspr_scope = str((sspr_policy.get("response") or {}).get("policyMode") or "").lower()

    if sspr_scope == "disabled" or (sspr_scope is None and len(sspr_enabled_users) == 0):
        status = "fail"
        reasoning = "SSPR is not enabled for any users in this tenant"
    elif (sspr_scope in {"selected", "all"}) or len(sspr_enabled_users) >= 1:
        status = "pass"
        reasoning = f"{len(sspr_enabled_users)} user(s) have SSPR enabled and registered"
    else:
        status = "fail"
        reasoning = "SSPR is not enabled for any users in this tenant"
    evidence = _evaluation_evidence(
        pass_criteria="SSPR scope is selected/all and at least one user is SSPR-registered",
        fail_criteria="SSPR scope is disabled or no users have SSPR enabled",
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "enabled_methods": enabled,
            "sspr_scope": sspr_scope,
            "sspr_enabled_user_count": len(sspr_enabled_users),
            "user_registration_details": registration_rows,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value={"sspr_scope": sspr_scope, "sspr_enabled_users": len(sspr_enabled_users), "enabled_methods": len(enabled)},
        expected_value="SSPR enabled (scope selected/all) with registered users",
        finding=reasoning,
        graph_endpoint="https://graph.microsoft.com/beta/policies/selfServicePasswordResetPolicy + /reports/authenticationMethods/userRegistrationDetails",
        evidence=evidence,
        raw_response={"authenticationMethodsPolicy": methods_response, "selfServicePasswordResetPolicy": sspr_policy, "userRegistrationDetails": registration_response},
        graph_calls=3,
        scoring_weight=5.0,
    )


async def collect_assigned_license(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "assigned_license"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    users_response = await _collect_users(tenant)
    sku_response = await _subscribed_skus(tenant)
    users = users_response.get("value") or []
    skus = sku_response.get("value") or []
    prerequisite_sku_ids = {
        str(sku.get("skuId"))
        for sku in skus
        if str(sku.get("skuPartNumber") or "").upper() in COPILOT_PREREQUISITE_SKU_PARTS
    }
    licensed_users = []
    missing_users = []
    for user in users:
        assigned = {str(item.get("skuId")) for item in user.get("assignedLicenses") or []}
        row = {
            "id": user.get("id"),
            "displayName": user.get("displayName"),
            "userPrincipalName": user.get("userPrincipalName"),
            "assignedLicenses": list(assigned),
        }
        if assigned & prerequisite_sku_ids:
            licensed_users.append(row)
        else:
            missing_users.append(row)
    ratio = _percent(len(licensed_users), len(users))
    status = "pass" if ratio > 85 else "fail"
    reasoning = f"{ratio}% of users have a recognized Copilot prerequisite license"
    evidence = _evaluation_evidence(
        pass_criteria="Number of eligible users with pre-req license is more than 85%",
        fail_criteria="Number of eligible users with pre-req license is less than 85%",
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "recognized_prerequisite_skus": sorted(prerequisite_sku_ids),
            "missing_users": missing_users,
            "eligible_users": len(licensed_users),
            "total_users": len(users),
            "eligible_ratio_percent": ratio,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="info",
        actual_value={"eligible_users": len(licensed_users), "total_users": len(users), "eligible_ratio_percent": ratio},
        expected_value=">85% users have prerequisite license",
        finding=reasoning,
        graph_endpoint="/users?$select=id,displayName,userPrincipalName,assignedLicenses + /subscribedSkus",
        evidence=evidence,
        raw_response={"users": users_response, "subscribedSkus": sku_response},
        graph_calls=2,
        scoring_weight=1.0,
    )


async def collect_conditional_access_policies_exclusion(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "conditional_access_policies_exclusion"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    raw_response = {"conditionalAccessPolicies": await _conditional_access_policies(tenant)}
    policies = raw_response["conditionalAccessPolicies"].get("value") or []
    exclusions = []
    for policy in policies:
        users = (policy.get("conditions") or {}).get("users") or {}
        excluded = {
            "excludeUsers": users.get("excludeUsers") or [],
            "excludeGroups": users.get("excludeGroups") or [],
            "excludeRoles": users.get("excludeRoles") or [],
        }
        if any(excluded.values()):
            exclusions.append({
                "id": policy.get("id"),
                "name": policy.get("displayName"),
                "state": policy.get("state"),
                **excluded,
            })
    status = "pass" if not exclusions else "fail"
    reasoning = f"{len(exclusions)} Conditional Access policy/policies have user, group, or role exclusions"
    evidence = _evaluation_evidence(
        pass_criteria="No users are excluded from conditional access policies",
        fail_criteria="Users are excluded from conditional access policies",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "policies_with_exclusions": exclusions},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"policies_with_exclusions": len(exclusions), "exclusions": exclusions},
        expected_value="No Conditional Access user/group/role exclusions",
        finding=reasoning,
        graph_endpoint="/identity/conditionalAccess/policies?$select=id,displayName,state,conditions,grantControls",
        evidence=evidence,
        raw_response=raw_response,
        graph_calls=1,
        scoring_weight=4.0,
    )


async def collect_devices_without_compliance_policies(tenant: ConnectedTenant) -> dict[str, Any]:
    """Check whether the tenant has any Microsoft Intune device COMPLIANCE POLICY.

    Workload: Microsoft Intune (not Entra ID). The control is about whether
    compliance *policies* exist so enrolled devices are actually evaluated — the
    previous implementation read enrolled *devices* (/deviceManagement/managedDevices)
    and graded their complianceState, which answers a different question and fails a
    tenant that simply has no devices enrolled yet.

      GET /deviceManagement/deviceCompliancePolicies   (Microsoft Graph v1.0)
      Permission: DeviceManagementConfiguration.Read.All  ·  Requires a Microsoft Intune licence.
      https://learn.microsoft.com/graph/api/intune-deviceconfig-devicecompliancepolicy-list
    """
    parameter_key = "devices_without_compliance_policies"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    endpoint = "/deviceManagement/deviceCompliancePolicies"
    _SEVERITY = "medium"
    _WEIGHT = 3.0
    _PASS = "At least one Intune device compliance policy is configured"
    _FAIL = "No Intune device compliance policy is configured"

    client = await _graph_client(tenant)
    try:
        response = await _get_all(client, endpoint)
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        error = payload.get("error") or payload
        status_code = exc.response.status_code
        graph_response = {"ok": False, "status_code": status_code, "error": error}
        if status_code in (401, 402, 403):
            # No Intune licence, or the app lacks DeviceManagementConfiguration.Read.All.
            return _licensing_required_result(
                tenant,
                parameter_key=parameter_key,
                endpoint=endpoint,
                required_sku="Microsoft Intune (Intune Plan 1 / Microsoft 365 E3 or E5)",
                required_service="Microsoft Intune device compliance management",
                required_role="Intune Administrator or Global Reader",
                required_permissions=["DeviceManagementConfiguration.Read.All"],
                expected_value="At least one Intune device compliance policy configured",
                pass_criteria=_PASS,
                fail_criteria=_FAIL,
                severity=_SEVERITY,
                scoring_weight=_WEIGHT,
                graph_response=graph_response,
            )
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_api="Microsoft Graph Intune /deviceManagement/deviceCompliancePolicies",
            required_permissions=["DeviceManagementConfiguration.Read.All"],
            expected_value="At least one Intune device compliance policy configured",
            pass_criteria=_PASS,
            fail_criteria=_FAIL,
            severity=_SEVERITY,
            scoring_weight=_WEIGHT,
            response=graph_response,
        )

    policies = response.get("value") or []
    policy_rows = [
        {
            "id": p.get("id"),
            "displayName": p.get("displayName"),
            "platform": str(p.get("@odata.type") or "").split(".")[-1] or None,
        }
        for p in policies
    ]
    status = "pass" if policies else "fail"
    if policies:
        reasoning = f"{len(policies)} Intune device compliance policy(ies) are configured."
    else:
        reasoning = (
            "No Intune device compliance policies are configured — enrolled devices are not evaluated for "
            "compliance, so device-based Conditional Access cannot gate access to Microsoft 365 Copilot data."
        )
    remediation = (
        "Create device compliance policies in the Microsoft Intune admin center > Devices > Compliance policies, "
        "then require compliant devices through a Conditional Access grant control."
    )
    evidence = _evaluation_evidence(
        pass_criteria=_PASS,
        fail_criteria=_FAIL,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "compliance_policy_count": len(policies),
            "compliance_policies": policy_rows[:50],
            "data_source": "Microsoft Graph /deviceManagement/deviceCompliancePolicies (Microsoft Intune)",
            "workload": "Microsoft Intune",
            "remediation": remediation,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity=_SEVERITY,
        actual_value={"compliance_policy_count": len(policies)},
        expected_value="At least one Intune device compliance policy configured",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"deviceCompliancePolicies": response},
        graph_calls=1,
        scoring_weight=_WEIGHT,
    )


async def _m365_report_rows(tenant: ConnectedTenant, endpoint: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    report = await _graph_get_text(tenant, endpoint)
    if not report.get("ok"):
        return [], report
    rows = _csv_rows(report)
    _log("GRAPH_RESPONSE", endpoint=endpoint, count=len(rows))
    return rows, report


def _report_error_result(
    *,
    tenant: ConnectedTenant,
    parameter_key: str,
    report: dict[str, Any],
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    graph_endpoint: str,
    severity: str,
    scoring_weight: float,
) -> dict[str, Any]:
    error = report.get("error") or {}
    reasoning = error.get("message") or "Microsoft Graph report data could not be collected"
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "graph_error": error, "status_code": report.get("status_code")},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="fail",
        severity=severity,
        actual_value={"report_available": False, "error": error},
        expected_value=expected_value,
        finding=reasoning,
        graph_endpoint=graph_endpoint,
        evidence=evidence,
        raw_response={"report": report},
        graph_calls=1,
        scoring_weight=scoring_weight,
    )


async def collect_mailboxes_status_active_inactive(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "mailboxes_status_active_inactive"
    endpoint = "/reports/getEmailActivityUserDetail(period='D90')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value=">85% active mailboxes",
            pass_criteria="When more than 85% of non-deleted mailboxes have Last Activity Date within the last 60 days in the D90 email activity report",
            fail_criteria="When less than 85% of non-deleted mailboxes have Last Activity Date within the last 60 days in the D90 email activity report",
            graph_endpoint=endpoint,
            severity="critical",
            scoring_weight=5.0,
        )
    mailboxes = [row for row in rows if str(row.get("Is Deleted") or "").lower() != "true"]
    active = _active_email_activity_rows(rows, within_days=60)
    inactive = [row for row in mailboxes if row not in active]
    ratio = _percent(len(active), len(mailboxes))
    status = "pass" if ratio > 85 else "fail"
    reasoning = (
        f"{len(active)}/{len(mailboxes)} active mailbox(es) ({ratio}%) based on D90 email activity; "
        "active means Last Activity Date is within the last 60 days"
    )
    evidence = _evaluation_evidence(
        pass_criteria="When more than 85% of non-deleted mailboxes have Last Activity Date within the last 60 days in the D90 email activity report",
        fail_criteria="When less than 85% of non-deleted mailboxes have Last Activity Date within the last 60 days in the D90 email activity report",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "active_mailboxes": active, "inactive_mailboxes": inactive, "active_ratio": ratio},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value={"active_mailboxes": len(active), "inactive_mailboxes": len(inactive), "active_ratio": ratio},
        expected_value=">85% active mailboxes",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"csv_rows": rows},
        graph_calls=1,
        scoring_weight=5.0,
    )


async def collect_mailbox_storage_usage(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "mailbox_storage_usage"
    endpoint = "/reports/getMailboxUsageDetail(period='D30')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value="<75% mailbox storage usage",
            pass_criteria="When the active storage on mailbox is less than 75%",
            fail_criteria="When the active storage on mailbox is more than 75%",
            graph_endpoint=endpoint,
            severity="medium",
            scoring_weight=3.0,
        )
    # getMailboxUsageDetail does NOT expose a recipient/mailbox type column, so we
    # cannot exclude shared/room/equipment mailboxes from this report alone. Detect
    # whether any type column is present; if absent, report that no type filtering
    # was possible rather than silently pretending to exclude non-user mailboxes.
    type_column = next(
        (col for col in ("Recipient Type", "Mailbox Type", "Recipient Type Details")
         if rows and col in rows[0]),
        None,
    )
    mailboxes = []
    over_threshold = []
    excluded_non_user = 0
    for row in rows:
        if type_column:
            recipient_type = str(row.get(type_column) or "").lower()
            if recipient_type and recipient_type != "usermailbox":
                excluded_non_user += 1
                continue
        used = _float_value(row, "Storage Used (Byte)")
        quota = _float_value(row, "Prohibit Send/Receive Quota (Byte)") or _float_value(row, "Prohibit Send Quota (Byte)")
        ratio = round(used / quota * 100, 2) if quota else 0.0
        item = {
            "userPrincipalName": row.get("User Principal Name"),
            "displayName": row.get("Display Name"),
            "storageUsedBytes": used,
            "quotaBytes": quota,
            "storage_usage_ratio": ratio,
        }
        mailboxes.append(item)
        if ratio >= 75:
            over_threshold.append(item)
    max_ratio = max([item["storage_usage_ratio"] for item in mailboxes], default=0.0)
    status = "pass" if not over_threshold else "fail"
    if type_column:
        reasoning = f"{len(over_threshold)} user mailbox(es) are at or above 75% of their storage quota (highest {max_ratio}%); {excluded_non_user} non-user mailboxes were excluded from this result"
    else:
        reasoning = f"{len(over_threshold)} mailbox(es) are at or above 75% of their storage quota (highest {max_ratio}%)"
    if over_threshold:
        reasoning += ". Some of these may be shared, room, or resource mailboxes, which should be reviewed separately from standard user mailboxes."
    evidence = _evaluation_evidence(
        pass_criteria="When the active storage on mailbox is less than 75%",
        fail_criteria="When the active storage on mailbox is more than 75%",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "mailboxes": mailboxes, "over_threshold": over_threshold, "storage_usage_ratio": max_ratio},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="medium",
        actual_value={"mailbox_count": len(mailboxes), "over_threshold": len(over_threshold), "storage_usage_ratio": max_ratio},
        expected_value="<75% mailbox storage usage",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"csv_rows": rows},
        graph_calls=1,
        scoring_weight=3.0,
    )


async def collect_number_of_emails_read_received(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "number_of_emails_read_received"
    endpoint = "/reports/getEmailActivityUserDetail(period='D90')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value=">75% users read more than 70% of received email",
            pass_criteria="More than 75% of users active in the last 60 days have read more than 70% of received email in the D90 email activity report",
            fail_criteria="Less than 75% of users active in the last 60 days have read more than 70% of received email in the D90 email activity report",
            graph_endpoint=endpoint,
            severity="info",
            scoring_weight=1.0,
        )
    active_rows = _active_email_activity_rows(rows, within_days=60)
    metrics = []
    engaged = []
    for row in active_rows:
        received = _int_value(row, "Receive Count")
        read = _int_value(row, "Read Count")
        read_ratio = _percent(read, received)
        item = {"userPrincipalName": row.get("User Principal Name"), "received": received, "read": read, "read_ratio": read_ratio}
        metrics.append(item)
        if received > 0 and read_ratio > 70:
            engaged.append(item)
    engagement_ratio = _percent(len(engaged), len(metrics))
    status = "pass" if engagement_ratio > 75 else "fail"
    reasoning = f"{len(engaged)}/{len(metrics)} active user(s) ({engagement_ratio}%) read more than 70% of received emails"
    evidence = _evaluation_evidence(
        pass_criteria="More than 75% of users active in the last 60 days have read more than 70% of received email in the D90 email activity report",
        fail_criteria="Less than 75% of users active in the last 60 days have read more than 70% of received email in the D90 email activity report",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "read_ratio": engagement_ratio, "engagement_metrics": metrics},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="info",
        actual_value={"read_ratio": engagement_ratio, "engaged_users": len(engaged), "active_users": len(metrics)},
        expected_value=">75% users read more than 70% of received email",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"csv_rows": rows},
        graph_calls=1,
        scoring_weight=1.0,
    )


async def collect_number_of_emails_sent(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "number_of_emails_sent"
    endpoint = "/reports/getEmailActivityUserDetail(period='D90')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value=">75% active users sent 30 or more emails",
            pass_criteria="More than 75% of users active in the last 60 days sent 30 or more emails in the D90 email activity report",
            fail_criteria="Less than 75% of users active in the last 60 days sent 30 or more emails in the D90 email activity report",
            graph_endpoint=endpoint,
            severity="info",
            scoring_weight=1.0,
        )
    active_rows = _active_email_activity_rows(rows, within_days=60)
    sent_counts = [{"userPrincipalName": row.get("User Principal Name"), "send_count": _int_value(row, "Send Count")} for row in active_rows]
    users_over_threshold = [item for item in sent_counts if item["send_count"] >= 30]
    sent_ratio = _percent(len(users_over_threshold), len(sent_counts))
    status = "pass" if sent_ratio > 75 else "fail"
    reasoning = f"{len(users_over_threshold)}/{len(sent_counts)} active user(s) ({sent_ratio}%) sent 30 or more emails"
    evidence = _evaluation_evidence(
        pass_criteria="More than 75% of users active in the last 60 days sent 30 or more emails in the D90 email activity report",
        fail_criteria="Less than 75% of users active in the last 60 days sent 30 or more emails in the D90 email activity report",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "sent_ratio": sent_ratio, "users": sent_counts, "users_over_threshold": users_over_threshold},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="info",
        actual_value={"sent_ratio": sent_ratio, "users_sent_30_or_more": len(users_over_threshold), "active_users": len(sent_counts)},
        expected_value=">75% active users sent 30 or more emails",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"csv_rows": rows},
        graph_calls=1,
        scoring_weight=1.0,
    )


async def collect_active_inactive_teams(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "active_inactive_teams"
    endpoint = "/reports/getTeamsTeamActivityDetail(period='D30')"
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant,
            parameter_key=parameter_key,
            service_name="Microsoft Teams",
            graph_endpoint=endpoint,
            expected_value="No inactive teams",
            pass_criteria="When a tenant does not have inactive teams",
            fail_criteria="When a tenant has inactive teams or Microsoft Teams is unavailable",
            severity="high",
            scoring_weight=4.0,
        )
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value="No inactive teams",
            pass_criteria="When a tenant does not have inactive teams",
            fail_criteria="When a tenant has inactive teams",
            graph_endpoint=endpoint,
            severity="high",
            scoring_weight=4.0,
        )
    teams = [row for row in rows if str(row.get("Is Deleted") or "").lower() != "true"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    active = []
    inactive = []
    for row in teams:
        last_activity_raw = row.get("Last Activity Date", "") or ""
        if not last_activity_raw.strip():
            inactive.append(row)
            continue
        try:
            last_activity = datetime.strptime(last_activity_raw.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if last_activity < cutoff:
                inactive.append(row)
            else:
                active.append(row)
        except Exception:
            inactive.append(row)
    total = len(teams)
    inactive_pct = _percent(len(inactive), total)
    status = "pass" if not inactive else "fail"
    if inactive:
        reasoning = f"{len(inactive)} out of {total} ({inactive_pct}%) teams are inactive"
    else:
        reasoning = f"All {total} team(s) were active within the last 60 days"
    evidence = _evaluation_evidence(
        pass_criteria="When a tenant does not have inactive teams",
        fail_criteria="When a tenant has inactive teams",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "active_teams": active, "inactive_teams": inactive},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"active_team_count": len(active), "inactive_team_count": len(inactive)},
        expected_value="No inactive teams",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"csv_rows": rows},
        graph_calls=1,
        scoring_weight=4.0,
    )


async def collect_activer_inactive_teams_users(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "activer_inactive_teams_users"
    endpoint = "/reports/getTeamsUserActivityUserDetail(period='D30')"
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant,
            parameter_key=parameter_key,
            service_name="Microsoft Teams",
            graph_endpoint=endpoint,
            expected_value="<15% inactive Teams users",
            pass_criteria="When the number of inactive Teams users are less than 15% for the tenant",
            fail_criteria="When the number of inactive Teams users are 15% or more, or Microsoft Teams is unavailable",
            severity="medium",
            scoring_weight=3.0,
        )
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value="<15% inactive Teams users",
            pass_criteria="When the number of inactive Teams users are less than 15% for the tenant",
            fail_criteria="When the number of active Teams users are more than 15% for the tenant",
            graph_endpoint=endpoint,
            severity="medium",
            scoring_weight=3.0,
        )
    users = [row for row in rows if str(row.get("Is Deleted") or "").lower() != "true"]
    active = [row for row in users if _has_recent_activity(row, within_days=60)]
    inactive = [row for row in users if row not in active]
    inactive_ratio = _percent(len(inactive), len(users))
    active_pct = _percent(len(active), len(users))
    status = "pass" if inactive_ratio < 15 else "fail"
    reasoning = f"{len(active)} out of {len(users)} Teams users are active ({active_pct}%)"
    evidence = _evaluation_evidence(
        pass_criteria="When the number of inactive Teams users are less than 15% for the tenant",
        fail_criteria="When the number of active Teams users are more than 15% for the tenant",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "active_users": active, "inactive_users": inactive, "inactive_ratio": inactive_ratio},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="medium",
        actual_value={"active_users": len(active), "inactive_users": len(inactive), "inactive_ratio": inactive_ratio},
        expected_value="<15% inactive Teams users",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"csv_rows": rows},
        graph_calls=1,
        scoring_weight=3.0,
    )


async def collect_active_sites_count(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "active_sites_count"
    endpoint = "/reports/getSharePointSiteUsageDetail(period='D180')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value=">85% active SharePoint sites",
            pass_criteria="When the number active sites on SharePoint are more than 85%",
            fail_criteria="When the number active sites on SharePoint are less than 85%",
            graph_endpoint=endpoint,
            severity="medium",
            scoring_weight=3.0,
        )
    sites = [row for row in rows if str(row.get("Is Deleted") or "").strip().lower() != "true"]
    active = [row for row in sites if _has_recent_activity(row, within_days=60)]
    ratio = _percent(len(active), len(sites))
    status = "pass" if ratio >= 85 else "fail"
    reasoning = f"{len(active)} sites are active out of {len(sites)} ({ratio}%)"
    evidence = _evaluation_evidence(
        pass_criteria="When the number active sites on SharePoint are more than 85%",
        fail_criteria="When the number active sites on SharePoint are less than 85%",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "active_sites": active, "all_sites": sites, "active_ratio": ratio},
    )
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"active_site_count": len(active), "total_sites": len(sites), "active_ratio": ratio}, expected_value=">85% active SharePoint sites", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"csv_rows": rows}, graph_calls=1, scoring_weight=3.0)


async def collect_active_users_on_sharepoint(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "active_users_on_sharepoint"
    endpoint = "/reports/getSharePointActivityUserDetail(period='D90')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(tenant=tenant, parameter_key=parameter_key, report=report, expected_value=">85% active SharePoint users", pass_criteria="When the number active users on SharePoint are more than 85%", fail_criteria="When the number active users on SharePoint are less than 85%", graph_endpoint=endpoint, severity="medium", scoring_weight=3.0)
    users = [row for row in rows if str(row.get("Is Deleted") or "").lower() != "true"]
    active = [row for row in users if _has_recent_activity(row, within_days=60)]
    ratio = _percent(len(active), len(users))
    status = "pass" if ratio >= 85 else "fail"
    reasoning = f"{len(active)} users are active out of {len(users)} ({ratio}%)"
    evidence = _evaluation_evidence(pass_criteria="When the number active users on SharePoint are more than or equal to 85%", fail_criteria="When the number active users on SharePoint are less than 85%", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "active_users": active, "all_users": users, "active_ratio": ratio})
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"active_users": len(active), "total_users": len(users), "active_ratio": ratio}, expected_value=">=85% active SharePoint users", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"csv_rows": rows}, graph_calls=1, scoring_weight=3.0)


async def collect_total_active_users_on_onedrive(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "total_active_users_on_onedrive"
    endpoint = "/reports/getOneDriveUsageAccountDetail(period='D180')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(tenant=tenant, parameter_key=parameter_key, report=report, expected_value=">=85% active OneDrive users", pass_criteria="When the total active user on OneDrive are more than or equal to 85%", fail_criteria="When the total active user on OneDrive are less than 85%", graph_endpoint=endpoint, severity="info", scoring_weight=1.0)
    users = [row for row in rows if str(row.get("Is Deleted") or "").strip().lower() != "true"]
    active = [row for row in users if _has_recent_activity(row, within_days=60)]
    ratio = _percent(len(active), len(users))
    status = "pass" if ratio > 80 else "fail"
    reasoning = f"{len(active)} out of {len(users)} users are active ({ratio}%) in last 2 months"
    if status == "fail":
        reasoning += " — below 80% threshold"
    evidence = _evaluation_evidence(pass_criteria="When the total active users on OneDrive are more than 80%", fail_criteria="When the total active users on OneDrive are 80% or less", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "active_users": active, "all_users": users, "active_ratio": ratio})
    return _collector_result(parameter_key=parameter_key, status=status, severity="info", actual_value={"active_users": len(active), "total_users": len(users), "active_ratio": ratio}, expected_value=">80% active OneDrive users", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"csv_rows": rows}, graph_calls=1, scoring_weight=1.0)


async def _teams_with_owners_and_members(tenant: ConnectedTenant) -> dict[str, Any]:
    client = await _graph_client(tenant)
    teams_endpoint = "/groups"
    params = {
        "$filter": "resourceProvisioningOptions/Any(x:x eq 'Team')",
        "$select": "id,displayName,resourceProvisioningOptions",
    }
    teams_response = await _get_all(client, teams_endpoint, params=params)
    teams = []
    raw: dict[str, Any] = {"teams": teams_response, "owners": {}, "members": {}}
    graph_calls = 1
    skipped_teams = 0
    for team in teams_response.get("value") or []:
        team_id = team.get("id")
        try:
            owners_response = await _get_all(client, f"/groups/{team_id}/owners", params={"$select": "id,displayName,userPrincipalName,mail,userType"})
            members_response = await _get_all(client, f"/groups/{team_id}/members", params={"$select": "id,displayName,userPrincipalName,userType"})
        except Exception as exc:  # noqa: BLE001 - one failing group must not blank the whole control
            skipped_teams += 1
            logger.warning("[GRAPH] Teams enumeration: skipped group %s after retries (%s)", team_id, exc)
            continue
        graph_calls += 2
        owners = owners_response.get("value") or []
        members = members_response.get("value") or []
        guests = [item for item in members if str(item.get("userType") or "").lower() == "guest"]
        raw["owners"][team_id] = owners_response
        raw["members"][team_id] = members_response
        teams.append({
            "id": team_id,
            "displayName": team.get("displayName"),
            "owner_count": len(owners),
            "owners": owners,
            "member_count": len(members),
            "guest_count": len(guests),
            "guest_members": guests,
        })
    return {"teams": teams, "raw_response": raw, "graph_calls": graph_calls, "skipped_teams": skipped_teams}


async def collect_minimum_number_of_owners(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "minimum_number_of_owners"
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant,
            parameter_key=parameter_key,
            service_name="Microsoft Teams",
            graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners",
            expected_value="All teams have at least 2 owners",
            pass_criteria="When all teams have more than 1 Owner",
            fail_criteria="When teams have less than 2 Owner or Microsoft Teams is unavailable",
            severity="high",
            scoring_weight=4.0,
        )
    data = await _teams_with_owners_and_members(tenant)
    teams = data["teams"]
    under_owned = [team for team in teams if team["owner_count"] < 2]
    status = "pass" if not under_owned else "fail"
    if under_owned:
        reasoning = f"There are {len(under_owned)} teams with less than 2 owners"
    else:
        reasoning = f"All {len(teams)} team(s) have at least 2 owners"
    evidence = _evaluation_evidence(pass_criteria="When all teams have more than 1 Owner", fail_criteria="When teams have less than 2 Owner", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "teams": teams, "under_owned_teams": under_owned})
    return _collector_result(parameter_key=parameter_key, status=status, severity="high", actual_value={"teams_with_less_than_2_owners": len(under_owned), "total_teams": len(teams)}, expected_value="All teams have at least 2 owners", finding=reasoning, graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners", evidence=evidence, raw_response=data["raw_response"], graph_calls=data["graph_calls"], scoring_weight=4.0)


async def collect_orphan_teams(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "orphan_teams"
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant,
            parameter_key=parameter_key,
            service_name="Microsoft Teams",
            graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners",
            expected_value="No orphan teams",
            pass_criteria="When there are no orphan teams",
            fail_criteria="When orphan teams are present or Microsoft Teams is unavailable",
            severity="high",
            scoring_weight=4.0,
        )
    data = await _teams_with_owners_and_members(tenant)
    teams = data["teams"]
    orphaned = [team for team in teams if team["owner_count"] == 0]
    status = "pass" if not orphaned else "fail"
    reasoning = "There are no orphan teams" if not orphaned else f"There are {len(orphaned)} orphan teams"
    evidence = _evaluation_evidence(pass_criteria="When there are no orphan teams", fail_criteria="When orphan teams are present", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "orphan_teams": orphaned, "teams": teams})
    return _collector_result(parameter_key=parameter_key, status=status, severity="high", actual_value={"orphan_team_count": len(orphaned), "total_teams": len(teams)}, expected_value="No orphan teams", finding=reasoning, graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners", evidence=evidence, raw_response=data["raw_response"], graph_calls=data["graph_calls"], scoring_weight=4.0)


async def collect_teams_with_external_users(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "teams_with_external_users"
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant,
            parameter_key=parameter_key,
            service_name="Microsoft Teams",
            graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/members",
            expected_value="<20% Teams with external users",
            pass_criteria="When it is less than 20%",
            fail_criteria="When it is more than to 20% or Microsoft Teams is unavailable",
            severity="high",
            scoring_weight=4.0,
        )
    data = await _teams_with_owners_and_members(tenant)
    teams = data["teams"]
    external = [team for team in teams if team["guest_count"] > 0]
    ratio = _percent(len(external), len(teams))
    status = "pass" if ratio < 20 else "fail"
    reasoning = f"Number of Teams with external users: {len(external)}"
    evidence = _evaluation_evidence(pass_criteria="When it is less than 20%", fail_criteria="When it is more than to 20%", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "teams_with_external_users": external, "all_teams": teams, "external_team_ratio": ratio})
    return _collector_result(parameter_key=parameter_key, status=status, severity="high", actual_value={"teams_with_external_users": len(external), "total_teams": len(teams), "external_team_ratio": ratio}, expected_value="<20% Teams with external users", finding=reasoning, graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/members", evidence=evidence, raw_response=data["raw_response"], graph_calls=data["graph_calls"], scoring_weight=4.0)


async def collect_teams_with_external_guest_as_owner(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "teams_with_external_guest_as_owner"
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant,
            parameter_key=parameter_key,
            service_name="Microsoft Teams",
            graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners",
            expected_value="No Teams have external guests as owners",
            pass_criteria="No Teams have external guests as owners",
            fail_criteria="One or more Teams have external guests as owners, or Microsoft Teams is unavailable",
            severity="high",
            scoring_weight=4.0,
        )
    try:
        data = await _teams_with_owners_and_members(tenant)
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners",
            required_api="Microsoft Graph Groups/Teams",
            required_permissions=["Group.Read.All", "Directory.Read.All", "Team.ReadBasic.All"],
            expected_value="No Teams have external guests as owners",
            pass_criteria="No Teams have external guests as owners",
            fail_criteria="One or more Teams have external guests as owners",
            severity="high",
            scoring_weight=4.0,
            response={"ok": False, "status_code": exc.response.status_code, "error": payload.get("error") or payload},
            command="Get-Team; Get-TeamUser -Role Owner plus Get-MgUser for userType",
        )
    teams = data["teams"]
    guest_owned = [
        team for team in teams
        if any(str(owner.get("userType") or "").lower() == "guest" for owner in team.get("owners") or [])
    ]
    status = "pass" if not guest_owned else "fail"
    reasoning = f"There are {len(guest_owned)} teams with external guests as owner"
    evidence = _evaluation_evidence(
        pass_criteria="No Teams have external guests as owners",
        fail_criteria="One or more Teams have external guests as owners",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "teams": teams, "teams_with_external_guest_owner": guest_owned},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"teams_with_external_guest_owner": len(guest_owned), "total_teams": len(teams)},
        expected_value="No Teams have external guests as owners",
        finding=reasoning,
        graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners",
        evidence=evidence,
        raw_response=data["raw_response"],
        graph_calls=data["graph_calls"],
        scoring_weight=4.0,
    )


async def _teams_policy_limitation_result(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
) -> dict[str, Any]:
    endpoint = "https://graph.microsoft.com/beta/teamwork/teamsAppSettings"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if response.get("ok"):
        settings = response.get("response") or {}
        reasoning = "Teams admin settings endpoint returned data, but this control requires Teams PowerShell-specific policy detail that is not exposed by this Graph endpoint."
        actual = {"teams_app_settings": settings, "teams_powershell_required": True}
    else:
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_api="Microsoft Teams admin policy Graph/PowerShell",
            required_permissions=["TeamSettings.Read.All", "Teams admin consent"],
            expected_value=expected_value,
            pass_criteria=pass_criteria,
            fail_criteria=fail_criteria,
            severity=severity,
            scoring_weight=scoring_weight,
            response=response,
            command="Teams PowerShell policy cmdlets for this control",
        )
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "teams_admin_endpoint_result": response},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="collection_error",
        severity=severity,
        actual_value=actual,
        expected_value=expected_value,
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"teamsAdminSettings": response},
        graph_calls=1,
        scoring_weight=scoring_weight,
    )


async def collect_guest_access_enabled_disabled(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="guest_access_enabled_disabled", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Guest access disabled",
            pass_criteria="When it is disabled", fail_criteria="When it is enabled",
            severity="medium", scoring_weight=3.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="guest_access_enabled_disabled", service_name="Microsoft Teams",
        portal_location="Teams Admin Center > Users > Guest access",
        graph_endpoint="beta/teamwork", expected_value="Guest access disabled",
        pass_criteria="When it is disabled", fail_criteria="When it is enabled",
        severity="medium", scoring_weight=3.0,
    )


async def collect_teams_anonymous_users(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="teams_anonymous_users", expected_value="Anonymous users disabled", pass_criteria="When it is disabled", fail_criteria="When it is enabled", severity="info", scoring_weight=1.0)


async def collect_teams_external_unmanaged_user_communication(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="teams_external_unmanaged_user_communication", expected_value="External unmanaged communication disabled", pass_criteria="When it is disabled", fail_criteria="When it is enabled", severity="info", scoring_weight=1.0)


async def collect_teams_file_storage_option(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="teams_file_storage_option", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Files stored within Microsoft suite",
            pass_criteria="When the files are stored within the Microsoft suite",
            fail_criteria="When the files are stored outside the Microsoft suite",
            severity="medium", scoring_weight=3.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="teams_file_storage_option", service_name="Microsoft Teams",
        portal_location="Teams Admin Center > Org-wide settings > Teams settings > Files",
        graph_endpoint="beta/teamwork", expected_value="Files stored within Microsoft suite",
        pass_criteria="When the files are stored within the Microsoft suite",
        fail_criteria="When the files are stored outside the Microsoft suite",
        severity="medium", scoring_weight=3.0,
    )


async def collect_copilot_integration_enabled(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="copilot_integration_enabled", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Copilot app integration enabled",
            pass_criteria="When it is enabled", fail_criteria="When it is disabled",
            severity="critical", scoring_weight=5.0,
        )
    result = _governance_unverifiable_fail(
        tenant, parameter_key="copilot_integration_enabled", service_name="Microsoft Teams",
        portal_location="Microsoft 365 Admin Center > Settings > Copilot",
        graph_endpoint="beta/teamwork", expected_value="Copilot app integration enabled",
        pass_criteria="When it is enabled", fail_criteria="When it is disabled",
        severity="critical", scoring_weight=5.0,
    )
    result["evaluated_value"] = "Microsoft Teams Copilot governance settings require PowerShell (Get-CsTeamsMeetingPolicy) and cannot be read via Graph API with app-only authentication. Manual verification required."
    return result


async def collect_meeting_transcription_enabled(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="meeting_transcription_enabled", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Meeting transcription enabled",
            pass_criteria="When it is enabled", fail_criteria="When it is disabled",
            severity="high", scoring_weight=4.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="meeting_transcription_enabled", service_name="Microsoft Teams",
        portal_location="Teams Admin Center > Meetings > Meeting policies",
        graph_endpoint="beta/teamwork", expected_value="Meeting transcription enabled",
        pass_criteria="When it is enabled", fail_criteria="When it is disabled",
        severity="high", scoring_weight=4.0,
    )


async def collect_meeting_recording_retention_policies(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="meeting_recording_retention_policies", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Meeting recording retention enabled",
            pass_criteria="When it is enabled", fail_criteria="When it is disabled",
            severity="medium", scoring_weight=3.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="meeting_recording_retention_policies", service_name="Microsoft Teams",
        portal_location="Teams Admin Center > Meetings > Meeting policies",
        graph_endpoint="beta/teamwork", expected_value="Meeting recording retention enabled",
        pass_criteria="When it is enabled", fail_criteria="When it is disabled",
        severity="medium", scoring_weight=3.0,
    )


async def collect_meeting_policies_configuration(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="meeting_policies_configuration", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Recommended Teams meeting policies configured",
            pass_criteria="When recommended settings are setup",
            fail_criteria="When recommended settings aren't setup",
            severity="high", scoring_weight=4.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="meeting_policies_configuration", service_name="Microsoft Teams",
        portal_location="Teams Admin Center > Meetings > Meeting policies",
        graph_endpoint="beta/teamwork", expected_value="Recommended Teams meeting policies configured",
        pass_criteria="When recommended settings are setup",
        fail_criteria="When recommended settings aren't setup",
        severity="high", scoring_weight=4.0,
    )


async def collect_teams_channel_email_addresses(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="teams_channel_email_addresses", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork",
            expected_value="Restricted sender list configured for channel email",
            pass_criteria="This will restrict Teams channels to allow accepting channel emails only from these Restricted Domains",
            fail_criteria="This will not restrict Teams channels to allow accepting channel emails only from these Restricted Domains",
            severity="low", scoring_weight=2.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="teams_channel_email_addresses", service_name="Microsoft Teams",
        portal_location="Teams Admin Center > Org-wide settings > Teams settings > Email integration",
        graph_endpoint="beta/teamwork",
        expected_value="Restricted sender list configured for channel email",
        pass_criteria="This will restrict Teams channels to allow accepting channel emails only from these Restricted Domains",
        fail_criteria="This will not restrict Teams channels to allow accepting channel emails only from these Restricted Domains",
        severity="low", scoring_weight=2.0,
    )


async def collect_teams_lobby_bypass(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="teams_lobby_bypass", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Lobby bypass set to Never",
            pass_criteria="Specifies whether participants can bypass the lobby when joining the meeting - Never",
            fail_criteria="Specifies whether participants can bypass the lobby when joining the meeting - Anyone",
            severity="medium", scoring_weight=3.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="teams_lobby_bypass", service_name="Microsoft Teams",
        portal_location="Teams Admin Center > Meetings > Meeting policies",
        graph_endpoint="beta/teamwork", expected_value="Lobby bypass set to Never",
        pass_criteria="Specifies whether participants can bypass the lobby when joining the meeting - Never",
        fail_criteria="Specifies whether participants can bypass the lobby when joining the meeting - Anyone",
        severity="medium", scoring_weight=3.0,
    )


async def collect_teams_meeting_chat(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="teams_meeting_chat", service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Meeting chat enabled",
            pass_criteria="Enabled: Participants are allowed to use chat during and after the meeting.",
            fail_criteria="Disabled: Meeting chat is disabled",
            severity="medium", scoring_weight=3.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="teams_meeting_chat", service_name="Microsoft Teams",
        portal_location="Teams Admin Center > Meetings > Meeting policies",
        graph_endpoint="beta/teamwork", expected_value="Meeting chat enabled",
        pass_criteria="Enabled: Participants are allowed to use chat during and after the meeting.",
        fail_criteria="Disabled: Meeting chat is disabled",
        severity="medium", scoring_weight=3.0,
    )


async def collect_third_party_apps_allowed(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "third_party_apps_allowed"
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key=parameter_key, service_name="Microsoft Teams",
            graph_endpoint="beta/teamwork", expected_value="Third-party/custom apps disabled",
            pass_criteria="Disabled — custom apps are unavailable in the organization's app",
            fail_criteria="Enabled — custom apps are available in the organization's app",
            severity="high", scoring_weight=4.0,
        )
    endpoint = "https://graph.microsoft.com/beta/teamwork/teamsAppSettings"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _governance_unverifiable_fail(
            tenant, parameter_key=parameter_key, service_name="Microsoft Teams",
            portal_location="Teams Admin Center > Teams apps > Permission policies",
            graph_endpoint=endpoint, expected_value="Third-party/custom apps disabled",
            pass_criteria="Disabled — custom apps are unavailable in the organization's app",
            fail_criteria="Enabled — custom apps are available in the organization's app",
            severity="high", scoring_weight=4.0,
        )
    settings = response.get("response") or {}
    sideloading_enabled = settings.get("isSideloadingEnabledForOrg", True)
    if sideloading_enabled:
        status = "fail"
        actual_msg = "Third-party app sideloading is enabled (isSideloadingEnabledForOrg=True) — custom apps can be installed"
        finding = "Custom app sideloading enabled — disable to prevent unauthorized app installs"
    else:
        status = "pass"
        actual_msg = "Third-party app sideloading is disabled (isSideloadingEnabledForOrg=False)"
        finding = "Custom app sideloading disabled — recommended security posture"
    evidence = _evaluation_evidence(
        pass_criteria="Disabled — custom apps are unavailable in the organization's app",
        fail_criteria="Enabled — custom apps are available in the organization's app",
        reasoning=finding,
        extra={"tenant_id": tenant.tenant_id, "isSideloadingEnabledForOrg": sideloading_enabled, "teams_app_settings": settings},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"isSideloadingEnabledForOrg": sideloading_enabled, "message": actual_msg},
        expected_value="Third-party/custom apps disabled",
        finding=finding,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"teams_app_settings": settings},
        graph_calls=2,
        scoring_weight=4.0,
    )


def _powershell_limitation_result(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    command: str,
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
    reason: str | None = None,
) -> dict[str, Any]:
    reasoning = reason or "This approved control requires a delegated Microsoft 365 PowerShell or portal evidence source that is not available to the app-only Graph runtime."
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "powershell_command": command,
            "collection_status": "COLLECTION_ERROR",
            "runtime": "app_only_graph",
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="collection_error",
        severity=severity,
        actual_value={
            "collection_status": "COLLECTION_ERROR",
            "required_source": command,
            "reason": reasoning,
        },
        expected_value=expected_value,
        finding=reasoning,
        graph_endpoint="",
        evidence=evidence,
        raw_response={"powershell_required": command, "reason": reasoning},
        graph_calls=0,
        scoring_weight=scoring_weight,
    )


def _manual_validation_required_result(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    portal_location: str,
    validation_procedure: str,
    expected_evidence: str,
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
) -> dict[str, Any]:
    reasoning = "Microsoft does not expose a stable tenant automation endpoint for this control in the current app-only runtime."
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "collection_status": "MANUAL_VALIDATION_REQUIRED",
            "portal_location": portal_location,
            "validation_procedure": validation_procedure,
            "expected_evidence": expected_evidence,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="manual_validation_required",
        severity=severity,
        actual_value={
            "collection_status": "MANUAL_VALIDATION_REQUIRED",
            "portal_location": portal_location,
            "validation_procedure": validation_procedure,
            "expected_evidence": expected_evidence,
            "reason": reasoning,
        },
        expected_value=expected_value,
        finding=reasoning,
        graph_endpoint="",
        evidence=evidence,
        raw_response={"manual_validation_required": True, "portal_location": portal_location},
        graph_calls=0,
        scoring_weight=scoring_weight,
    )


async def _teams_service_available(tenant: ConnectedTenant) -> bool:
    response = await _graph_get_json_or_error(tenant, "https://graph.microsoft.com/beta/teamwork")
    return bool(response.get("ok"))


async def _exchange_service_available(tenant: ConnectedTenant) -> bool:
    response = await _graph_get_json_or_error(tenant, "https://graph.microsoft.com/beta/admin/exchange/settings")
    return bool(response.get("ok"))


def _service_unavailable_fail(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    service_name: str,
    graph_endpoint: str,
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
) -> dict[str, Any]:
    message = (
        f"{service_name} is not available in this tenant — service must be provisioned and "
        "licensed before M365 Copilot deployment. This is a readiness gap."
    )
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=message,
        extra={"tenant_id": tenant.tenant_id, "service_available": False, "service": service_name},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="fail",
        severity=severity,
        actual_value={"service_available": False, "service": service_name, "message": message},
        expected_value=expected_value,
        finding=f"{service_name} not available in tenant — readiness gap",
        graph_endpoint=graph_endpoint,
        evidence=evidence,
        raw_response={"service_available": False, "service": service_name},
        graph_calls=1,
        scoring_weight=scoring_weight,
    )


def _governance_unverifiable_fail(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    service_name: str,
    portal_location: str,
    graph_endpoint: str,
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
) -> dict[str, Any]:
    message = (
        f"{service_name} is available but this governance setting is not exposed via "
        f"app-only Graph API. Configure this setting at: {portal_location}. "
        "Treating as not configured — readiness gap."
    )
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=message,
        extra={"tenant_id": tenant.tenant_id, "service_available": True, "governance_verified": False},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="fail",
        severity=severity,
        actual_value={"service_available": True, "governance_verified": False, "message": message},
        expected_value=expected_value,
        finding=f"{service_name} governance not verifiable via Graph API — treat as not configured",
        graph_endpoint=graph_endpoint,
        evidence=evidence,
        raw_response={"service_available": True, "governance_verified": False},
        graph_calls=1,
        scoring_weight=scoring_weight,
    )


def _licensing_required_result(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    endpoint: str,
    required_sku: str,
    required_service: str,
    required_role: str,
    required_permissions: list[str],
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
    graph_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reasoning = (
        f"{required_service} requires {required_sku} license and is not available in this tenant. "
        f"Required role: {required_role}. Required permission(s): {', '.join(required_permissions)}. "
        "This is a readiness gap — provision the required license to meet Copilot prerequisites."
    )
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "graph_endpoint": endpoint,
            "collection_status": "LICENSING_GAP",
            "required_sku": required_sku,
            "required_service": required_service,
            "required_role": required_role,
            "required_permissions": required_permissions,
            "graph_response": graph_response,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="fail",
        severity=severity,
        actual_value={
            "collection_status": "LICENSING_GAP",
            "required_sku": required_sku,
            "required_service": required_service,
            "required_role": required_role,
            "required_permissions": required_permissions,
            "message": f"Required license not available: {required_sku}",
        },
        expected_value=expected_value,
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"graph_response": graph_response or {}, "licensing_gap": True},
        graph_calls=1 if endpoint else 0,
        scoring_weight=scoring_weight,
    )


def _graph_limitation_result(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    endpoint: str,
    response: dict[str, Any],
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
) -> dict[str, Any]:
    error = response.get("error") or {}
    reasoning = error.get("message") or "Microsoft Graph did not return supported data for this control."
    lowered = reasoning.lower()
    status = "fail" if any(token in lowered for token in ["license", "subscription", "premium", "not available"]) else "collection_error"
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "graph_endpoint": endpoint,
            "graph_response": response,
            "collection_status": status.upper(),
            "required_permissions": ["See collector feasibility report for this endpoint."],
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity=severity,
        actual_value={"collection_status": status.upper(), "error": error},
        expected_value=expected_value,
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"graph_response": response},
        graph_calls=1,
        scoring_weight=scoring_weight,
    )


async def collect_secure_score_percentage(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "secure_score_percentage"
    endpoint = "/security/secureScores"
    client = await _graph_client(tenant)
    try:
        response = await client.get(endpoint, params={"$top": "1"})
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        return _graph_limitation_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            response={"ok": False, "status_code": exc.response.status_code, "error": payload.get("error") or payload},
            expected_value="Secure score percentage >=80%",
            pass_criteria="When it is more than or equal to 80%",
            fail_criteria="When it is less than 80%",
            severity="critical",
            scoring_weight=5.0,
        )
    values = response.get("value") or []
    latest = values[0] if values else {}
    current = float(latest.get("currentScore") or 0)
    maximum = float(latest.get("maxScore") or 0)
    percentage = round(current / maximum * 100, 2) if maximum else 0.0
    status = "pass" if percentage > 70 else "fail"
    if status == "pass":
        reasoning = f"Secure score: {percentage}% (threshold: 70%)"
    else:
        reasoning = f"Secure score: {percentage}% — below 70% threshold"
    evidence = _evaluation_evidence(
        pass_criteria="When it is more than 70%",
        fail_criteria="When it is 70% or less",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "secure_score": latest, "secure_score_percentage": percentage},
    )
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"current_score": current, "max_score": maximum, "secure_score_percentage": percentage}, expected_value="Secure score percentage >70%", finding=reasoning, graph_endpoint="/security/secureScores?$top=1", evidence=evidence, raw_response={"secureScores": response}, graph_calls=1, scoring_weight=5.0)


async def collect_audit_logs_enabled(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "audit_logs_enabled"
    endpoint = "/auditLogs/directoryAudits"
    client = await _graph_client(tenant)
    try:
        response = await client.get(endpoint, params={"$top": "1"})
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        return _graph_limitation_result(tenant, parameter_key=parameter_key, endpoint=endpoint, response={"ok": False, "status_code": exc.response.status_code, "error": payload.get("error") or payload}, expected_value="Audit logs enabled and queryable", pass_criteria="If audit logs enabled this will hunt the results for query", fail_criteria="If audit logs not enabled we cannot get the logs for the query", severity="critical", scoring_weight=5.0)
    rows = response.get("value") or []
    status = "pass" if rows else "fail"
    reasoning = f"Directory audit log query returned {len(rows)} record(s)"
    evidence = _evaluation_evidence(pass_criteria="If audit logs enabled this will hunt the results for query", fail_criteria="If audit logs not enabled we cannot get the logs for the query", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "audit_records": rows})
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"audit_logs_queryable": bool(rows), "sample_count": len(rows)}, expected_value="Audit logs enabled and queryable", finding=reasoning, graph_endpoint="/auditLogs/directoryAudits?$top=1", evidence=evidence, raw_response={"directoryAudits": response}, graph_calls=1, scoring_weight=5.0)


async def collect_emergency_access_accounts(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "emergency_access_accounts"
    client = await _graph_client(tenant)
    graph_calls = 0

    # Tenant assessment rule: an emergency-access account is an enabled, cloud-only
    # *.onmicrosoft.com user with active Global Administrator membership and zero licenses.
    roles = await client.get("/directoryRoles", params={"$filter": "displayName eq 'Global Administrator'", "$select": "id,displayName"})
    graph_calls += 1
    role = (roles.get("value") or [None])[0]
    members: list[dict[str, Any]] = []
    if role:
        members_resp = await client.get(
            f"/directoryRoles/{role['id']}/members",
            params={"$select": "id,displayName,userPrincipalName,accountEnabled,onPremisesSyncEnabled,assignedLicenses"},
        )
        graph_calls += 1
        members = members_resp.get("value") or []

    evaluated_accounts: list[dict[str, Any]] = []
    emergency_accounts: list[dict[str, Any]] = []
    for user in members:
        user_principal_name = str(user.get("userPrincipalName") or "")
        assigned_licenses = user.get("assignedLicenses") or []
        account = {
            "id": user.get("id"),
            "displayName": user.get("displayName"),
            "userPrincipalName": user.get("userPrincipalName"),
            "accountEnabled": user.get("accountEnabled"),
            "cloudOnly": user.get("onPremisesSyncEnabled") is None,
            "onMicrosoftDomain": user_principal_name.lower().endswith(".onmicrosoft.com"),
            "assignedLicenseCount": len(assigned_licenses),
        }
        evaluated_accounts.append(account)
        if (
            account["accountEnabled"] is True
            and account["cloudOnly"] is True
            and account["onMicrosoftDomain"] is True
            and account["assignedLicenseCount"] == 0
        ):
            emergency_accounts.append(account)

    count = len(emergency_accounts)
    status = "pass" if count >= 1 else "fail"
    if status == "pass":
        account_names = ", ".join(
            str(account.get("displayName") or account.get("userPrincipalName") or account.get("id"))
            for account in emergency_accounts
        )
        finding = (
            f"{count} emergency access account(s) identified: enabled cloud-only "
            f"Global Administrator on the .onmicrosoft.com domain with 0 assigned licenses: {account_names}"
        )
    else:
        finding = "No break glass account is present"

    evidence = _evaluation_evidence(
        pass_criteria="When it is Present",
        fail_criteria="When not present",
        reasoning=finding,
        extra={
            "tenant_id": tenant.tenant_id,
            "global_admin_members": members,
            "evaluated_global_admin_accounts": evaluated_accounts,
            "emergency_access_accounts": emergency_accounts,
        },
    )
    result = _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value={
            "emergency_access_accounts": count,
            "global_admin_members": len(members),
            "qualification": "Enabled cloud-only Global Administrator on the tenant .onmicrosoft.com domain with 0 assigned licenses",
        },
        expected_value="At least one identifiable emergency access account",
        finding=finding,
        graph_endpoint="/directoryRoles + /directoryRoles/{id}/members",
        evidence=evidence,
        raw_response={"global_admin_members": members},
        graph_calls=graph_calls,
        scoring_weight=5.0,
    )
    # This Best Practice control remains Critical even when it passes.
    result["severity"] = "critical"
    return result


async def collect_custom_banned_password_list(tenant: ConnectedTenant) -> dict[str, Any]:
    """Collect Custom Banned Password List via Entra ID Directory Settings.

    The correct Microsoft Graph endpoint is GET /v1.0/settings (or /beta/settings).
    Look for the 'Password Rule Settings' entry (templateId 5cf42378-d67d-4f36-ba46-e8b86229381d).
    If no such setting exists the feature has never been configured → fail.
    If the setting exists, inspect whether EnableBannedPasswordCheck is enabled.
    """
    parameter_key = "custom_banned_password_list"
    _PASS_CRITERIA = "Custom banned password list is enabled."
    _FAIL_CRITERIA = "Custom banned password list is not enabled."
    _PASSWORD_RULE_TEMPLATE_ID = "5cf42378-d67d-4f36-ba46-e8b86229381d"

    # Primary: directory settings (v1.0 then beta)
    settings_endpoints = [
        "/settings",
        "https://graph.microsoft.com/beta/settings",
    ]
    all_responses: list[dict[str, Any]] = []

    for endpoint in settings_endpoints:
        resp = await _graph_get_json_or_error(tenant, endpoint)
        all_responses.append({"endpoint": endpoint, **resp})
        if not resp.get("ok"):
            continue

        body = resp.get("response") or {}
        parsed_direct = _parse_custom_banned_password_policy(body) if isinstance(body, dict) else {}
        if parsed_direct.get("configuration_exposed"):
            enabled = parsed_direct["password_protection_enabled"]
            custom_word_count = parsed_direct["custom_word_count"]
            reasoning = (
                f"Custom banned password list enabled: {enabled}; "
                f"custom banned terms reported by Graph: {custom_word_count}."
            )
            actual_value = {
                "enabled": enabled,
                "password_protection_enabled": enabled,
                "enforcement_mode": parsed_direct["enforcement_mode"],
                "custom_word_count": custom_word_count,
                "custom_banned_password_count": custom_word_count,
                "custom_words_present": custom_word_count > 0,
            }
            evidence = _evaluation_evidence(
                pass_criteria=_PASS_CRITERIA,
                fail_criteria=_FAIL_CRITERIA,
                reasoning=reasoning,
                extra={"tenant_id": tenant.tenant_id, "graph_endpoint": endpoint, **actual_value},
            )
            evidence["remediation"] = (
                "Enable the Microsoft Entra custom banned password list in Entra admin center "
                "> Protection > Authentication methods > Password protection."
            )
            return _collector_result(
                parameter_key=parameter_key,
                status="pass" if enabled else "fail",
                severity="critical",
                actual_value=actual_value,
                expected_value="Custom banned password list enabled",
                finding=(
                    "Custom banned password list is enforced"
                    if enabled
                    else "Custom banned password list is not enforced"
                ),
                graph_endpoint=endpoint,
                evidence=evidence,
                raw_response={"password_policy": body, "endpoint_used": endpoint},
                graph_calls=len(all_responses),
                scoring_weight=5.0,
            )

        settings_list: list[dict[str, Any]] = body.get("value") or []

        # Find the Password Rule Settings entry
        pwd_setting: dict[str, Any] | None = None
        for s in settings_list:
            if s.get("templateId") == _PASSWORD_RULE_TEMPLATE_ID or s.get("displayName") == "Password Rule Settings":
                pwd_setting = s
                break

        if pwd_setting is None:
            # Feature never configured in Entra — this is a definitive FAIL, not NOT_COLLECTED
            reasoning = (
                "No 'Password Rule Settings' directory setting was found in this tenant. "
                "The Custom Banned Password List feature has not been configured. "
                f"({len(settings_list)} directory settings exist; none match templateId {_PASSWORD_RULE_TEMPLATE_ID})."
            )
            evidence = _evaluation_evidence(
                pass_criteria=_PASS_CRITERIA,
                fail_criteria=_FAIL_CRITERIA,
                reasoning=reasoning,
                extra={
                    "tenant_id": tenant.tenant_id,
                    "graph_endpoint": endpoint,
                    "enabled": False,
                    "directory_settings_found": len(settings_list),
                    "password_rule_template_id": _PASSWORD_RULE_TEMPLATE_ID,
                },
            )
            evidence["remediation"] = (
                "In Entra admin center > Protection > Authentication methods > Password protection, "
                "enable Custom banned password list and add your organization's custom banned terms."
            )
            return _collector_result(
                parameter_key=parameter_key,
                status="fail",
                severity="critical",
                actual_value={"enabled": False, "custom_word_count": 0, "configured": False},
                expected_value="Custom banned password list enabled",
                finding="Custom banned password list is not enforced",
                graph_endpoint=endpoint,
                evidence=evidence,
                raw_response={"settings": settings_list, "endpoint_used": endpoint},
                graph_calls=len(all_responses),
                scoring_weight=5.0,
            )

        # Password Rule Settings found — extract the values array
        values: list[dict[str, Any]] = pwd_setting.get("values") or []
        val_map = {v.get("name", "").lower(): v.get("value", "") for v in values}

        enabled_raw = val_map.get("enablebannedpasswordcheck", "False")
        enabled = str(enabled_raw).strip().lower() in {"true", "1", "yes", "enabled"}

        onprem_enabled_raw = val_map.get("enablebannedpasswordcheckonpremises", "False")
        onprem_enabled = str(onprem_enabled_raw).strip().lower() in {"true", "1", "yes", "enabled"}

        enforcement_mode = val_map.get("bannedpasswordcheckonpremisesmode", "Audit")

        custom_passwords_raw = val_map.get("custombannedpasswords", "")
        custom_words = [w.strip() for w in custom_passwords_raw.replace("\n", ",").split(",") if w.strip()] if custom_passwords_raw else []
        custom_word_count = len(custom_words)

        status = "pass" if enabled else "fail"
        reasoning = (
            f"Custom banned password list enabled: {enabled}; "
            f"on-premises enforcement: {onprem_enabled} (mode: {enforcement_mode}); "
            f"custom banned terms reported by Graph: {custom_word_count}."
        )
        actual_value = {
            "enabled": enabled,
            "password_protection_enabled": enabled,
            "enforcement_mode": enforcement_mode,
            "custom_word_count": custom_word_count,
            "custom_banned_password_count": custom_word_count,
            "custom_words_present": custom_word_count > 0,
            "on_premises_enforcement": onprem_enabled,
        }
        evidence = _evaluation_evidence(
            pass_criteria=_PASS_CRITERIA,
            fail_criteria=_FAIL_CRITERIA,
            reasoning=reasoning,
            extra={
                "tenant_id": tenant.tenant_id,
                "graph_endpoint": endpoint,
                "setting_id": pwd_setting.get("id"),
                **actual_value,
            },
        )
        evidence["remediation"] = (
            "Enable the Microsoft Entra custom banned password list in Entra admin center "
            "> Protection > Authentication methods > Password protection."
        )
        return _collector_result(
            parameter_key=parameter_key,
            status=status,
            severity="critical",
            actual_value=actual_value,
            expected_value="Custom banned password list enabled",
            finding=(
                "Custom banned password list is enforced"
                if status == "pass"
                else "Custom banned password list is not enforced"
            ),
            graph_endpoint=endpoint,
            evidence=evidence,
            raw_response={"password_rule_setting": pwd_setting, "endpoint_used": endpoint},
            graph_calls=len(all_responses),
            scoring_weight=5.0,
        )

    # Both directory settings endpoints failed — fall back to legacy policy endpoints
    legacy_endpoints = [
        "https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/password",
        "https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy",
    ]
    for endpoint in legacy_endpoints:
        response = await _graph_get_json_or_error(tenant, endpoint)
        all_responses.append({"endpoint": endpoint, **response})
        if not response.get("ok"):
            continue
        policy = response.get("response") or {}
        parsed = _parse_custom_banned_password_policy(policy)
        if not parsed["configuration_exposed"]:
            continue
        enabled = parsed["password_protection_enabled"]
        custom_word_count = parsed["custom_word_count"]
        custom_words = parsed["custom_words"]
        status = "pass" if enabled else "fail"
        reasoning = (
            f"Password protection enabled: {enabled}; enforcement mode: {parsed['enforcement_mode']}; "
            f"custom banned password terms reported by Graph: {custom_word_count}."
        )
        actual_value = {
            "enabled": enabled,
            "password_protection_enabled": enabled,
            "enforcement_mode": parsed["enforcement_mode"],
            "custom_word_count": custom_word_count,
            "custom_banned_password_count": custom_word_count,
            "custom_words_present": custom_word_count > 0,
        }
        evidence = _evaluation_evidence(
            pass_criteria=_PASS_CRITERIA,
            fail_criteria=_FAIL_CRITERIA,
            reasoning=reasoning,
            extra={"tenant_id": tenant.tenant_id, "graph_endpoint": endpoint, **actual_value},
        )
        evidence["remediation"] = (
            "Enable the Microsoft Entra custom banned password list and enforce password validation across all users."
        )
        return _collector_result(
            parameter_key=parameter_key,
            status=status,
            severity="critical",
            actual_value=actual_value,
            expected_value="Custom banned password list enabled",
            finding=(
                "Custom banned password list is enforced"
                if status == "pass"
                else "Custom banned password list is not enforced"
            ),
            graph_endpoint=endpoint,
            evidence=evidence,
            raw_response={"password_protection_policy": policy, "endpoint_attempts": all_responses},
            graph_calls=len(all_responses),
            scoring_weight=5.0,
        )

    # All endpoints exhausted — definitively FAIL (not configured) rather than NOT_COLLECTED
    # If Graph was reachable for any call, absence of the setting IS a finding
    any_reachable = any(r.get("ok") for r in all_responses)
    if any_reachable:
        reasoning = (
            "Microsoft Graph was reachable but no Custom Banned Password List configuration "
            "was found in directory settings or authentication policy endpoints. "
            "The feature appears to be unconfigured for this tenant."
        )
        evidence = _evaluation_evidence(
            pass_criteria=_PASS_CRITERIA,
            fail_criteria=_FAIL_CRITERIA,
            reasoning=reasoning,
            extra={
                "tenant_id": tenant.tenant_id,
                "enabled": False,
                "portal_location": "Entra admin center > Protection > Authentication methods > Password protection",
            },
        )
        evidence["remediation"] = (
            "Configure Microsoft Entra Password Protection: enable the custom banned password list "
            "and add custom terms in Entra admin center > Protection > Authentication methods > Password protection."
        )
        return _collector_result(
            parameter_key=parameter_key,
            status="fail",
            severity="critical",
            actual_value={"enabled": False, "custom_word_count": 0, "configured": False},
            expected_value="Custom banned password list enabled",
            finding="Custom banned password list is not enforced",
            graph_endpoint=", ".join(settings_endpoints + legacy_endpoints),
            evidence=evidence,
            raw_response={"endpoint_attempts": all_responses},
            graph_calls=len(all_responses),
            scoring_weight=5.0,
        )

    return _collection_error_result(
        tenant,
        parameter_key=parameter_key,
        endpoint=settings_endpoints[0],
        required_api="Microsoft Graph Directory Settings (/v1.0/settings)",
        required_permissions=["Policy.Read.All", "Directory.Read.All"],
        expected_value="Custom banned password list enabled",
        pass_criteria=_PASS_CRITERIA,
        fail_criteria=_FAIL_CRITERIA,
        severity="critical",
        scoring_weight=5.0,
        response={"endpoint_attempts": all_responses},
        reason="All Microsoft Graph endpoints for password protection policy were unreachable.",
    )


def _parse_custom_banned_password_policy(policy: dict[str, Any]) -> dict[str, Any]:
    custom_words = _extract_custom_banned_words(policy)
    custom_word_count = _extract_custom_banned_word_count(policy, custom_words)
    enabled_value = _first_present(
        policy,
        [
            "isCustomBannedPasswordListEnabled",
            "customBannedPasswordListEnabled",
            "enableBannedPasswordCheck",
            "bannedPasswordCheckEnabled",
            "passwordProtectionEnabled",
            "isPasswordProtectionEnabled",
            "state",
        ],
    )
    enforcement_mode = str(
        _first_present(
            policy,
            [
                "enforcementMode",
                "mode",
                "passwordProtectionMode",
                "bannedPasswordCheckMode",
                "state",
            ],
        )
        or "unknown"
    )
    password_protection_enabled = _enabled_from_value(enabled_value, custom_word_count)
    configuration_exposed = any(
        key in policy
        for key in [
            "isCustomBannedPasswordListEnabled",
            "customBannedPasswordListEnabled",
            "customBannedPasswords",
            "bannedPasswords",
            "customBannedPasswordCount",
            "customWords",
            "enforcementMode",
            "passwordProtectionEnabled",
            "isPasswordProtectionEnabled",
            "state",
        ]
    )
    return {
        "configuration_exposed": configuration_exposed,
        "password_protection_enabled": password_protection_enabled,
        "enforcement_mode": enforcement_mode,
        "custom_word_count": custom_word_count,
        "custom_words": custom_words,
        "tenant_configuration_status": "configuration_exposed" if configuration_exposed else "configuration_not_exposed",
    }


def _extract_custom_banned_words(policy: dict[str, Any]) -> list[str]:
    for key in ("customBannedPasswords", "bannedPasswords", "customWords", "customBannedPasswordTerms"):
        value = policy.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.replace("\r", "\n").replace(",", "\n").split("\n") if item.strip()]
    nested = policy.get("customBannedPasswordList")
    if isinstance(nested, dict):
        return _extract_custom_banned_words(nested)
    return []


def _extract_custom_banned_word_count(policy: dict[str, Any], words: list[str]) -> int:
    for key in ("customBannedPasswordCount", "customWordCount", "bannedPasswordCount", "count"):
        value = policy.get(key)
        if value in {None, ""}:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return len(words)


def _first_present(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in payload and payload[key] not in {None, ""}:
            return payload[key]
    return None


def _enabled_from_value(value: Any, custom_word_count: int) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"enabled", "enforced", "enforce", "on", "true"}:
            return True
        if normalized in {"disabled", "off", "false"}:
            return False
    return custom_word_count > 0


def _classify_custom_banned_password_failure(responses: list[dict[str, Any]]) -> dict[str, str]:
    if not responses:
        return {"status": "collection_error", "endpoint": "", "reason": "No Microsoft Graph endpoint was attempted."}
    messages = " ".join(_error_message(item) for item in responses).lower()
    endpoint = str(responses[-1].get("endpoint") or "")
    if any(token in messages for token in ["license", "subscription", "premium", "requires azure ad premium", "requires microsoft entra id p"]):
        return {"status": "licensing_gap", "endpoint": endpoint, "reason": _error_message(responses[-1])}
    if any(item.get("ok") for item in responses):
        return {
            "status": "manual_validation_required",
            "endpoint": endpoint,
            "reason": "Microsoft Graph was reachable but did not expose Custom Banned Password List fields for this tenant/runtime.",
        }
    if any(token in messages for token in ["does not exist", "not found", "unknown", "unsupported", "resource not found", "invalid version", "invalid request"]):
        return {
            "status": "manual_validation_required",
            "endpoint": endpoint,
            "reason": "Microsoft Graph did not expose Custom Banned Password List configuration for this tenant/runtime.",
        }
    return {"status": "collection_error", "endpoint": endpoint, "reason": _error_message(responses[-1])}


async def collect_sensitivity_labels_applied_to_teams(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "sensitivity_labels_applied_to_teams"
    if not await _teams_service_available(tenant):
        return _service_unavailable_fail(
            tenant,
            parameter_key=parameter_key,
            service_name="Microsoft Teams",
            graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')&$select=id,displayName,assignedLabels,resourceProvisioningOptions",
            expected_value="Sensitivity labels applied to Teams",
            pass_criteria="If labels is configured and applied",
            fail_criteria="If labels is not configured and applied, or Microsoft Teams is unavailable",
            severity="critical",
            scoring_weight=5.0,
        )
    client = await _graph_client(tenant)
    endpoint = "/groups"
    params = {"$filter": "resourceProvisioningOptions/Any(x:x eq 'Team')", "$select": "id,displayName,assignedLabels,resourceProvisioningOptions"}
    response = await _get_all(client, endpoint, params=params)
    teams = response.get("value") or []
    labeled = [team for team in teams if team.get("assignedLabels")]
    status = "pass" if labeled else "fail"
    reasoning = f"{len(labeled)} team(s) have assigned sensitivity labels out of {len(teams)} team(s)"
    evidence = _evaluation_evidence(pass_criteria="If labels is configured and applied", fail_criteria="If labels is not configured and applied", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "teams": teams, "labeled_teams": labeled})
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"labeled_teams": len(labeled), "total_teams": len(teams)}, expected_value="Sensitivity labels applied to Teams", finding=reasoning, graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')&$select=id,displayName,assignedLabels,resourceProvisioningOptions", evidence=evidence, raw_response={"groups": response}, graph_calls=1, scoring_weight=5.0)


async def _sensitivity_label_graph_collector(tenant: ConnectedTenant, *, parameter_key: str, severity: str, scoring_weight: float) -> dict[str, Any]:
    """Validate that sensitivity labels are CONFIGURED **and actually APPLIED**.

    The previous implementation passed whenever any label merely existed in the
    tenant — a false PASS, because a configured-but-never-applied label protects
    nothing. This collector combines two supported, documented Microsoft Graph
    signals and is shared by every sensitivity-label parameter (single source of
    truth — no duplicated per-parameter logic):

      1. Configured labels — GET /security/informationProtection/sensitivityLabels
         (Microsoft Purview Information Protection; InformationProtectionPolicy.Read.All).
         A failure here is a licensing/permission gap, not a plain FAIL.
         https://learn.microsoft.com/graph/api/security-informationprotection-list-sensitivitylabels
      2. Applied labels — GET /groups?$filter=groupTypes/any(c:c eq 'Unified')
         &$select=id,displayName,assignedLabels (v1.0; Group.Read.All). A label in a
         container's assignedLabels proves it is applied to that Microsoft 365
         group / Team / group-connected SharePoint site.
         https://learn.microsoft.com/graph/api/group-list

    PASS only when at least one label is configured AND at least one container
    carries an applied label. Configured-but-never-applied is a FAIL.

    Limitation: app-only Graph exposes container-level (group/site) application, not
    per-file labelling; that is documented in the evidence rather than guessed at.
    """
    labels_endpoint = "https://graph.microsoft.com/beta/security/informationProtection/sensitivityLabels"
    _PASS = "At least one sensitivity label is configured AND applied to a Microsoft 365 container"
    _FAIL = "No labels configured, or labels configured but not applied to any container"

    label_response = await _graph_get_json_or_error(tenant, labels_endpoint)
    if not label_response.get("ok"):
        # Licensing (no Purview IP) or permission (missing InformationProtectionPolicy.Read.All).
        return _licensing_required_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=labels_endpoint,
            required_sku="Microsoft 365 E5 / E5 Compliance or Microsoft Purview Information Protection",
            required_service="Microsoft Purview Information Protection",
            required_role="Compliance Administrator or Information Protection Administrator",
            required_permissions=["InformationProtectionPolicy.Read.All", "Group.Read.All"],
            expected_value="Sensitivity labels configured and applied to Microsoft 365 containers",
            pass_criteria=_PASS,
            fail_criteria=_FAIL,
            severity=severity,
            scoring_weight=scoring_weight,
            graph_response=label_response,
        )
    configured_labels = (label_response.get("response") or {}).get("value") or []

    # Application signal: Microsoft 365 group containers (Teams / group-connected
    # SharePoint sites) carrying an assigned sensitivity label.
    groups_endpoint = "/groups?$filter=groupTypes/any(c:c eq 'Unified')&$select=id,displayName,assignedLabels"
    client = await _graph_client(tenant)
    try:
        groups_response = await _get_all(
            client,
            "/groups",
            params={"$filter": "groupTypes/any(c:c eq 'Unified')", "$select": "id,displayName,assignedLabels"},
        )
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=groups_endpoint,
            required_api="Microsoft Graph /groups (assignedLabels)",
            required_permissions=["Group.Read.All"],
            expected_value="Sensitivity labels configured and applied to Microsoft 365 containers",
            pass_criteria=_PASS,
            fail_criteria=_FAIL,
            severity=severity,
            scoring_weight=scoring_weight,
            response={"ok": False, "status_code": exc.response.status_code, "error": payload.get("error") or payload},
        )

    groups = groups_response.get("value") or []
    applied = [
        {
            "id": g.get("id"),
            "displayName": g.get("displayName"),
            "assignedLabels": [
                (label.get("displayName") or label.get("labelId")) for label in (g.get("assignedLabels") or [])
            ],
        }
        for g in groups
        if g.get("assignedLabels")
    ]
    configured_count = len(configured_labels)
    applied_count = len(applied)
    container_count = len(groups)

    if configured_count == 0:
        status = "fail"
        reasoning = "No sensitivity labels are configured in this tenant, so none can be applied."
    elif applied_count == 0:
        status = "fail"
        reasoning = (
            f"{configured_count} sensitivity label(s) are configured but none are applied to any of the "
            f"{container_count} Microsoft 365 group / Team / SharePoint site container(s) — labels exist but "
            "are not in use."
        )
    else:
        status = "pass"
        reasoning = (
            f"{applied_count} of {container_count} Microsoft 365 container(s) have a sensitivity label applied "
            f"({configured_count} label(s) configured)."
        )

    remediation = (
        "Publish sensitivity labels and enable a label policy (default/auto-labelling) so they are applied to "
        "Microsoft 365 groups, Teams, SharePoint sites and content: Microsoft Purview portal > Information "
        "Protection > Labels and Label policies."
    )
    evidence = _evaluation_evidence(
        pass_criteria=_PASS,
        fail_criteria=_FAIL,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "configured_label_count": configured_count,
            "applied_container_count": applied_count,
            "total_container_count": container_count,
            "applied_containers": applied[:50],
            "configured_labels": [
                (label.get("name") or label.get("displayName")) for label in configured_labels
            ][:50],
            "data_source": "Graph /security/informationProtection/sensitivityLabels (configured) + /groups assignedLabels (applied)",
            "measures": "container-level label application (Microsoft 365 groups/Teams/SharePoint sites); per-file labelling is not exposed by a supported app-only Graph API",
            "remediation": remediation,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity=severity,
        actual_value={
            "configured_label_count": configured_count,
            "applied_container_count": applied_count,
            "total_container_count": container_count,
        },
        expected_value="Sensitivity labels configured AND applied to Microsoft 365 containers",
        finding=reasoning,
        graph_endpoint="/security/informationProtection/sensitivityLabels + /groups?$select=assignedLabels",
        evidence=evidence,
        raw_response={"sensitivityLabels": label_response.get("response"), "groups": groups_response},
        graph_calls=2,
        scoring_weight=scoring_weight,
    )


async def collect_sensitivity_labels_configured_and_applied(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _sensitivity_label_graph_collector(tenant, parameter_key="sensitivity_labels_configured_and_applied", severity="critical", scoring_weight=5.0)


async def collect_information_protection_labels_applied(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _sensitivity_label_graph_collector(tenant, parameter_key="information_protection_labels_applied", severity="critical", scoring_weight=5.0)


async def collect_sensitivity_labels_are_applied(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _sensitivity_label_graph_collector(tenant, parameter_key="sensitivity_labels_are_applied", severity="info", scoring_weight=1.0)


async def collect_storage_quota_consumption(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "storage_quota_consumption"
    endpoint = "/reports/getSharePointSiteUsageDetail(period='D30')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(tenant=tenant, parameter_key=parameter_key, report=report, expected_value="<90% SharePoint storage quota consumption", pass_criteria="When it is less than 90%", fail_criteria="When it is more than or equal to 90%", graph_endpoint=endpoint, severity="info", scoring_weight=1.0)
    sites = []
    over = []
    for row in rows:
        used = _float_value(row, "Storage Used (Byte)")
        allocated = _float_value(row, "Storage Allocated (Byte)")
        ratio = round(used / allocated * 100, 2) if allocated else 0.0
        item = {"siteUrl": row.get("Site URL"), "storageUsedBytes": used, "storageAllocatedBytes": allocated, "storage_quota_ratio": ratio}
        sites.append(item)
        if ratio >= 90:
            over.append(item)
    max_ratio = max([item["storage_quota_ratio"] for item in sites], default=0.0)
    total_used = sum(item["storageUsedBytes"] for item in sites)
    total_allocated = sum(item["storageAllocatedBytes"] for item in sites)

    def _fmt_bytes(num: float) -> str:
        tb = num / (1024 ** 4)
        if tb >= 1:
            return f"{round(tb, 2)} TB"
        gb = num / (1024 ** 3)
        if gb >= 1:
            return f"{round(gb, 2)} GB"
        return f"{round(num / (1024 ** 2), 2)} MB"

    status = "pass" if not over else "fail"
    # Sum of per-site "Storage Allocated" is each site's max quota CEILING (SharePoint
    # over-provisions ~25 TB/site), not the tenant's purchased storage — so it is not a
    # meaningful denominator. Report real usage across sites instead of a misleading total.
    reasoning = f"{_fmt_bytes(total_used)} used across {len(sites)} SharePoint site(s)"
    if over:
        reasoning += f" — {len(over)} site(s) at or above 90% of their quota (max {max_ratio}%)"
    evidence = _evaluation_evidence(pass_criteria="When it is less than 90%", fail_criteria="When it is more than or equal to 90%", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sites": sites, "over_threshold": over, "storage_quota_consumption": max_ratio, "total_used_bytes": total_used, "total_allocated_bytes": total_allocated})
    return _collector_result(parameter_key=parameter_key, status=status, severity="info", actual_value={"sites_over_90_percent": len(over), "site_count": len(sites), "max_storage_quota_ratio": max_ratio, "total_used_bytes": total_used, "total_allocated_bytes": total_allocated}, expected_value="<90% SharePoint storage quota consumption", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"csv_rows": rows}, graph_calls=1, scoring_weight=1.0)


async def collect_checking_sharing_permissions_for_each_sites_on_a_tenant(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "checking_sharing_permissions_for_each_sites_on_a_tenant"
    endpoint = "/sites?search=*"
    client = await _graph_client(tenant)
    try:
        response = await _get_all(client, "/sites", params={"search": "*"})
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        return _licensing_required_result(tenant, parameter_key=parameter_key, endpoint=endpoint, required_sku="SharePoint Online", required_service="SharePoint site permissions", required_role="SharePoint Administrator or Global Administrator", required_permissions=["Sites.FullControl.All"], expected_value="Site sharing permissions reviewed", pass_criteria="Result on which sites shared externally if more or less, less sites shared externally can be considered as pass", fail_criteria="More sites sharing externally and we can have guest access expiration period", severity="info", scoring_weight=1.0, graph_response={"ok": False, "status_code": exc.response.status_code, "error": payload.get("error") or payload})
    sites = response.get("value") or []
    permission_rows = []
    graph_calls = 1
    for site in sites:
        site_id = site.get("id")
        if not site_id:
            continue
        try:
            permissions = await _get_all(client, f"/sites/{site_id}/permissions")
            graph_calls += 1
        except httpx.HTTPStatusError as exc:
            try:
                payload = exc.response.json()
            except ValueError:
                payload = {"error": {"message": exc.response.text}}
            return _licensing_required_result(tenant, parameter_key=parameter_key, endpoint=f"/sites/{site_id}/permissions", required_sku="SharePoint Online", required_service="SharePoint site permissions", required_role="SharePoint Administrator or Global Administrator", required_permissions=["Sites.FullControl.All"], expected_value="Site sharing permissions reviewed", pass_criteria="Result on which sites shared externally if more or less, less sites shared externally can be considered as pass", fail_criteria="More sites sharing externally and we can have guest access expiration period", severity="info", scoring_weight=1.0, graph_response={"ok": False, "status_code": exc.response.status_code, "error": payload.get("error") or payload})
        for permission in permissions.get("value") or []:
            permission_rows.append({
                "siteId": site_id,
                "siteName": site.get("displayName") or site.get("name"),
                "siteUrl": site.get("webUrl"),
                "permissionId": permission.get("id"),
                "roles": permission.get("roles"),
                "link": permission.get("link"),
                "grantedTo": permission.get("grantedToV2") or permission.get("grantedTo"),
                "grantedToIdentities": permission.get("grantedToIdentitiesV2") or permission.get("grantedToIdentities"),
            })
    external_permissions = [item for item in permission_rows if item.get("link") or item.get("grantedToIdentities")]
    status = "pass" if not external_permissions else "fail"
    reasoning = f"{len(permission_rows)} permission grant(s) reviewed across {len(sites)} SharePoint site(s); {len(external_permissions)} grant(s) indicate sharing links or external identities"
    evidence = _evaluation_evidence(pass_criteria="Result on which sites shared externally if more or less, less sites shared externally can be considered as pass", fail_criteria="More sites sharing externally and we can have guest access expiration period", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sites": sites, "permissions": permission_rows, "external_permissions": external_permissions})
    return _collector_result(parameter_key=parameter_key, status=status, severity="info", actual_value={"site_count": len(sites), "permission_count": len(permission_rows), "external_permission_count": len(external_permissions)}, expected_value="Site sharing permissions reviewed", finding=reasoning, graph_endpoint="/sites?search=* + /sites/{id}/permissions", evidence=evidence, raw_response={"sites": response, "permissions": permission_rows}, graph_calls=graph_calls, scoring_weight=1.0)


async def collect_getting_all_sites_with_sensitivity_keywords_on_a_tenant(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "getting_all_sites_with_sensitivity_keywords_on_a_tenant"
    _PASS = "Sensitive sites are excluded from Copilot search via SharePoint Advanced Management"
    _FAIL = "Sensitive sites are not excluded from Copilot search"
    # "Sensitive SharePoint site excluded from Copilot search" (restricted content
    # discovery) is a SharePoint Advanced Management (SAM) feature. Without the SAM
    # license the control cannot be configured or verified.
    sam_licensed, sku_parts, sku_response = await _sharepoint_advanced_management_licensed(tenant)
    if not sam_licensed:
        return _sam_unavailable_result(parameter_key=parameter_key, tenant=tenant, sku_parts=sku_parts, sku_response=sku_response, pass_criteria=_PASS, fail_criteria=_FAIL, severity="critical", scoring_weight=1.0)
    client = await _graph_client(tenant)
    endpoint = "/sites"
    try:
        response = await _get_all(client, endpoint, params={"search": "*"})
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        return _licensing_required_result(tenant, parameter_key=parameter_key, endpoint="/sites?search=*", required_sku="SharePoint Online", required_service="SharePoint site inventory", required_role="SharePoint Administrator or Global Administrator", required_permissions=["Sites.Read.All"], expected_value="Sites with sensitivity keywords identified when present", pass_criteria="This will give accurate result for sensitivity sites if anything exist", fail_criteria="If there is no sites with sensitivity keywords then we can consider there are no sites with sensitive information.", severity="info", scoring_weight=1.0, graph_response={"ok": False, "status_code": exc.response.status_code, "error": payload.get("error") or payload})
    sites = response.get("value") or []
    keywords = ("confidential", "sensitive", "restricted", "secret", "private")
    matched = [
        site for site in sites
        if any(keyword in f"{site.get('name')} {site.get('displayName')} {site.get('webUrl')}".lower() for keyword in keywords)
    ]
    status = "pass" if matched else "fail"
    reasoning = f"{len(matched)} site(s) matched sensitivity keywords out of {len(sites)} site(s)"
    evidence = _evaluation_evidence(pass_criteria="This will give accurate result for sensitivity sites if anything exist", fail_criteria="If there is no sites with sensitivity keywords then we can consider there are no sites with sensitive information.", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "keywords": keywords, "matched_sites": matched, "sites": sites})
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"sensitivity_keyword_site_count": len(matched), "site_count": len(sites)}, expected_value="Sites with sensitivity keywords identified when present", finding=reasoning, graph_endpoint="/sites?search=*", evidence=evidence, raw_response={"sites": response}, graph_calls=1, scoring_weight=1.0)


# ---------------------------------------------------------------------------
# Microsoft Purview Compliance Manager — overall Compliance Score
#
# Verified against official Microsoft documentation (2026-07-08):
#   - https://learn.microsoft.com/graph/compliance-concept-overview
#     Lists every compliance/privacy capability Microsoft Graph exposes:
#     eDiscovery, subject rights requests, and records management. There is
#     no Compliance Manager score API in v1.0 or beta.
#   - https://learn.microsoft.com/purview/compliance-manager
#     Compliance Manager's overall Compliance Score is a portal-only
#     (compliance.microsoft.com/compliancemanager) experience.
#   - https://learn.microsoft.com/office365/servicedescriptions/microsoft-365-service-descriptions/microsoft-365-tenantlevel-services-licensing-guidance/microsoft-purview-service-description
#     Compliance Manager requires an Office 365 / Microsoft 365 subscription
#     (or GCC/GCC High/DoD).
#
# Microsoft Graph's `/security/secureScores` is a DIFFERENT product (Secure
# Score measures identity/device/app security posture) and must never be
# reported as the Compliance Score. This collector therefore never calls
# Secure Score and never estimates a compliance percentage of its own.
#
# Business rule — this parameter returns ONLY "pass" or "fail":
#   PASS  = the official Compliance Manager score was retrieved AND is >= 80%.
#   FAIL  = the score is < 80%, OR it could not be retrieved for any reason
#           (no supported API, missing licensing, missing permissions,
#           Compliance Manager not provisioned, or API/service errors).
# The CRA readiness score is computed on pass/fail only, so any control that
# cannot be validated is a failed readiness requirement. The `reason` (finding)
# text always carries the specific root cause for the dashboard and report.
#
# Because Microsoft exposes no supported API today, the retrieval below always
# yields score=None and the collector fails with a specific reason. The
# _evaluate_compliance_score() helper keeps the >=80% pass path ready for the
# day a real API exists — replace `_retrieve_compliance_manager_score()` with
# a genuine call and the pass/fail logic already holds.
# ---------------------------------------------------------------------------
COMPLIANCE_MANAGER_ELIGIBLE_SKU_PARTS = {
    # Per the Purview service description (see citation above): "Compliance
    # Manager is available to organizations with Office 365 and Microsoft
    # 365 licenses (incl. Business Premium), and to US Government Community
    # Cloud (GCC), GCC High, and Department of Defense (DoD) customers."
    "ENTERPRISEPACK",       # Office 365 E3
    "ENTERPRISEPREMIUM",    # Office 365 E5
    "SPE_E3",               # Microsoft 365 E3
    "SPE_E5",               # Microsoft 365 E5
    "O365_BUSINESS_PREMIUM",
    "SPB",                  # Microsoft 365 Business Premium
    "STANDARDWOFFPACK",     # Office 365 E1
    "M365EDU_A3_FACULTY",
    "M365EDU_A5_FACULTY",
}

_COMPLIANCE_SCORE_PASS_THRESHOLD = 80.0

_COMPLIANCE_SCORE_NOT_AVAILABLE_REASON = (
    "Microsoft Purview Compliance Manager does not expose an officially supported "
    "public API for retrieving the overall Compliance Score, so it cannot be "
    "validated automatically and is treated as a failed readiness requirement."
)


async def collect_compliance_score_overview(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "compliance_score_overview"
    endpoint = "/subscribedSkus"

    # Determine the specific root cause. `score` stays None until Microsoft
    # ships a supported Compliance Manager score API. `root_cause` is a stable
    # machine code; `reason` is the human-readable explanation for the report.
    score: float | None = None
    root_cause = "api_not_supported"
    reason = _COMPLIANCE_SCORE_NOT_AVAILABLE_REASON
    graph_response: dict[str, Any] | None = None
    licensed_sku_parts: list[str] = []

    try:
        sku_response = await _subscribed_skus(tenant)
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        error = payload.get("error") or payload
        status_code = exc.response.status_code
        graph_response = {"status_code": status_code, "error": error}
        if status_code in (401, 403):
            root_cause = "insufficient_permissions"
            reason = (
                f"{_COMPLIANCE_SCORE_NOT_AVAILABLE_REASON} The CRA application also lacks Microsoft "
                "Graph permission to read tenant licensing (grant Organization.Read.All to the app "
                "registration and re-run the assessment)."
            )
        else:
            root_cause = "service_error"
            reason = (
                f"{_COMPLIANCE_SCORE_NOT_AVAILABLE_REASON} A Microsoft Graph error also prevented "
                f"licensing verification: {error.get('message') or error}"
            )
        sku_response = {"value": []}
    else:
        skus = sku_response.get("value") or []
        licensed_sku_parts = sorted(
            {
                str(sku.get("skuPartNumber") or "").upper()
                for sku in skus
                if float(sku.get("consumedUnits") or 0) > 0
            }
        )
        if not set(licensed_sku_parts) & COMPLIANCE_MANAGER_ELIGIBLE_SKU_PARTS:
            root_cause = "licensing_required"
            reason = (
                f"{_COMPLIANCE_SCORE_NOT_AVAILABLE_REASON} Additionally, no Office 365 or Microsoft "
                "365 subscription that entitles Compliance Manager (e.g., E3/E5, Business Premium, "
                "GCC/GCC High/DoD) was found assigned in this tenant."
            )

    # Business rule: pass only when a real score was retrieved and is >= 80%.
    if score is not None and score >= _COMPLIANCE_SCORE_PASS_THRESHOLD:
        status = "pass"
        root_cause = "score_met_threshold"
        reason = f"Compliance Manager score is {score}% (>= {int(_COMPLIANCE_SCORE_PASS_THRESHOLD)}% threshold)."
    elif score is not None:
        status = "fail"
        root_cause = "score_below_threshold"
        reason = f"Compliance Manager score is {score}% — below the {int(_COMPLIANCE_SCORE_PASS_THRESHOLD)}% threshold."
    else:
        status = "fail"  # score could not be retrieved — reason/root_cause set above

    _log("COMPLIANCE_SCORE_PATH", parameter_key=parameter_key, status=status, root_cause=root_cause)

    evidence = _evaluation_evidence(
        pass_criteria=f"Official Compliance Manager score is retrieved and is >= {int(_COMPLIANCE_SCORE_PASS_THRESHOLD)}%.",
        fail_criteria=(
            f"Score is < {int(_COMPLIANCE_SCORE_PASS_THRESHOLD)}%, or the official score cannot be "
            "retrieved for any reason (unsupported API, missing licensing, missing permissions, "
            "Compliance Manager not provisioned, or service errors)."
        ),
        reasoning=reason,
        extra={
            "tenant_id": tenant.tenant_id,
            "root_cause": root_cause,
            "compliance_manager_score": score,
            "licensed_sku_parts_detected": licensed_sku_parts,
            "data_source": "Microsoft Graph /subscribedSkus (licensing signal only — no Graph API exposes the Compliance Manager score)",
            "graph_response": graph_response,
            "reference_urls": [
                "https://learn.microsoft.com/graph/compliance-concept-overview",
                "https://learn.microsoft.com/purview/compliance-manager",
                "https://learn.microsoft.com/office365/servicedescriptions/microsoft-365-service-descriptions/microsoft-365-tenantlevel-services-licensing-guidance/microsoft-purview-service-description",
            ],
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value={"compliance_manager_score": score, "root_cause": root_cause},
        expected_value=f"Official Microsoft Purview Compliance Manager score >= {int(_COMPLIANCE_SCORE_PASS_THRESHOLD)}%",
        finding=reason,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"subscribedSkus": sku_response, "graph_response": graph_response},
        graph_calls=1,
        scoring_weight=5.0,
    )


async def collect_auto_expiration_policy_for_inactive_m365_groups(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "auto_expiration_policy_for_inactive_m365_groups"
    endpoint = "/groupLifecyclePolicies"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_api="Microsoft Graph group lifecycle policies",
            required_permissions=["Directory.Read.All", "Group.Read.All"],
            expected_value="Auto-expiration policy for inactive Microsoft 365 groups is configured",
            pass_criteria="Auto-expiration policy for inactive M365 groups is configured",
            fail_criteria="Auto-expiration policy for inactive M365 groups is not configured",
            severity="medium",
            scoring_weight=3.0,
            response=response,
            command="Get-MgGroupLifecyclePolicy",
        )
    policies = (response.get("response") or {}).get("value") or []
    active_policies = [policy for policy in policies if int(policy.get("groupLifetimeInDays") or 0) > 0]
    status = "pass" if active_policies else "fail"
    reasoning = f"{len(active_policies)} active group lifecycle policie(s) found out of {len(policies)} returned"
    evidence = _evaluation_evidence(
        pass_criteria="Auto-expiration policy for inactive M365 groups is configured",
        fail_criteria="Auto-expiration policy for inactive M365 groups is not configured",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "group_lifecycle_policies": policies, "active_policies": active_policies},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="medium",
        actual_value={"policy_count": len(policies), "active_policy_count": len(active_policies)},
        expected_value="Auto-expiration policy for inactive Microsoft 365 groups is configured",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"groupLifecyclePolicies": response.get("response")},
        graph_calls=1,
        scoring_weight=3.0,
    )


async def collect_audit_log_retention_duration(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "audit_log_retention_duration"
    try:
        from app.services.powershell import PowerShellExecutionEngine

        ps_engine = PowerShellExecutionEngine()
        result = await ps_engine.execute_purview_collector(
            tenant_id=tenant.tenant_id,
            collector_name="powershell.audit_log_retention_duration",
            parameter_key=parameter_key,
        )

        if result.get("status") == "error" or not result.get("ok"):
            return _governance_unverifiable_fail(
                tenant,
                parameter_key=parameter_key,
                service_name="Microsoft Purview",
                portal_location="Purview Compliance Portal > Audit > Retention Policies",
                expected_value="Audit log retention policy configured",
                pass_criteria="When policies are set up",
                fail_criteria="When no policies are set up",
                severity="medium",
                scoring_weight=3.0,
            )

        policies = result.get("policies", [])

        if not policies or len(policies) == 0:
            reasoning = "No audit log retention policy configured"
            status = "fail"
            actual_value = {"audit_log_retention_policies_count": 0}
        else:
            highest_priority_policy = policies[0]
            retention_duration = highest_priority_policy.get("RetentionDuration", "Unknown")
            policy_name = highest_priority_policy.get("Name", "Unnamed Policy")
            reasoning = f"Audit log retention policy configured: {retention_duration} (Policy: {policy_name})"
            status = "pass"
            actual_value = {
                "audit_log_retention_policies_count": len(policies),
                "highest_priority_retention_duration": retention_duration,
                "highest_priority_policy_name": policy_name,
                "all_policies": policies,
            }

        evidence = _evaluation_evidence(
            pass_criteria="When policies are set up",
            fail_criteria="When no policies are set up",
            reasoning=reasoning,
            extra={
                "tenant_id": tenant.tenant_id,
                "policies_retrieved": policies,
                "source": "Get-UnifiedAuditLogRetentionPolicy (Purview PowerShell)",
            },
        )

        return _collector_result(
            parameter_key=parameter_key,
            status=status,
            severity="medium",
            actual_value=actual_value,
            expected_value="Audit log retention policy configured",
            finding=reasoning,
            evidence=evidence,
            raw_response={"unified_audit_log_retention_policies": policies},
            graph_calls=0,
            powershell_calls=1,
            scoring_weight=3.0,
        )

    except Exception as e:
        logger.warning(f"[AUDIT_LOG_RETENTION] Collector error: {e}")
        return _governance_unverifiable_fail(
            tenant,
            parameter_key=parameter_key,
            service_name="Microsoft Purview",
            portal_location="Purview Compliance Portal > Audit > Retention Policies",
            expected_value="Audit log retention policy configured",
            pass_criteria="When policies are set up",
            fail_criteria="When no policies are set up",
            severity="medium",
            scoring_weight=3.0,
        )


async def collect_dlp_rules_configured(tenant: ConnectedTenant) -> dict[str, Any]:
    endpoint = "https://graph.microsoft.com/beta/security/dataLossPrevention/policies"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _licensing_required_result(tenant, parameter_key="dlp_rules_configured", endpoint=endpoint, required_sku="Microsoft 365 E5 or Microsoft Purview DLP", required_service="Microsoft Purview Data Loss Prevention", required_role="Compliance Administrator or DLP Compliance Management", required_permissions=["SecurityActions.Read.All"], expected_value="DLP policies configured and applied", pass_criteria="If DLP rules is configured and applied correctly to exchange,sharepoint,teams etc", fail_criteria="If DLP rules is not configured and applied correctly to exchange,sharepoint,teams etc", severity="critical", scoring_weight=5.0, graph_response=response)
    policies = (response.get("response") or {}).get("value") or []
    status = "pass" if policies else "fail"
    reasoning = f"{len(policies)} DLP policie(s) returned by Microsoft Graph"
    evidence = _evaluation_evidence(pass_criteria="If DLP rules is configured and applied correctly to exchange,sharepoint,teams etc", fail_criteria="If DLP rules is not configured and applied correctly to exchange,sharepoint,teams etc", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "dlp_policies": policies})
    return _collector_result(parameter_key="dlp_rules_configured", status=status, severity="critical", actual_value={"dlp_policy_count": len(policies)}, expected_value="DLP policies configured and applied", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"dlpPolicies": response.get("response")}, graph_calls=1, scoring_weight=5.0)


async def collect_external_storage_providers_in_owa(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _exchange_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="external_storage_providers_in_owa", service_name="Exchange Online",
            graph_endpoint="beta/admin/exchange/settings",
            expected_value="External storage providers disabled in OWA",
            pass_criteria="When not enabled, users cannot connect third-party storage services to Outlook Web App",
            fail_criteria="When enabled, users can connect third-party storage services to Outlook Web App",
            severity="high", scoring_weight=4.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="external_storage_providers_in_owa", service_name="Exchange Online",
        portal_location="Exchange Admin Center > Outlook Web App policies (Set-OwaMailboxPolicy -AdditionalStorageProvidersAvailable $false)",
        graph_endpoint="beta/admin/exchange/settings",
        expected_value="External storage providers disabled in OWA",
        pass_criteria="When not enabled, users cannot connect third-party storage services to Outlook Web App",
        fail_criteria="When enabled, users can connect third-party storage services to Outlook Web App",
        severity="high", scoring_weight=4.0,
    )


async def collect_full_calendar_schedules_able_to_be_shared_externally(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _exchange_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="full_calendar_schedules_able_to_be_shared_externally", service_name="Exchange Online",
            graph_endpoint="beta/admin/exchange/settings",
            expected_value="External full calendar sharing disabled",
            pass_criteria="If False, calendar sharing is disabled across the organization",
            fail_criteria="If True, calendar sharing is enabled for the organization",
            severity="medium", scoring_weight=3.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="full_calendar_schedules_able_to_be_shared_externally", service_name="Exchange Online",
        portal_location="Exchange Admin Center > Organization > Sharing policies",
        graph_endpoint="beta/admin/exchange/settings",
        expected_value="External full calendar sharing disabled",
        pass_criteria="If False, calendar sharing is disabled across the organization",
        fail_criteria="If True, calendar sharing is enabled for the organization",
        severity="medium", scoring_weight=3.0,
    )


async def collect_customer_lockbox(tenant: ConnectedTenant) -> dict[str, Any]:
    if not await _exchange_service_available(tenant):
        return _service_unavailable_fail(
            tenant, parameter_key="customer_lockbox", service_name="Exchange Online",
            graph_endpoint="beta/admin/exchange/settings",
            expected_value="Customer Lockbox enabled",
            pass_criteria="Microsoft support staff cannot access your content without your explicit approval",
            fail_criteria="Microsoft support staff can access your content without your explicit approval",
            severity="medium", scoring_weight=3.0,
        )
    return _governance_unverifiable_fail(
        tenant, parameter_key="customer_lockbox", service_name="Exchange Online",
        portal_location="Microsoft 365 Admin Center > Settings > Security & privacy > Customer Lockbox",
        graph_endpoint="beta/admin/exchange/settings",
        expected_value="Customer Lockbox enabled",
        pass_criteria="Microsoft support staff cannot access your content without your explicit approval",
        fail_criteria="Microsoft support staff can access your content without your explicit approval",
        severity="medium", scoring_weight=3.0,
    )


async def _sharepoint_settings_or_status(
    tenant: ConnectedTenant,
    *,
    parameter_key: str,
    expected_value: str,
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
    command: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    endpoint = "https://graph.microsoft.com/beta/admin/sharepoint/settings"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        result = _licensing_required_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_sku="SharePoint Online",
            required_service="SharePoint tenant settings",
            required_role="SharePoint Administrator or Global Administrator",
            required_permissions=["SharePointTenantSettings.Read.All"],
            expected_value=expected_value,
            pass_criteria=pass_criteria,
            fail_criteria=fail_criteria,
            severity=severity,
            scoring_weight=scoring_weight,
            graph_response=response,
        )
        result["raw_value"]["required_powershell_command"] = command
        result["telemetry"]["source_script"] = command
        return None, result
    return response.get("response") or {}, None


async def collect_external_sharing_settings(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "external_sharing_settings"
    endpoint = "https://graph.microsoft.com/beta/admin/sharepoint/settings"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _licensing_required_result(tenant, parameter_key=parameter_key, endpoint=endpoint, required_sku="SharePoint Online", required_service="SharePoint tenant settings", required_role="SharePoint Administrator or Global Administrator", required_permissions=["SharePointTenantSettings.Read.All"], expected_value="New and existing guests or more restrictive", pass_criteria="When it is set to New and existing guests or more restrictive", fail_criteria="When it is set to Anyone(Least restrictive)", severity="high", scoring_weight=4.0, graph_response=response)
    settings = response.get("response") or {}
    sharing = str(settings.get("oneDriveSharingCapability") or settings.get("sharingCapability") or "")
    # OneDrive external sharing capability (manual criteria). Only "Disabled" and
    # "ExistingExternalUserSharingOnly" are acceptable. "ExternalUserSharingOnly"
    # ("new and existing guests") and "ExternalUserAndGuestSharing" ("Anyone" links)
    # both expose content to newly invited external identities and FAIL.
    ONEDRIVE_SHARING_MAP = {
        "disabled": ("pass", "External sharing is disabled"),
        "existingexternalusersharingonly": ("pass", "Set to existing external users only"),
        "externalusersharingonly": ("fail", "Set to new and existing guests"),
        "externaluserandguestsharing": ("fail", "Set to anyone links"),
    }
    status, reasoning = ONEDRIVE_SHARING_MAP.get(
        sharing.lower(),
        ("fail", f"Set to {sharing or 'unknown'} — could not confirm a restrictive level"),
    )
    evidence = _evaluation_evidence(pass_criteria="When it is set to New and existing guests or more restrictive", fail_criteria="When it is set to Anyone(Least restrictive)", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings})
    return _collector_result(parameter_key=parameter_key, status=status, severity="high", actual_value={"sharingCapability": settings.get("sharingCapability"), "oneDriveSharingCapability": settings.get("oneDriveSharingCapability")}, expected_value="New and existing guests or more restrictive", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=4.0)


async def collect_sharepoint_modern_authentication(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "sharepoint_modern_authentication"
    endpoint = "https://graph.microsoft.com/beta/admin/sharepoint/settings"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _licensing_required_result(tenant, parameter_key=parameter_key, endpoint=endpoint, required_sku="SharePoint Online", required_service="SharePoint tenant settings", required_role="SharePoint Administrator or Global Administrator", required_permissions=["SharePointTenantSettings.Read.All"], expected_value="Modern authentication enabled / legacy auth disabled", pass_criteria="When it is enabled", fail_criteria="When it is disabled", severity="medium", scoring_weight=3.0, graph_response=response)
    settings = response.get("response") or {}
    legacy_enabled = settings.get("isLegacyAuthProtocolsEnabled")
    # Modern authentication is enforced only when legacy auth protocols are disabled.
    if legacy_enabled is False:
        status = "pass"
        reasoning = "Apps using legacy authentication are disabled"
    else:
        status = "fail"
        reasoning = "Apps using legacy authentication are enabled"
    evidence = _evaluation_evidence(pass_criteria="When it is enabled", fail_criteria="When it is disabled", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings})
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"isLegacyAuthProtocolsEnabled": legacy_enabled}, expected_value="Modern authentication enabled / legacy auth disabled", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=3.0)


async def collect_sharing_settings_external_internal(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "sharing_settings_external_internal"
    endpoint = "https://graph.microsoft.com/beta/admin/sharepoint/settings"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _licensing_required_result(tenant, parameter_key=parameter_key, endpoint=endpoint, required_sku="SharePoint Online", required_service="SharePoint tenant settings", required_role="SharePoint Administrator or Global Administrator", required_permissions=["SharePointTenantSettings.Read.All"], expected_value="Restrictive sharing settings enabled", pass_criteria="When settings enabled", fail_criteria="When restrictive setting no set up", severity="critical", scoring_weight=5.0, graph_response=response)
    settings = response.get("response") or {}
    # SharePoint tenant SharingCapability (manual criteria). External User Sharing —
    # existing OR new external users — is acceptable; only anonymous/"Anyone" guest
    # sharing (ExternalUserAndGuestSharing) FAILs. This parameter evaluates
    # SharingCapability ONLY — not PreventExternalUsersFromResharing.
    sharing = str(settings.get("sharingCapability") or "")
    SHAREPOINT_SHARING_MAP = {
        "disabled": ("pass", "External sharing is disabled"),
        "existingexternalusersharingonly": ("pass", "Set to Existing External User Sharing only"),
        "externalusersharingonly": ("pass", "Set to External User Sharing only"),
        "externaluserandguestsharing": ("fail", "Set to Anyone / anonymous guest sharing"),
    }
    status, reasoning = SHAREPOINT_SHARING_MAP.get(
        sharing.lower(),
        ("fail", f"SharingCapability={sharing or 'unknown'} — could not confirm a restrictive level"),
    )
    evidence = _evaluation_evidence(pass_criteria="External User Sharing (existing or new external users) or more restrictive", fail_criteria="Anyone / anonymous guest sharing enabled", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings})
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"sharingCapability": sharing}, expected_value="External User Sharing only or more restrictive", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=5.0)


async def collect_sharepoint_and_onedrive_guest_access_expiry(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "sharepoint_and_onedrive_guest_access_expiry"
    command = "Get-SPOTenant | Select ExternalUserExpirationRequired,ExternalUserExpireInDays,RequireAnonymousLinksExpireInDays"
    settings, blocked = await _sharepoint_settings_or_status(
        tenant,
        parameter_key=parameter_key,
        expected_value="Guest access/link expiry configured",
        pass_criteria="SharingExpirationPeriod: The number of days the guest access link will be valid before it expires",
        fail_criteria="SharingExpirationPeriod not enabled",
        severity="critical",
        scoring_weight=5.0,
        command=command,
    )
    if blocked:
        return blocked
    assert settings is not None
    expiry_days = settings.get("requireAnonymousLinksExpireInDays") or settings.get("anonymousLinkExpirationInDays")
    external_required = settings.get("isExternalUserExpirationRequired") or settings.get("externalUserExpirationRequired")
    external_days = settings.get("externalUserExpireInDays")
    configured = bool(expiry_days or external_required or external_days)
    status = "pass" if configured else "fail"
    reasoning = f"Guest/link expiry settings returned: anonymous link days={expiry_days}; external expiration required={external_required}; external days={external_days}"
    evidence = _evaluation_evidence(
        pass_criteria="SharingExpirationPeriod: The number of days the guest access link will be valid before it expires",
        fail_criteria="SharingExpirationPeriod not enabled",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings, "required_powershell_command": command},
    )
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"requireAnonymousLinksExpireInDays": expiry_days, "externalUserExpirationRequired": external_required, "externalUserExpireInDays": external_days}, expected_value="Guest access/link expiry configured", finding=reasoning, graph_endpoint="https://graph.microsoft.com/beta/admin/sharepoint/settings", evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=5.0)


async def collect_days_to_retain_a_deleted_user_s_onedrive(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "days_to_retain_a_deleted_user_s_onedrive"
    endpoint = "https://graph.microsoft.com/beta/admin/sharepoint/settings"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        result = _licensing_required_result(tenant, parameter_key=parameter_key, endpoint=endpoint, required_sku="SharePoint Online", required_service="SharePoint tenant settings", required_role="SharePoint Administrator or Global Administrator", required_permissions=["SharePointTenantSettings.Read.All"], expected_value="Deleted OneDrive retained for at least 180 days", pass_criteria="Retention period is 180 days or more", fail_criteria="Retention period is below 180 days", severity="low", scoring_weight=2.0, graph_response=response)
        result["raw_value"]["required_powershell_command"] = "Get-SPOTenant | Select OrphanedPersonalSitesRetentionPeriod"
        return result
    settings = response.get("response") or {}
    # Graph exposes the deleted-user OneDrive retention as
    # deletedUserPersonalSiteRetentionPeriodInDays (PnP: OrphanedPersonalSitesRetentionPeriod).
    retention = settings.get("deletedUserPersonalSiteRetentionPeriodInDays")
    if retention is None:
        retention = settings.get("orphanedPersonalSitesRetentionPeriod") or settings.get("oneDriveRetentionPeriod")
    try:
        days = int(retention) if retention is not None else None
    except (TypeError, ValueError):
        days = None
    status = "pass" if (days is not None and days >= 180) else "fail"
    if days is None:
        reasoning = "Deleted user's OneDrive retention period could not be read"
    else:
        reasoning = f"Set for {days} days"
    evidence = _evaluation_evidence(pass_criteria="Retention period is 180 days or more", fail_criteria="Retention period is below 180 days", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings})
    return _collector_result(parameter_key=parameter_key, status=status, severity="low", actual_value={"deletedUserPersonalSiteRetentionPeriodInDays": days}, expected_value="Deleted OneDrive retained for at least 180 days", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=2.0)


async def collect_expiration_policy_for_anyone_links(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "expiration_policy_for_anyone_links"
    command = "Get-SPOTenant | Select RequireAnonymousLinksExpireInDays"
    settings, blocked = await _sharepoint_settings_or_status(
        tenant,
        parameter_key=parameter_key,
        expected_value="Anyone links have an expiration policy configured",
        pass_criteria="Anyone links expire within the approved duration",
        fail_criteria="Anyone links do not expire or exceed the approved duration",
        severity="high",
        scoring_weight=4.0,
        command=command,
    )
    if blocked:
        return blocked
    assert settings is not None
    days = settings.get("requireAnonymousLinksExpireInDays") or settings.get("anonymousLinkExpirationInDays")
    configured = days is not None and int(days or 0) > 0
    status = "pass" if configured else "fail"
    reasoning = f"Anyone link expiration days: {days if days is not None else 'not returned'}"
    evidence = _evaluation_evidence(pass_criteria="Anyone links expire within the approved duration", fail_criteria="Anyone links do not expire or exceed the approved duration", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings, "required_powershell_command": command})
    return _collector_result(parameter_key=parameter_key, status=status, severity="high", actual_value={"requireAnonymousLinksExpireInDays": days}, expected_value="Anyone links have an expiration policy configured", finding=reasoning, graph_endpoint="https://graph.microsoft.com/beta/admin/sharepoint/settings", evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=4.0)


async def collect_permission_setting_for_anyone_links(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "permission_setting_for_anyone_links"
    command = "Get-SPOTenant | Select DefaultSharingLinkType,FileAnonymousLinkType,FolderAnonymousLinkType"
    settings, blocked = await _sharepoint_settings_or_status(
        tenant,
        parameter_key=parameter_key,
        expected_value="Anyone links are disabled or restricted to view-only least privilege access",
        pass_criteria="Anyone links are disabled or restricted to view-only least privilege access",
        fail_criteria="Anyone links allow edit or overly permissive access",
        severity="critical",
        scoring_weight=5.0,
        command=command,
    )
    if blocked:
        return blocked
    assert settings is not None
    sharing = str(settings.get("sharingCapability") or "")
    default_link = str(settings.get("defaultLinkPermission") or settings.get("defaultSharingLinkType") or "")
    file_link = str(settings.get("fileAnonymousLinkType") or "")
    folder_link = str(settings.get("folderAnonymousLinkType") or "")
    PASS_VALUES = {"view", "none"}
    if not default_link:
        status = "fail"
        reasoning = "Anyone link permission level could not be verified — treating as unverified gap"
    elif default_link.lower() in PASS_VALUES:
        status = "pass"
        reasoning = f"Anyone link permission set to: {default_link}"
    else:
        status = "fail"
        reasoning = f"Anyone link permission set to: {default_link} — Edit access allows data exposure"
    evidence = _evaluation_evidence(pass_criteria="Anyone links are disabled or restricted to view-only least privilege access", fail_criteria="Anyone links allow edit or overly permissive access", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings, "required_powershell_command": command})
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"sharingCapability": sharing, "defaultSharingLinkType": default_link, "fileAnonymousLinkType": file_link, "folderAnonymousLinkType": folder_link}, expected_value="Anyone links are disabled or restricted to view-only least privilege access", finding=reasoning, graph_endpoint="https://graph.microsoft.com/beta/admin/sharepoint/settings", evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=5.0)


async def _sharepoint_advanced_management_licensed(
    tenant: ConnectedTenant,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Return whether the tenant is licensed for SharePoint Advanced Management (SAM).

    Inactive-site policies, site-ownership policies and Copilot/restricted-content
    discovery are SAM add-on features. Detection is by subscribed SKU part number so
    the check stays multi-tenant (no hardcoded tenant values).
    """
    sku_response = await _subscribed_skus(tenant)
    parts = [str(sku.get("skuPartNumber") or "") for sku in (sku_response.get("value") or [])]
    normalized = ["".join(ch for ch in part.upper() if ch.isalnum()) for part in parts]
    licensed = any("SHAREPOINTADVANCEDMANAGEMENT" in part for part in normalized)
    return licensed, parts, sku_response


def _sam_unavailable_result(
    *,
    parameter_key: str,
    tenant: ConnectedTenant,
    sku_parts: list[str],
    sku_response: dict[str, Any],
    pass_criteria: str,
    fail_criteria: str,
    severity: str,
    scoring_weight: float,
) -> dict[str, Any]:
    reasoning = "Part of SharePoint Advanced Management"
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=f"{reasoning} — the SharePoint Advanced Management add-on license is not present in this tenant, so this control cannot be enforced or verified.",
        extra={"tenant_id": tenant.tenant_id, "subscribed_sku_parts": sku_parts, "sam_licensed": False},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="fail",
        severity=severity,
        actual_value={"sam_licensed": False, "subscribed_sku_parts": sku_parts},
        expected_value="SharePoint Advanced Management licensed and policy configured",
        finding=reasoning,
        graph_endpoint="/subscribedSkus",
        evidence=evidence,
        raw_response={"subscribedSkus": sku_response},
        graph_calls=1,
        scoring_weight=scoring_weight,
    )


async def collect_inactive_site_policies(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "inactive_site_policies"
    _PASS = "Inactive site policies are configured via SharePoint Advanced Management"
    _FAIL = "Inactive site policies are not configured"
    # Inactive Site Policies is a SharePoint Advanced Management (SAM) feature.
    sam_licensed, sku_parts, sku_response = await _sharepoint_advanced_management_licensed(tenant)
    if not sam_licensed:
        return _sam_unavailable_result(parameter_key=parameter_key, tenant=tenant, sku_parts=sku_parts, sku_response=sku_response, pass_criteria=_PASS, fail_criteria=_FAIL, severity="medium", scoring_weight=3.0)
    endpoint = "/reports/getSharePointSiteUsageDetail(period='D180')"
    report = await _graph_get_text(tenant, endpoint)
    if not report.get("ok"):
        spo_msg = "Part of SharePoint Advanced Management"
        evidence = _evaluation_evidence(pass_criteria=_PASS, fail_criteria=_FAIL, reasoning=spo_msg, extra={"tenant_id": tenant.tenant_id, "endpoint": endpoint, "response": str(report.get("response", ""))[:200]})
        return _collector_result(parameter_key=parameter_key, status="fail", severity="medium", actual_value={"error": spo_msg}, expected_value="Inactive site policy is configured", finding=spo_msg, graph_endpoint=endpoint, evidence=evidence, raw_response={"error": spo_msg}, graph_calls=1, scoring_weight=3.0)
    rows = _csv_rows(report)
    inactive = [row for row in rows if not _has_activity(row)]
    ratio = _percent(len(inactive), len(rows))
    status = "pass" if ratio < 20 else "fail"
    reasoning = f"{len(inactive)} inactive SharePoint site(s) found out of {len(rows)} reported sites ({ratio}%)"
    evidence = _evaluation_evidence(pass_criteria=_PASS, fail_criteria=_FAIL, reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "site_usage_rows": rows[:50], "inactive_sites": inactive[:50], "required_powershell_command": "Get-SPOSite -Limit All | Select Url,LastContentModifiedDate,Owner"})
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"site_count": len(rows), "inactive_site_count": len(inactive), "inactive_site_percent": ratio}, expected_value="Inactive site policy is configured", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sharePointSiteUsageDetail": {"row_count": len(rows)}}, graph_calls=1, scoring_weight=3.0)


async def collect_site_ownership_policies(tenant: ConnectedTenant) -> dict[str, Any]:
    """Collect site ownership policies via M365 Groups (avoids SPO license requirement).

    Uses /groups?$filter=groupTypes/any(x:x eq 'Unified') to enumerate M365 groups
    (which back SharePoint team sites), then checks owner counts via /groups/{id}/owners.
    Falls back to SharePoint admin settings endpoint if groups endpoint also fails.
    """
    parameter_key = "site_ownership_policies"
    _PASS_CRITERIA = "All Microsoft 365 Groups (team sites) have at least one owner assigned."
    _FAIL_CRITERIA = "One or more Microsoft 365 Groups lack an assigned owner, creating ungoverned sites."

    client = await _graph_client(tenant)

    # Site Ownership Policies is a SharePoint Advanced Management (SAM) feature. If the
    # tenant is not licensed for SAM, the control cannot be enforced or verified.
    sam_licensed, sku_parts, sku_response = await _sharepoint_advanced_management_licensed(tenant)
    if not sam_licensed:
        return _sam_unavailable_result(parameter_key=parameter_key, tenant=tenant, sku_parts=sku_parts, sku_response=sku_response, pass_criteria=_PASS_CRITERIA, fail_criteria=_FAIL_CRITERIA, severity="medium", scoring_weight=3.0)

    # Use M365 Groups as proxy for SharePoint team sites — no SPO license required
    groups_resp = await _graph_get_json_or_error(
        tenant,
        "/groups?$filter=groupTypes/any(x:x eq 'Unified')&$select=id,displayName,mail&$top=100",
    )

    if not groups_resp.get("ok"):
        # Try SharePoint admin settings as a fallback signal
        settings_resp = await _graph_get_json_or_error(tenant, "https://graph.microsoft.com/beta/admin/sharepoint/settings")
        if settings_resp.get("ok"):
            settings = settings_resp.get("response") or {}
            # If we can read SharePoint settings, treat site governance as partially assessable
            allow_guests = settings.get("isSharingEnabledForAllDomains") or settings.get("sharingCapability")
            reasoning = (
                f"Microsoft 365 Groups endpoint was unavailable (SPO license may be absent). "
                f"SharePoint admin settings were readable: sharingCapability={allow_guests}. "
                "Manual review of site ownership is recommended."
            )
            evidence = _evaluation_evidence(
                pass_criteria=_PASS_CRITERIA,
                fail_criteria=_FAIL_CRITERIA,
                reasoning=reasoning,
                extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings},
            )
            return _collector_result(
                parameter_key=parameter_key,
                status="fail",
                severity="medium",
                actual_value={"site_count": 0, "groups_with_no_owner": 0, "note": "SPO license not present; manual review needed"},
                expected_value="All M365 Groups have at least one designated owner",
                finding=reasoning,
                graph_endpoint="https://graph.microsoft.com/beta/admin/sharepoint/settings",
                evidence=evidence,
                raw_response={"sharepoint_settings": settings},
                graph_calls=2,
                scoring_weight=3.0,
            )
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint="/groups?$filter=groupTypes/any(x:x eq 'Unified')",
            required_api="Microsoft Graph Groups API (Group.Read.All)",
            required_permissions=["Group.Read.All"],
            expected_value="All M365 Groups have at least one designated owner",
            pass_criteria=_PASS_CRITERIA,
            fail_criteria=_FAIL_CRITERIA,
            severity="medium",
            scoring_weight=3.0,
            response=groups_resp,
            command="Get-MgGroup -Filter \"groupTypes/any(x:x eq 'Unified')\" | Get-MgGroupOwner",
        )

    groups: list[dict[str, Any]] = (groups_resp.get("response") or {}).get("value") or []
    groups_without_owner: list[str] = []

    # Check owner count for each group (sample up to 50 to avoid throttling)
    for group in groups[:50]:
        gid = group.get("id")
        if not gid:
            continue
        owners_resp = await _graph_get_json_or_error(tenant, f"/groups/{gid}/owners?$select=id&$top=1")
        if owners_resp.get("ok"):
            owners = (owners_resp.get("response") or {}).get("value") or []
            if not owners:
                groups_without_owner.append(group.get("displayName") or gid)
        # If owner endpoint fails we skip that group (don't penalise on permission gap)

    total = len(groups)
    no_owner_count = len(groups_without_owner)
    ratio = _percent(no_owner_count, total) if total else 0
    status = "pass" if no_owner_count == 0 else "fail"
    reasoning = (
        f"{no_owner_count} of {total} Microsoft 365 Groups (team sites) have no assigned owner "
        f"({ratio}% ungoverned). "
        + (f"Groups without owner: {', '.join(groups_without_owner[:10])}." if groups_without_owner else "All sampled groups have at least one owner.")
    )
    evidence = _evaluation_evidence(
        pass_criteria=_PASS_CRITERIA,
        fail_criteria=_FAIL_CRITERIA,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "total_groups_enumerated": total,
            "groups_without_owner": groups_without_owner[:20],
            "ungoverned_percent": ratio,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="medium",
        actual_value={"site_count": total, "groups_with_no_owner": no_owner_count, "ungoverned_percent": ratio},
        expected_value="All M365 Groups have at least one designated owner",
        finding=reasoning,
        graph_endpoint="/groups?$filter=groupTypes/any(x:x eq 'Unified')",
        evidence=evidence,
        raw_response={"groups_sample": groups[:20]},
        graph_calls=1 + len(groups[:50]),
        scoring_weight=3.0,
    )


GRAPH_COLLECTORS = {
    "global_administrator_accounts": collect_global_administrator_accounts,
    "guest_users_count": collect_guest_users_count,
    "account_enabled": collect_account_enabled,
    "user_information": collect_user_information,
    "guest_invite_settings": collect_guest_invite_settings,
    "entra_tenant_creation_by_non_admin": collect_entra_tenant_creation_by_non_admin,
    "entra_third_party_app_integrations": collect_entra_third_party_app_integrations,
    "tenant_collaboration_invitations": collect_tenant_collaboration_invitations,
    "authentication_methods_enabled": collect_authentication_methods_enabled,
    "admin_consent_workflow": collect_admin_consent_workflow,
    "cap_policies_for_risky_sign_ins": collect_cap_policies_for_risky_sign_ins,
    "users_without_mfa": collect_users_without_mfa,
    "user_consent_for_applications": collect_user_consent_for_applications,
    "non_admin_users_can_register_applications": collect_non_admin_users_can_register_applications,
    "restricted_access_to_microsoft_entra_admin_centre": collect_restricted_access_to_microsoft_entra_admin_centre,
    "self_service_password_reset_authentication_method": collect_self_service_password_reset_authentication_method,
    "assigned_license": collect_assigned_license,
    "conditional_access_policies_exclusion": collect_conditional_access_policies_exclusion,
    "devices_without_compliance_policies": collect_devices_without_compliance_policies,
    "mailboxes_status_active_inactive": collect_mailboxes_status_active_inactive,
    "mailbox_storage_usage": collect_mailbox_storage_usage,
    "number_of_emails_read_received": collect_number_of_emails_read_received,
    "number_of_emails_sent": collect_number_of_emails_sent,
    "active_inactive_teams": collect_active_inactive_teams,
    "activer_inactive_teams_users": collect_activer_inactive_teams_users,
    "active_sites_count": collect_active_sites_count,
    "active_users_on_sharepoint": collect_active_users_on_sharepoint,
    "total_active_users_on_onedrive": collect_total_active_users_on_onedrive,
    "guest_access_enabled_disabled": collect_guest_access_enabled_disabled,
    "minimum_number_of_owners": collect_minimum_number_of_owners,
    "orphan_teams": collect_orphan_teams,
    "teams_anonymous_users": collect_teams_anonymous_users,
    "teams_external_unmanaged_user_communication": collect_teams_external_unmanaged_user_communication,
    "teams_file_storage_option": collect_teams_file_storage_option,
    "teams_with_external_users": collect_teams_with_external_users,
    "copilot_integration_enabled": collect_copilot_integration_enabled,
    "meeting_transcription_enabled": collect_meeting_transcription_enabled,
    "meeting_recording_retention_policies": collect_meeting_recording_retention_policies,
    "meeting_policies_configuration": collect_meeting_policies_configuration,
    "teams_channel_email_addresses": collect_teams_channel_email_addresses,
    "teams_lobby_bypass": collect_teams_lobby_bypass,
    "teams_meeting_chat": collect_teams_meeting_chat,
    "third_party_apps_allowed": collect_third_party_apps_allowed,
    "teams_with_external_guest_as_owner": collect_teams_with_external_guest_as_owner,
    "compliance_score_overview": collect_compliance_score_overview,
    "auto_expiration_policy_for_inactive_m365_groups": collect_auto_expiration_policy_for_inactive_m365_groups,
    "secure_score_percentage": collect_secure_score_percentage,
    "audit_logs_enabled": collect_audit_logs_enabled,
    "audit_log_retention_duration": collect_audit_log_retention_duration,
    "dlp_rules_configured": collect_dlp_rules_configured,
    "information_protection_labels_applied": collect_information_protection_labels_applied,
    "sensitivity_labels_configured_and_applied": collect_sensitivity_labels_configured_and_applied,
    "sensitivity_labels_applied_to_teams": collect_sensitivity_labels_applied_to_teams,
    "sensitivity_labels_are_applied": collect_sensitivity_labels_are_applied,
    "emergency_access_accounts": collect_emergency_access_accounts,
    "custom_banned_password_list": collect_custom_banned_password_list,
    "external_sharing_settings": collect_external_sharing_settings,
    "sharepoint_modern_authentication": collect_sharepoint_modern_authentication,
    "storage_quota_consumption": collect_storage_quota_consumption,
    "sharing_settings_external_internal": collect_sharing_settings_external_internal,
    "checking_sharing_permissions_for_each_sites_on_a_tenant": collect_checking_sharing_permissions_for_each_sites_on_a_tenant,
    "getting_all_sites_with_sensitivity_keywords_on_a_tenant": collect_getting_all_sites_with_sensitivity_keywords_on_a_tenant,
    "external_storage_providers_in_owa": collect_external_storage_providers_in_owa,
    "full_calendar_schedules_able_to_be_shared_externally": collect_full_calendar_schedules_able_to_be_shared_externally,
    "customer_lockbox": collect_customer_lockbox,
    "days_to_retain_a_deleted_user_s_onedrive": collect_days_to_retain_a_deleted_user_s_onedrive,
    "expiration_policy_for_anyone_links": collect_expiration_policy_for_anyone_links,
    "inactive_site_policies": collect_inactive_site_policies,
    "permission_setting_for_anyone_links": collect_permission_setting_for_anyone_links,
    "sharepoint_and_onedrive_guest_access_expiry": collect_sharepoint_and_onedrive_guest_access_expiry,
    "site_ownership_policies": collect_site_ownership_policies,
}
