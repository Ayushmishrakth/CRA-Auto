from __future__ import annotations

import csv
from io import StringIO
from datetime import datetime, timezone
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


async def _get_all(client: GraphClient, endpoint: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    values: list[dict[str, Any]] = []
    page = await client.get(endpoint, params=params)
    values.extend(page.get("value") or [])
    next_link = page.get("@odata.nextLink")
    while next_link:
        page = await client.get(next_link)
        values.extend(page.get("value") or [])
        next_link = page.get("@odata.nextLink")
    return {"value": values}


async def _graph_get_text(tenant: ConnectedTenant, endpoint: str) -> dict[str, Any]:
    token = await get_app_graph_token(tenant)
    url = endpoint if endpoint.startswith("https://") else f"https://graph.microsoft.com/v1.0/{endpoint.lstrip('/')}"
    _log("GRAPH_REQUEST", endpoint=endpoint)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "status_code": None,
                "error": {
                    "code": exc.__class__.__name__,
                    "message": str(exc),
                },
                "text": "",
            }
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
    policy = await _authorization_policy(tenant)
    permissions = policy.get("defaultUserRolePermissions") or {}
    allowed = permissions.get("allowedToCreateApps")
    status = "pass" if allowed is False else "fail"
    evidence = {"tenant_id": tenant.tenant_id, "authorization_policy": policy}
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value=allowed,
        expected_value="allowedToCreateApps=false",
        finding=f"Users allowed to register applications: {allowed}",
        graph_endpoint="/policies/authorizationPolicy?$select=defaultUserRolePermissions",
        evidence=evidence,
        raw_response={"authorizationPolicy": policy},
        graph_calls=1,
        scoring_weight=4.0,
    )


async def collect_tenant_collaboration_invitations(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "tenant_collaboration_invitations"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    client = await _graph_client(tenant)
    policy_endpoint = "/policies/crossTenantAccessPolicy"
    partners_endpoint = "/policies/crossTenantAccessPolicy/partners"
    policy = await client.get(policy_endpoint)
    partners = await _get_all(client, partners_endpoint)
    partner_values = partners.get("value") or []
    default = policy.get("default") or {}
    outbound = default.get("b2bCollaborationOutbound") or {}
    inbound = default.get("b2bCollaborationInbound") or {}
    outbound_targets = outbound.get("usersAndGroups", {}).get("accessType")
    inbound_targets = inbound.get("usersAndGroups", {}).get("accessType")
    unrestricted = not partner_values and outbound_targets in {None, "allowed"} and inbound_targets in {None, "allowed"}
    status = "fail" if unrestricted else "pass"
    reasoning = (
        "Tenant collaboration appears open to any domain"
        if status == "fail"
        else "Tenant collaboration has partner or default restrictions configured"
    )
    evidence = _evaluation_evidence(
        pass_criteria="Allow invitations only to the specified domain or deny invitations to specified domains",
        fail_criteria="Allow invitations to be sent to any domain",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "policy": policy, "partners": partner_values},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"partner_count": len(partner_values), "default": default},
        expected_value="Tenant collaboration invitations restricted by allowed or denied domain policy",
        finding=reasoning,
        graph_endpoint="/policies/crossTenantAccessPolicy + /policies/crossTenantAccessPolicy/partners",
        evidence=evidence,
        raw_response={"policy": policy, "partners": partners},
        graph_calls=2,
        scoring_weight=4.0,
    )


async def collect_authentication_methods_enabled(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "authentication_methods_enabled"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    raw_response = {"authenticationMethodsPolicy": await _authentication_methods_policy(tenant)}
    methods = raw_response["authenticationMethodsPolicy"].get("authenticationMethodConfigurations") or []
    enabled = [
        {"method": _auth_method_name(item), "state": item.get("state")}
        for item in methods
        if str(item.get("state") or "").lower() == "enabled"
    ]
    status = "pass" if len(enabled) > 2 else "fail"
    reasoning = f"{len(enabled)} authentication method(s) are enabled"
    evidence = _evaluation_evidence(
        pass_criteria="Authentication method has more than 2 authentication methods",
        fail_criteria="Authentication method has less than 2 authentication methods",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "methods": [{"method": _auth_method_name(item), "state": item.get("state")} for item in methods]},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value={"enabled_methods": len(enabled), "methods": enabled},
        expected_value="More than 2 authentication methods enabled",
        finding=reasoning,
        graph_endpoint="https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy",
        evidence=evidence,
        raw_response=raw_response,
        graph_calls=1,
        scoring_weight=5.0,
    )


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
        actual_value=policy,
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
    parameter_key = "users_without_mfa"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    client = await _graph_client(tenant)
    users_response = await _collect_users(tenant)
    users = users_response.get("value") or []
    method_rows = []
    raw_methods: dict[str, Any] = {}
    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue
        methods_response = await _user_authentication_methods(client, user_id)
        methods = methods_response.get("value") or []
        raw_methods[user_id] = methods_response
        method_types = [str(item.get("@odata.type") or item.get("id") or "") for item in methods]
        mfa_methods = [
            item for item in method_types
            if item and "passwordAuthenticationMethod" not in item
        ]
        method_rows.append({
            "id": user_id,
            "userPrincipalName": user.get("userPrincipalName"),
            "authMethodTypes": method_types,
            "mfaMethodTypes": mfa_methods,
        })
    without_mfa = [item for item in method_rows if not item["mfaMethodTypes"]]
    status = "pass" if not without_mfa else "fail"
    reasoning = f"{len(without_mfa)} user(s) do not have a non-password MFA authentication method registered"
    evidence = _evaluation_evidence(
        pass_criteria="MFA is enabled for all capable users",
        fail_criteria="MFA is not configured for some capable users",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "users_without_mfa": without_mfa, "users": method_rows},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="high",
        actual_value={"users_without_mfa": len(without_mfa), "total_users": len(method_rows)},
        expected_value="All MFA-capable users are registered for MFA",
        finding=reasoning,
        graph_endpoint="/users + /users/{id}/authentication/methods",
        evidence=evidence,
        raw_response={"users": users_response, "authenticationMethodsByUser": raw_methods},
        graph_calls=1 + len(method_rows),
        scoring_weight=4.0,
    )


async def collect_user_consent_for_applications(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "user_consent_for_applications"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    policy = await _authorization_policy(tenant)
    permissions = policy.get("defaultUserRolePermissions") or {}
    assigned = permissions.get("permissionGrantPoliciesAssigned") or []
    users_can_consent = bool(assigned)
    status = "fail" if users_can_consent else "pass"
    reasoning = "Users can consent for applications" if users_can_consent else "Users cannot consent for applications by default"
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
    reasoning = f"Non-admin users allowed to read other users/admin center data: {allowed}"
    evidence = _evaluation_evidence(
        pass_criteria="Non-Admin Users should not have access to Microsoft Entra Admin Centre",
        fail_criteria="Non-Admin Users have access to Microsoft Entra Admin Centre",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "authorization_policy": policy},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="info",
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
    status = "pass" if enabled else "fail"
    reasoning = f"{len(enabled)} SSPR/authentication method(s) are enabled"
    evidence = _evaluation_evidence(
        pass_criteria="Enabled to see how many methods registered",
        fail_criteria="No methods enabled",
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "enabled_methods": enabled,
            "user_registration_details": registration_response.get("value") or [],
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="critical",
        actual_value={"enabled_methods": len(enabled), "methods": enabled},
        expected_value="At least one SSPR/authentication method enabled",
        finding=reasoning,
        graph_endpoint="https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy + /reports/authenticationMethods/userRegistrationDetails",
        evidence=evidence,
        raw_response={"authenticationMethodsPolicy": methods_response, "userRegistrationDetails": registration_response},
        graph_calls=2,
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
    parameter_key = "devices_without_compliance_policies"
    _log("COLLECTOR_STARTED", parameter_key=parameter_key, tenant_id=tenant.tenant_id)
    client = await _graph_client(tenant)
    endpoint = "/deviceManagement/managedDevices"
    try:
        response = await _get_all(client, endpoint)
    except httpx.HTTPStatusError as exc:
        try:
            error_payload: dict[str, Any] = exc.response.json()
        except ValueError:
            error_payload = {"error": {"message": exc.response.text}}
        graph_error = error_payload.get("error") or error_payload
        reasoning = graph_error.get("message") or "Managed devices data is not available for this tenant"
        evidence = _evaluation_evidence(
            pass_criteria="Compliance policy is configured",
            fail_criteria="Compliance policy is not configured",
            reasoning=reasoning,
            extra={
                "tenant_id": tenant.tenant_id,
                "graph_error": graph_error,
                "status_code": exc.response.status_code,
            },
        )
        return _collector_result(
            parameter_key=parameter_key,
            status="fail",
            severity="info",
            actual_value={"managed_devices_available": False, "error": graph_error},
            expected_value="Managed device compliance data available and compliant",
            finding=reasoning,
            graph_endpoint=endpoint,
            evidence=evidence,
            raw_response={
                "managedDevices": {
                    "error": graph_error,
                    "status_code": exc.response.status_code,
                }
            },
            graph_calls=1,
            scoring_weight=1.0,
        )
    devices = response.get("value") or []
    non_compliant = [
        {
            "id": item.get("id"),
            "deviceName": item.get("deviceName"),
            "userPrincipalName": item.get("userPrincipalName"),
            "complianceState": item.get("complianceState"),
            "managementAgent": item.get("managementAgent"),
            "operatingSystem": item.get("operatingSystem"),
        }
        for item in devices
        if str(item.get("complianceState") or "").lower() not in {"compliant"}
    ]
    status = "pass" if not non_compliant else "fail"
    reasoning = f"{len(non_compliant)} device(s) are non-compliant or missing compliance state"
    evidence = _evaluation_evidence(
        pass_criteria="Compliance policy is configured",
        fail_criteria="Compliance policy is not configured",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "non_compliant_devices": non_compliant, "total_devices": len(devices)},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="info",
        actual_value={"non_compliant_devices": len(non_compliant), "total_devices": len(devices)},
        expected_value="No non-compliant or unmanaged devices",
        finding=reasoning,
        graph_endpoint="/deviceManagement/managedDevices",
        evidence=evidence,
        raw_response={"managedDevices": response},
        graph_calls=1,
        scoring_weight=1.0,
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
    endpoint = "/reports/getEmailActivityUserDetail(period='D30')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value=">85% active mailboxes",
            pass_criteria="When the number active mailboxes are more than 85%",
            fail_criteria="When the number active mailboxes are less than 85%",
            graph_endpoint=endpoint,
            severity="critical",
            scoring_weight=5.0,
        )
    mailboxes = [row for row in rows if str(row.get("Is Deleted") or "").lower() != "true"]
    active = [row for row in mailboxes if _has_activity(row)]
    inactive = [row for row in mailboxes if row not in active]
    ratio = _percent(len(active), len(mailboxes))
    status = "pass" if ratio > 85 else "fail"
    reasoning = f"{len(active)} active mailbox(es), {len(inactive)} inactive mailbox(es), active ratio {ratio}%"
    evidence = _evaluation_evidence(
        pass_criteria="When the number active mailboxes are more than 85%",
        fail_criteria="When the number active mailboxes are less than 85%",
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
    mailboxes = []
    over_threshold = []
    for row in rows:
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
        if ratio > 75:
            over_threshold.append(item)
    max_ratio = max([item["storage_usage_ratio"] for item in mailboxes], default=0.0)
    status = "pass" if not over_threshold else "fail"
    reasoning = f"{len(over_threshold)} mailbox(es) exceed 75% storage utilization; maximum utilization {max_ratio}%"
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
    endpoint = "/reports/getEmailActivityUserDetail(period='D30')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value=">75% users read more than 70% of received email",
            pass_criteria="More than 75% of users have read more than 70% of their emails.",
            fail_criteria="Less than 75% of users have read more than 70% of their emails.",
            graph_endpoint=endpoint,
            severity="info",
            scoring_weight=1.0,
        )
    metrics = []
    engaged = []
    for row in rows:
        received = _int_value(row, "Receive Count")
        read = _int_value(row, "Read Count")
        read_ratio = _percent(read, received)
        item = {"userPrincipalName": row.get("User Principal Name"), "received": received, "read": read, "read_ratio": read_ratio}
        metrics.append(item)
        if received > 0 and read_ratio > 70:
            engaged.append(item)
    engagement_ratio = _percent(len(engaged), len(metrics))
    status = "pass" if engagement_ratio > 75 else "fail"
    reasoning = f"{engagement_ratio}% of users read more than 70% of received emails"
    evidence = _evaluation_evidence(
        pass_criteria="More than 75% of users have read more than 70% of their emails.",
        fail_criteria="Less than 75% of users have read more than 70% of their emails.",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "read_ratio": engagement_ratio, "engagement_metrics": metrics},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="info",
        actual_value={"read_ratio": engagement_ratio, "engaged_users": len(engaged), "total_users": len(metrics)},
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
    endpoint = "/reports/getEmailActivityUserDetail(period='D30')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(
            tenant=tenant,
            parameter_key=parameter_key,
            report=report,
            expected_value=">30 average sent emails per user",
            pass_criteria="When the number of emails sent by the users are more than 30",
            fail_criteria="When the number of emails sent by the users are less than 30",
            graph_endpoint=endpoint,
            severity="info",
            scoring_weight=1.0,
        )
    sent_counts = [{"userPrincipalName": row.get("User Principal Name"), "send_count": _int_value(row, "Send Count")} for row in rows]
    average_sent = round(sum(item["send_count"] for item in sent_counts) / len(sent_counts), 2) if sent_counts else 0.0
    status = "pass" if average_sent > 30 else "fail"
    reasoning = f"Average sent email count per user is {average_sent}"
    evidence = _evaluation_evidence(
        pass_criteria="When the number of emails sent by the users are more than 30",
        fail_criteria="When the number of emails sent by the users are less than 30",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "average_sent_per_user": average_sent, "users": sent_counts},
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="info",
        actual_value={"average_sent_per_user": average_sent, "total_users": len(sent_counts)},
        expected_value=">30 average sent emails per user",
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
    active = [row for row in teams if _has_activity(row)]
    inactive = [row for row in teams if row not in active]
    status = "pass" if not inactive else "fail"
    reasoning = f"{len(active)} active team(s), {len(inactive)} inactive team(s)"
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
    active = [row for row in users if _has_activity(row)]
    inactive = [row for row in users if row not in active]
    inactive_ratio = _percent(len(inactive), len(users))
    status = "pass" if inactive_ratio < 15 else "fail"
    reasoning = f"{len(active)} active Teams user(s), {len(inactive)} inactive Teams user(s), inactive ratio {inactive_ratio}%"
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
    endpoint = "/reports/getSharePointSiteUsageDetail(period='D30')"
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
    sites = [row for row in rows if str(row.get("Is Deleted") or "").lower() != "true"]
    active = [row for row in sites if _has_activity(row)]
    ratio = _percent(len(active), len(sites))
    status = "pass" if ratio > 85 else "fail"
    reasoning = f"{len(active)} active SharePoint site(s) out of {len(sites)} ({ratio}%)"
    evidence = _evaluation_evidence(
        pass_criteria="When the number active sites on SharePoint are more than 85%",
        fail_criteria="When the number active sites on SharePoint are less than 85%",
        reasoning=reasoning,
        extra={"tenant_id": tenant.tenant_id, "active_sites": active, "all_sites": sites, "active_ratio": ratio},
    )
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"active_site_count": len(active), "total_sites": len(sites), "active_ratio": ratio}, expected_value=">85% active SharePoint sites", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"csv_rows": rows}, graph_calls=1, scoring_weight=3.0)


async def collect_active_users_on_sharepoint(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "active_users_on_sharepoint"
    endpoint = "/reports/getSharePointActivityUserDetail(period='D30')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(tenant=tenant, parameter_key=parameter_key, report=report, expected_value=">85% active SharePoint users", pass_criteria="When the number active users on SharePoint are more than 85%", fail_criteria="When the number active users on SharePoint are less than 85%", graph_endpoint=endpoint, severity="medium", scoring_weight=3.0)
    users = [row for row in rows if str(row.get("Is Deleted") or "").lower() != "true"]
    active = [row for row in users if _has_activity(row)]
    ratio = _percent(len(active), len(users))
    status = "pass" if ratio > 85 else "fail"
    reasoning = f"{len(active)} active SharePoint user(s) out of {len(users)} ({ratio}%)"
    evidence = _evaluation_evidence(pass_criteria="When the number active users on SharePoint are more than 85%", fail_criteria="When the number active users on SharePoint are less than 85%", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "active_users": active, "all_users": users, "active_ratio": ratio})
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"active_users": len(active), "total_users": len(users), "active_ratio": ratio}, expected_value=">85% active SharePoint users", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"csv_rows": rows}, graph_calls=1, scoring_weight=3.0)


async def collect_total_active_users_on_onedrive(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "total_active_users_on_onedrive"
    endpoint = "/reports/getOneDriveActivityUserDetail(period='D30')"
    rows, report = await _m365_report_rows(tenant, endpoint)
    if not report.get("ok"):
        return _report_error_result(tenant=tenant, parameter_key=parameter_key, report=report, expected_value=">80% active OneDrive users", pass_criteria="When the total active user on OneDrive are more than than 80%", fail_criteria="When the total active user on OneDrive are more than than 80%", graph_endpoint=endpoint, severity="info", scoring_weight=1.0)
    users = [row for row in rows if str(row.get("Is Deleted") or "").lower() != "true"]
    active = [row for row in users if _has_activity(row)]
    ratio = _percent(len(active), len(users))
    status = "pass" if ratio > 80 else "fail"
    reasoning = f"{len(active)} active OneDrive user(s) out of {len(users)} ({ratio}%)"
    evidence = _evaluation_evidence(pass_criteria="When the total active user on OneDrive are more than than 80%", fail_criteria="When the total active user on OneDrive are more than than 80%", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "active_users": active, "all_users": users, "active_ratio": ratio})
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
    for team in teams_response.get("value") or []:
        team_id = team.get("id")
        owners_response = await _get_all(client, f"/groups/{team_id}/owners", params={"$select": "id,displayName,userPrincipalName,mail,userType"})
        members_response = await _get_all(client, f"/groups/{team_id}/members", params={"$select": "id,displayName,userPrincipalName,userType"})
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
    return {"teams": teams, "raw_response": raw, "graph_calls": graph_calls}


async def collect_minimum_number_of_owners(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "minimum_number_of_owners"
    data = await _teams_with_owners_and_members(tenant)
    teams = data["teams"]
    under_owned = [team for team in teams if team["owner_count"] < 2]
    status = "pass" if not under_owned else "fail"
    reasoning = f"{len(under_owned)} team(s) have fewer than 2 owners"
    evidence = _evaluation_evidence(pass_criteria="When all teams have more than 1 Owner", fail_criteria="When teams have less than 2 Owner", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "teams": teams, "under_owned_teams": under_owned})
    return _collector_result(parameter_key=parameter_key, status=status, severity="high", actual_value={"teams_with_less_than_2_owners": len(under_owned), "total_teams": len(teams)}, expected_value="All teams have at least 2 owners", finding=reasoning, graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners", evidence=evidence, raw_response=data["raw_response"], graph_calls=data["graph_calls"], scoring_weight=4.0)


async def collect_orphan_teams(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "orphan_teams"
    data = await _teams_with_owners_and_members(tenant)
    teams = data["teams"]
    orphaned = [team for team in teams if team["owner_count"] == 0]
    status = "pass" if not orphaned else "fail"
    reasoning = f"{len(orphaned)} orphan team(s) found"
    evidence = _evaluation_evidence(pass_criteria="When there are no orphan teams", fail_criteria="When orphan teams are present", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "orphan_teams": orphaned, "teams": teams})
    return _collector_result(parameter_key=parameter_key, status=status, severity="high", actual_value={"orphan_team_count": len(orphaned), "total_teams": len(teams)}, expected_value="No orphan teams", finding=reasoning, graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/owners", evidence=evidence, raw_response=data["raw_response"], graph_calls=data["graph_calls"], scoring_weight=4.0)


async def collect_teams_with_external_users(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "teams_with_external_users"
    data = await _teams_with_owners_and_members(tenant)
    teams = data["teams"]
    external = [team for team in teams if team["guest_count"] > 0]
    ratio = _percent(len(external), len(teams))
    status = "pass" if ratio < 20 else "fail"
    reasoning = f"{len(external)} team(s) have external users ({ratio}% of teams)"
    evidence = _evaluation_evidence(pass_criteria="When it is less than 20%", fail_criteria="When it is more than to 20%", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "teams_with_external_users": external, "all_teams": teams, "external_team_ratio": ratio})
    return _collector_result(parameter_key=parameter_key, status=status, severity="high", actual_value={"teams_with_external_users": len(external), "total_teams": len(teams), "external_team_ratio": ratio}, expected_value="<20% Teams with external users", finding=reasoning, graph_endpoint="/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') + /groups/{id}/members", evidence=evidence, raw_response=data["raw_response"], graph_calls=data["graph_calls"], scoring_weight=4.0)


async def collect_teams_with_external_guest_as_owner(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "teams_with_external_guest_as_owner"
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
    reasoning = f"{len(guest_owned)} team(s) have external guest owners out of {len(teams)} Teams"
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
    return await _teams_policy_limitation_result(tenant, parameter_key="guest_access_enabled_disabled", expected_value="Guest access disabled", pass_criteria="When it is disabled", fail_criteria="When it is enabled", severity="medium", scoring_weight=3.0)


async def collect_teams_anonymous_users(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="teams_anonymous_users", expected_value="Anonymous users disabled", pass_criteria="When it is disabled", fail_criteria="When it is enabled", severity="info", scoring_weight=1.0)


async def collect_teams_external_unmanaged_user_communication(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="teams_external_unmanaged_user_communication", expected_value="External unmanaged communication disabled", pass_criteria="When it is disabled", fail_criteria="When it is enabled", severity="info", scoring_weight=1.0)


async def collect_teams_file_storage_option(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="teams_file_storage_option", expected_value="Files stored within Microsoft suite", pass_criteria="When the files are stored within the Microsoft suit", fail_criteria="When the files are stored outside the Microsoft suit", severity="medium", scoring_weight=3.0)


async def collect_copilot_integration_enabled(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="copilot_integration_enabled", expected_value="Copilot app integration enabled", pass_criteria="When it is enabled", fail_criteria="When it is disabled", severity="critical", scoring_weight=5.0)


async def collect_meeting_transcription_enabled(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="meeting_transcription_enabled", expected_value="Meeting transcription enabled", pass_criteria="When it is enabled", fail_criteria="When it is disabled", severity="high", scoring_weight=4.0)


async def collect_meeting_recording_retention_policies(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="meeting_recording_retention_policies", expected_value="Meeting recording retention enabled", pass_criteria="When it is enabled", fail_criteria="When it is disabled", severity="medium", scoring_weight=3.0)


async def collect_meeting_policies_configuration(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="meeting_policies_configuration", expected_value="Recommended Teams meeting policies configured", pass_criteria="When recommended settings are setup", fail_criteria="When recommended settings aren't setup", severity="high", scoring_weight=4.0)


async def collect_teams_channel_email_addresses(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="teams_channel_email_addresses", expected_value="Restricted sender list configured for channel email", pass_criteria="This will restrict Teams channels to allow accepting channel emails only from these Restricted Domains", fail_criteria="This will not restrict Teams channels to allow accepting channel emails only from these Restricted Domains", severity="low", scoring_weight=2.0)


async def collect_teams_lobby_bypass(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="teams_lobby_bypass", expected_value="Lobby bypass set to Never", pass_criteria="Specifies whether participants can bypass the lobby when joining the meeting - Never", fail_criteria="Specifies whether participants can bypass the lobby when joining the meeting - Anyone", severity="medium", scoring_weight=3.0)


async def collect_teams_meeting_chat(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="teams_meeting_chat", expected_value="Meeting chat enabled", pass_criteria="Enabled: Participants are allowed to use chat during and after the meeting.", fail_criteria="Disabled: Meeting chat is disabled", severity="medium", scoring_weight=3.0)


async def collect_third_party_apps_allowed(tenant: ConnectedTenant) -> dict[str, Any]:
    return await _teams_policy_limitation_result(tenant, parameter_key="third_party_apps_allowed", expected_value="Third-party/custom apps disabled", pass_criteria="Disabled- custom apps are unavailable in the organization's app", fail_criteria="Enabled- custom apps are available in the organization's app", severity="high", scoring_weight=4.0)


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
    reasoning = f"{required_service} evidence requires {required_sku}, {required_role}, and Graph permission(s): {', '.join(required_permissions)}."
    evidence = _evaluation_evidence(
        pass_criteria=pass_criteria,
        fail_criteria=fail_criteria,
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "graph_endpoint": endpoint,
            "collection_status": "LICENSING_REQUIRED",
            "required_sku": required_sku,
            "required_service": required_service,
            "required_role": required_role,
            "required_permissions": required_permissions,
            "graph_response": graph_response,
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status="licensing_required",
        severity=severity,
        actual_value={
            "collection_status": "LICENSING_REQUIRED",
            "required_sku": required_sku,
            "required_service": required_service,
            "required_role": required_role,
            "required_permissions": required_permissions,
        },
        expected_value=expected_value,
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"graph_response": graph_response or {}, "licensing_required": True},
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
    status = "licensing_required" if any(token in lowered for token in ["license", "subscription", "premium", "not available"]) else "collection_error"
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
            expected_value="Secure score percentage >70%",
            pass_criteria="When it is more than 70%",
            fail_criteria="When it is less than 70%",
            severity="critical",
            scoring_weight=5.0,
        )
    values = response.get("value") or []
    latest = values[0] if values else {}
    current = float(latest.get("currentScore") or 0)
    maximum = float(latest.get("maxScore") or 0)
    percentage = round(current / maximum * 100, 2) if maximum else 0.0
    status = "pass" if percentage > 70 else "fail"
    reasoning = f"Secure score is {percentage}% ({current}/{maximum})"
    evidence = _evaluation_evidence(
        pass_criteria="When it is more than 70%",
        fail_criteria="When it is less than 70%",
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
    roles = await client.get("/directoryRoles", params={"$filter": "displayName eq 'Global Administrator'", "$select": "id,displayName"})
    role = (roles.get("value") or [None])[0]
    members_response = {"value": []}
    if role:
        members_response = await client.get(f"/directoryRoles/{role['id']}/members", params={"$select": "id,displayName,userPrincipalName,mail"})
    members = members_response.get("value") or []
    emergency_markers = ("break", "glass", "emergency", "backup", "elevated")
    emergency = [
        item for item in members
        if any(marker in str(item.get("displayName") or item.get("userPrincipalName") or "").lower() for marker in emergency_markers)
    ]
    status = "pass" if emergency else "fail"
    reasoning = f"{len(emergency)} emergency access account(s) identified among {len(members)} Global Administrator member(s)"
    evidence = _evaluation_evidence(pass_criteria="When it is Present", fail_criteria="When not present", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "global_admin_members": members, "emergency_access_accounts": emergency, "matching_markers": emergency_markers})
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"emergency_access_accounts": len(emergency), "global_admin_members": len(members)}, expected_value="At least one identifiable emergency access account", finding=reasoning, graph_endpoint="/directoryRoles + /directoryRoles/{id}/members", evidence=evidence, raw_response={"directoryRoles": roles, "members": members_response}, graph_calls=2 if role else 1, scoring_weight=5.0)


async def collect_custom_banned_password_list(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "custom_banned_password_list"
    endpoints = [
        "https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/password",
        "https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy",
    ]
    responses: list[dict[str, Any]] = []
    for endpoint in endpoints:
        response = await _graph_get_json_or_error(tenant, endpoint)
        responses.append({"endpoint": endpoint, **response})
        if not response.get("ok"):
            continue
        policy = response.get("response") or {}
        parsed = _parse_custom_banned_password_policy(policy)
        if not parsed["configuration_exposed"]:
            continue
        enabled = parsed["password_protection_enabled"]
        custom_word_count = parsed["custom_word_count"]
        custom_words = parsed["custom_words"]
        status = "pass" if enabled and custom_word_count > 0 else "fail"
        reasoning = (
            f"Password protection enabled: {enabled}; enforcement mode: {parsed['enforcement_mode']}; "
            f"custom banned password terms exposed: {custom_word_count}."
        )
        actual_value = {
            "enabled": enabled,
            "password_protection_enabled": enabled,
            "enforcement_mode": parsed["enforcement_mode"],
            "custom_word_count": custom_word_count,
            "custom_banned_password_count": custom_word_count,
            "custom_words_present": custom_word_count > 0,
            "tenant_configuration_status": parsed["tenant_configuration_status"],
        }
        evidence_payload = {
            "password_protection_enabled": enabled,
            "enforcement_mode": parsed["enforcement_mode"],
            "custom_banned_password_count": custom_word_count,
            "custom_words_present": custom_word_count > 0,
            "custom_word_count": custom_word_count,
            "tenant_configuration_status": parsed["tenant_configuration_status"],
        }
        if custom_words:
            evidence_payload["custom_banned_password_terms"] = custom_words
        evidence = _evaluation_evidence(
            pass_criteria="Custom banned password list is configured and contains one or more custom banned terms.",
            fail_criteria="Custom banned password list is not configured or contains no custom banned terms.",
            reasoning=reasoning,
            extra={
                "tenant_id": tenant.tenant_id,
                "graph_endpoint": endpoint,
                "evidence_source": "Microsoft Graph authentication methods policy",
                **evidence_payload,
            },
        )
        evidence["remediation"] = (
            "Configure Microsoft Entra Password Protection custom banned password list and enforce password validation across all users."
        )
        return _collector_result(
            parameter_key=parameter_key,
            status=status,
            severity="critical",
            actual_value=actual_value,
            expected_value="Custom banned password list configured",
            finding=reasoning,
            graph_endpoint=endpoint,
            evidence=evidence,
            raw_response={
                "password_protection_policy": policy,
                "endpoint_attempts": responses,
                "actual_values_only": True,
            },
            graph_calls=len(responses),
            scoring_weight=5.0,
        )

    terminal = _classify_custom_banned_password_failure(responses)
    endpoint = terminal["endpoint"]
    if terminal["status"] == "licensing_required":
        return _licensing_required_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_sku="Microsoft Entra ID P1 or P2",
            required_service="Entra ID Password Protection",
            required_role="Authentication Policy Administrator or Global Administrator",
            required_permissions=["Policy.Read.All"],
            expected_value="Custom banned password list configured",
            pass_criteria="Custom banned password list is configured and contains one or more custom banned terms.",
            fail_criteria="Custom banned password list is not configured or contains no custom banned terms.",
            severity="critical",
            scoring_weight=5.0,
            graph_response={"endpoint_attempts": responses, "reason": terminal["reason"]},
        )

    if terminal["status"] == "manual_validation_required":
        evidence = _evaluation_evidence(
            pass_criteria="Custom banned password list is configured and contains one or more custom banned terms.",
            fail_criteria="Custom banned password list is not configured or contains no custom banned terms.",
            reasoning=terminal["reason"],
            extra={
                "tenant_id": tenant.tenant_id,
                "collection_status": "MANUAL_VALIDATION_REQUIRED",
                "graph_endpoint_attempts": responses,
                "portal_location": "Entra admin center > Protection > Authentication methods > Password protection",
                "validation_procedure": "Review Password protection settings and confirm the custom banned password list contains at least one custom term.",
                "expected_evidence": "Password Protection Enabled, Enforcement Mode, and Custom Banned Password Count.",
            },
        )
        return _collector_result(
            parameter_key=parameter_key,
            status="manual_validation_required",
            severity="critical",
            actual_value={
                "collection_status": "MANUAL_VALIDATION_REQUIRED",
                "reason": terminal["reason"],
                "enabled": None,
                "custom_word_count": None,
            },
            expected_value="Custom banned password list configured",
            finding=terminal["reason"],
            graph_endpoint=", ".join(endpoints),
            evidence=evidence,
            raw_response={"endpoint_attempts": responses, "manual_validation_required": True},
            graph_calls=len(responses),
            scoring_weight=5.0,
        )

    return _collection_error_result(
        tenant,
        parameter_key=parameter_key,
        endpoint=endpoint,
        required_api="Microsoft Graph authentication methods policy",
        required_permissions=["Policy.Read.All"],
        expected_value="Custom banned password list configured",
        pass_criteria="Custom banned password list is configured and contains one or more custom banned terms.",
        fail_criteria="Custom banned password list is not configured or contains no custom banned terms.",
        severity="critical",
        scoring_weight=5.0,
        response={"endpoint_attempts": responses, "reason": terminal["reason"]},
        reason=terminal["reason"],
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
        return {"status": "licensing_required", "endpoint": endpoint, "reason": _error_message(responses[-1])}
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
    endpoint = "https://graph.microsoft.com/beta/security/informationProtection/sensitivityLabels"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _licensing_required_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_sku="Microsoft 365 E5 or Microsoft Purview Information Protection",
            required_service="Microsoft Purview Information Protection",
            required_role="Compliance Administrator or Information Protection Administrator",
            required_permissions=["InformationProtectionPolicy.Read.All"],
            expected_value="Sensitivity labels configured and applied",
            pass_criteria="If labels is configured and applied",
            fail_criteria="If labels is not configured and applied",
            severity=severity,
            scoring_weight=scoring_weight,
            graph_response=response,
        )
    labels = (response.get("response") or {}).get("value") or []
    status = "pass" if labels else "fail"
    reasoning = f"{len(labels)} sensitivity label(s) returned by Microsoft Graph"
    evidence = _evaluation_evidence(pass_criteria="If labels is configured and applied", fail_criteria="If labels is not configured and applied", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "labels": labels})
    return _collector_result(parameter_key=parameter_key, status=status, severity=severity, actual_value={"sensitivity_label_count": len(labels)}, expected_value="Sensitivity labels configured and applied", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sensitivityLabels": response.get("response")}, graph_calls=1, scoring_weight=scoring_weight)


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
    status = "pass" if not over else "fail"
    reasoning = f"{len(over)} SharePoint site(s) are at or above 90% storage quota; maximum {max_ratio}%"
    evidence = _evaluation_evidence(pass_criteria="When it is less than 90%", fail_criteria="When it is more than or equal to 90%", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sites": sites, "over_threshold": over, "storage_quota_consumption": max_ratio})
    return _collector_result(parameter_key=parameter_key, status=status, severity="info", actual_value={"sites_over_90_percent": len(over), "site_count": len(sites), "max_storage_quota_ratio": max_ratio}, expected_value="<90% SharePoint storage quota consumption", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"csv_rows": rows}, graph_calls=1, scoring_weight=1.0)


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
    return _collector_result(parameter_key=parameter_key, status=status, severity="info", actual_value={"sensitivity_keyword_site_count": len(matched), "site_count": len(sites)}, expected_value="Sites with sensitivity keywords identified when present", finding=reasoning, graph_endpoint="/sites?search=*", evidence=evidence, raw_response={"sites": response}, graph_calls=1, scoring_weight=1.0)


async def collect_compliance_score_overview(tenant: ConnectedTenant) -> dict[str, Any]:
    return _manual_validation_required_result(
        tenant,
        parameter_key="compliance_score_overview",
        portal_location="Microsoft Purview portal > Compliance Manager",
        validation_procedure="Open Compliance Manager, export or capture the current compliance score overview, and attach the tenant score evidence to the assessment package.",
        expected_evidence="Compliance Manager score overview export or screenshot showing current score and assessment date.",
        expected_value="Compliance score >=80%",
        pass_criteria="When it is more than or equal to 80%",
        fail_criteria="When it is less than 80%",
        severity="critical",
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
    endpoint = "/auditLogs/directoryAudits"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_api="Microsoft Graph audit logs plus Purview retention policy PowerShell",
            required_permissions=["AuditLog.Read.All", "Directory.Read.All"],
            expected_value="Audit retention policies configured",
            pass_criteria="When policies are set up",
            fail_criteria="When no policies are set up",
            severity="medium",
            scoring_weight=3.0,
            response=response,
            command="Connect-IPPSSession; Get-RetentionCompliancePolicy; Get-RetentionComplianceRule",
        )
    rows = (response.get("response") or {}).get("value") or []
    status = "pass" if rows else "fail"
    reasoning = f"Audit log endpoint returned {len(rows)} sample record(s); exact retention duration requires Purview policy PowerShell."
    evidence = _evaluation_evidence(
        pass_criteria="When policies are set up",
        fail_criteria="When no policies are set up",
        reasoning=reasoning,
        extra={
            "tenant_id": tenant.tenant_id,
            "audit_records": rows,
            "required_powershell_command": "Connect-IPPSSession; Get-RetentionCompliancePolicy; Get-RetentionComplianceRule",
            "automation_scope": "Partial: verifies audit log availability through Graph; exact retention policy requires Purview PowerShell.",
        },
    )
    return _collector_result(
        parameter_key=parameter_key,
        status=status,
        severity="medium",
        actual_value={"audit_log_sample_count": len(rows), "retention_policy_source": "Purview PowerShell required for exact duration"},
        expected_value="Audit retention policies configured",
        finding=reasoning,
        graph_endpoint=endpoint,
        evidence=evidence,
        raw_response={"directoryAudits": response.get("response")},
        graph_calls=1,
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
    return _powershell_limitation_result(tenant, parameter_key="external_storage_providers_in_owa", command="Get-OwaMailboxPolicy | Select-Object Identity,AdditionalStorageProvidersAvailable", expected_value="External storage providers disabled in OWA", pass_criteria="When not enabled, users cannot connect third-party storage services to Outlook Web App", fail_criteria="When enabled, users can connect third-party storage services to Outlook Web App", severity="high", scoring_weight=4.0, reason="This control is fully automatable with Exchange Online PowerShell. The app-only Graph runtime cannot read OWA mailbox policy settings directly, so this collector must run through delegated Exchange automation.")


async def collect_full_calendar_schedules_able_to_be_shared_externally(tenant: ConnectedTenant) -> dict[str, Any]:
    return _powershell_limitation_result(tenant, parameter_key="full_calendar_schedules_able_to_be_shared_externally", command="Get-SharingPolicy | Format-List Domains,Enabled,Default", expected_value="External full calendar sharing disabled", pass_criteria="If False, calendar sharing is disabled across the organization", fail_criteria="If True, calendar sharing is enabled for the organization", severity="medium", scoring_weight=3.0, reason="This control is fully automatable with Exchange Online PowerShell sharing policies. The app-only Graph runtime cannot read this tenant sharing policy directly.")


async def collect_customer_lockbox(tenant: ConnectedTenant) -> dict[str, Any]:
    return _powershell_limitation_result(tenant, parameter_key="customer_lockbox", command="Get-OrganizationConfig | Select-Object CustomerLockBoxEnabled", expected_value="Customer Lockbox enabled", pass_criteria="Microsoft support staff cannot access your content without your explicit approval", fail_criteria="Microsoft support staff can access your content without your explicit approval", severity="medium", scoring_weight=3.0, reason="This control is fully automatable with Exchange Online PowerShell organization configuration. The app-only Graph runtime cannot read CustomerLockBoxEnabled directly.")


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
    sharing = str(settings.get("sharingCapability") or settings.get("oneDriveSharingCapability") or "")
    status = "fail" if "anonymous" in sharing.lower() or "guest" in sharing.lower() else "pass"
    reasoning = f"SharePoint sharingCapability is {sharing or 'not returned'}"
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
    status = "pass" if legacy_enabled is False else "fail"
    reasoning = f"SharePoint legacy auth protocols enabled: {legacy_enabled}"
    evidence = _evaluation_evidence(pass_criteria="When it is enabled", fail_criteria="When it is disabled", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings})
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"isLegacyAuthProtocolsEnabled": legacy_enabled}, expected_value="Modern authentication enabled / legacy auth disabled", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=3.0)


async def collect_sharing_settings_external_internal(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "sharing_settings_external_internal"
    endpoint = "https://graph.microsoft.com/beta/admin/sharepoint/settings"
    response = await _graph_get_json_or_error(tenant, endpoint)
    if not response.get("ok"):
        return _licensing_required_result(tenant, parameter_key=parameter_key, endpoint=endpoint, required_sku="SharePoint Online", required_service="SharePoint tenant settings", required_role="SharePoint Administrator or Global Administrator", required_permissions=["SharePointTenantSettings.Read.All"], expected_value="Restrictive sharing settings enabled", pass_criteria="When settings enabled", fail_criteria="When restrictive setting no set up", severity="critical", scoring_weight=5.0, graph_response=response)
    settings = response.get("response") or {}
    prevent_resharing = settings.get("isResharingByExternalUsersEnabled")
    sharing = str(settings.get("sharingCapability") or "")
    status = "pass" if prevent_resharing is False and "anonymous" not in sharing.lower() else "fail"
    reasoning = f"External resharing enabled: {prevent_resharing}; sharingCapability: {sharing or 'not returned'}"
    evidence = _evaluation_evidence(pass_criteria="When settings enabled", fail_criteria="When restrictive setting no set up", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings})
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"isResharingByExternalUsersEnabled": prevent_resharing, "sharingCapability": settings.get("sharingCapability")}, expected_value="Restrictive sharing settings enabled", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=5.0)


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
    command = "Get-SPOTenant | Select OrphanedPersonalSitesRetentionPeriod,OneDriveRetentionPeriod"
    settings, blocked = await _sharepoint_settings_or_status(
        tenant,
        parameter_key=parameter_key,
        expected_value="Deleted user's OneDrive retention period is configured",
        pass_criteria="Deleted user's OneDrive retention period is configured",
        fail_criteria="Deleted user's OneDrive retention period is not configured or is below the expected baseline",
        severity="low",
        scoring_weight=2.0,
        command=command,
    )
    if blocked:
        return blocked
    assert settings is not None
    retention = settings.get("orphanedPersonalSitesRetentionPeriod") or settings.get("oneDriveRetentionPeriod")
    configured = retention is not None and str(retention) != "0"
    status = "pass" if configured else "fail"
    reasoning = f"OneDrive deleted user retention setting returned: {retention if retention is not None else 'not returned'}"
    evidence = _evaluation_evidence(pass_criteria="Deleted user's OneDrive retention period is configured", fail_criteria="Deleted user's OneDrive retention period is not configured or is below the expected baseline", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings, "required_powershell_command": command})
    return _collector_result(parameter_key=parameter_key, status=status, severity="low", actual_value={"oneDriveRetentionPeriod": retention}, expected_value="Deleted user's OneDrive retention period is configured", finding=reasoning, graph_endpoint="https://graph.microsoft.com/beta/admin/sharepoint/settings", evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=2.0)


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
    default_link = str(settings.get("defaultSharingLinkType") or settings.get("defaultLinkPermission") or "")
    file_link = str(settings.get("fileAnonymousLinkType") or "")
    folder_link = str(settings.get("folderAnonymousLinkType") or "")
    risky = any("edit" in item.lower() for item in [default_link, file_link, folder_link]) or "anonymous" in sharing.lower()
    status = "fail" if risky else "pass"
    reasoning = f"Anyone link permissions: sharingCapability={sharing or 'not returned'}, default={default_link or 'not returned'}, file={file_link or 'not returned'}, folder={folder_link or 'not returned'}"
    evidence = _evaluation_evidence(pass_criteria="Anyone links are disabled or restricted to view-only least privilege access", fail_criteria="Anyone links allow edit or overly permissive access", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sharepoint_settings": settings, "required_powershell_command": command})
    return _collector_result(parameter_key=parameter_key, status=status, severity="critical", actual_value={"sharingCapability": sharing, "defaultSharingLinkType": default_link, "fileAnonymousLinkType": file_link, "folderAnonymousLinkType": folder_link}, expected_value="Anyone links are disabled or restricted to view-only least privilege access", finding=reasoning, graph_endpoint="https://graph.microsoft.com/beta/admin/sharepoint/settings", evidence=evidence, raw_response={"sharepointSettings": settings}, graph_calls=1, scoring_weight=5.0)


async def collect_inactive_site_policies(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "inactive_site_policies"
    endpoint = "/reports/getSharePointSiteUsageDetail(period='D180')"
    report = await _graph_get_text(tenant, endpoint)
    if not report.get("ok"):
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint=endpoint,
            required_api="Microsoft Graph usage reports plus SharePoint Online PowerShell",
            required_permissions=["Reports.Read.All", "Sites.Read.All"],
            expected_value="Inactive site policy is configured",
            pass_criteria="Inactive site policies are configured",
            fail_criteria="Inactive site policies are not configured",
            severity="medium",
            scoring_weight=3.0,
            response=report,
            command="Get-SPOSite -Limit All | Select Url,LastContentModifiedDate,Owner",
        )
    rows = _csv_rows(report)
    inactive = [row for row in rows if not _has_activity(row)]
    ratio = _percent(len(inactive), len(rows))
    status = "pass" if ratio < 20 else "fail"
    reasoning = f"{len(inactive)} inactive SharePoint site(s) found out of {len(rows)} reported sites ({ratio}%)"
    evidence = _evaluation_evidence(pass_criteria="Inactive site policies are configured", fail_criteria="Inactive site policies are not configured", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "site_usage_rows": rows[:50], "inactive_sites": inactive[:50], "required_powershell_command": "Get-SPOSite -Limit All | Select Url,LastContentModifiedDate,Owner"})
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"site_count": len(rows), "inactive_site_count": len(inactive), "inactive_site_percent": ratio}, expected_value="Inactive site policy is configured", finding=reasoning, graph_endpoint=endpoint, evidence=evidence, raw_response={"sharePointSiteUsageDetail": {"row_count": len(rows)}}, graph_calls=1, scoring_weight=3.0)


async def collect_site_ownership_policies(tenant: ConnectedTenant) -> dict[str, Any]:
    parameter_key = "site_ownership_policies"
    client = await _graph_client(tenant)
    try:
        response = await _get_all(client, "/sites", params={"search": "*"})
    except httpx.HTTPStatusError as exc:
        try:
            payload: dict[str, Any] = exc.response.json()
        except ValueError:
            payload = {"error": {"message": exc.response.text}}
        return _collection_error_result(
            tenant,
            parameter_key=parameter_key,
            endpoint="/sites?search=*",
            required_api="Microsoft Graph Sites plus SharePoint Online PowerShell",
            required_permissions=["Sites.Read.All", "Group.Read.All"],
            expected_value="Site ownership policies are configured and sites have accountable owners",
            pass_criteria="Site ownership policies are configured and sites have accountable owners",
            fail_criteria="Site ownership policies are not configured or sites lack accountable ownership",
            severity="medium",
            scoring_weight=3.0,
            response={"ok": False, "status_code": exc.response.status_code, "error": payload.get("error") or payload},
            command="Get-SPOSite -Limit All; Get-SPOUser -Site <url> or Get-MgGroupOwner",
        )
    sites = response.get("value") or []
    missing_owner = [site for site in sites if not (site.get("createdBy") or site.get("owner") or site.get("lastModifiedBy"))]
    ratio = _percent(len(missing_owner), len(sites))
    status = "pass" if ratio < 5 else "fail"
    reasoning = f"{len(missing_owner)} site(s) lack owner/creator metadata out of {len(sites)} enumerated sites ({ratio}%)"
    evidence = _evaluation_evidence(pass_criteria="Site ownership policies are configured and sites have accountable owners", fail_criteria="Site ownership policies are not configured or sites lack accountable ownership", reasoning=reasoning, extra={"tenant_id": tenant.tenant_id, "sites": sites[:50], "sites_missing_owner_metadata": missing_owner[:50], "required_powershell_command": "Get-SPOSite -Limit All; Get-SPOUser -Site <url> or Get-MgGroupOwner"})
    return _collector_result(parameter_key=parameter_key, status=status, severity="medium", actual_value={"site_count": len(sites), "sites_missing_owner_metadata": len(missing_owner), "missing_owner_percent": ratio}, expected_value="Site ownership policies are configured and sites have accountable owners", finding=reasoning, graph_endpoint="/sites?search=*", evidence=evidence, raw_response={"sites": response}, graph_calls=1, scoring_weight=3.0)


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
