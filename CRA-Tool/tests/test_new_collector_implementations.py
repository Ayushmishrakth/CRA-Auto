"""
Tests for the two improved collectors:
  - collect_compliance_score_overview  (no supported Compliance Manager score
    API exists — see the doc comment above the collector; returns pass/fail
    ONLY and must never fall back to Secure Score)
  - collect_emergency_access_accounts  (replaced name-only heuristic with CAP exclusion)
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


def _make_tenant() -> Any:
    t = SimpleNamespace()
    t.tenant_id = "fe4eff9a-f69c-48c0-921d-8006a6d5beb2"
    t.app_client_id = "fake-client-id"
    t.encrypted_client_secret = b"fake-secret"
    t.secret_version = 1
    return t


def _graph_error(status_code: int, message: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://graph.microsoft.com/v1.0/subscribedSkus")
    response = httpx.Response(status_code, request=request, json={"error": {"message": message}})
    return httpx.HTTPStatusError(message, request=request, response=response)


# ─────────────────────────────────────────────────────────────────────────────
# compliance_score_overview
#
# Business rule: this parameter returns ONLY "pass" or "fail". Because Microsoft
# exposes no supported Compliance Manager score API, every path fails today — but
# the finding must carry the specific root cause, and never a fabricated score.
# ─────────────────────────────────────────────────────────────────────────────

async def _run_compliance_collector(mock_get):
    from app.services.graph_cra_collector_service import collect_compliance_score_overview

    client = MagicMock()
    client.get = mock_get
    with patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)):
        return await collect_compliance_score_overview(_make_tenant())


@pytest.mark.asyncio
async def test_compliance_score_licensed_tenant_fails_api_not_supported():
    """Even with a qualifying license, no supported API exists — must fail, never fabricate a score."""

    async def mock_get(url, **kw):
        return {"value": [{"skuPartNumber": "SPE_E5", "consumedUnits": 25}]}

    result = await _run_compliance_collector(mock_get)

    assert result["parameter_key"] == "compliance_score_overview"
    assert result["status"] == "fail"
    actual = result["raw_value"]["actual_value"]
    assert actual["compliance_manager_score"] is None
    assert actual["root_cause"] == "api_not_supported"
    assert "does not expose an officially supported public API" in result["evaluated_value"]


@pytest.mark.asyncio
async def test_compliance_score_unlicensed_tenant_fails_licensing_required():
    async def mock_get(url, **kw):
        return {"value": [{"skuPartNumber": "FLOW_FREE", "consumedUnits": 3}]}

    result = await _run_compliance_collector(mock_get)

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["root_cause"] == "licensing_required"
    assert result["raw_value"]["actual_value"]["compliance_manager_score"] is None


@pytest.mark.asyncio
async def test_compliance_score_no_skus_fails_licensing_required():
    async def mock_get(url, **kw):
        return {"value": []}

    result = await _run_compliance_collector(mock_get)

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["root_cause"] == "licensing_required"


@pytest.mark.asyncio
async def test_compliance_score_permission_denied_fails_insufficient_permissions():
    async def mock_get(url, **kw):
        raise _graph_error(403, "Authorization_RequestDenied")

    result = await _run_compliance_collector(mock_get)

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["root_cause"] == "insufficient_permissions"
    assert "Organization.Read.All" in result["evaluated_value"]


@pytest.mark.asyncio
async def test_compliance_score_service_error_fails_with_reason():
    async def mock_get(url, **kw):
        raise _graph_error(500, "Internal server error")

    result = await _run_compliance_collector(mock_get)

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["root_cause"] == "service_error"


@pytest.mark.asyncio
async def test_compliance_score_only_returns_pass_or_fail_and_never_secure_score():
    """Status must be pass/fail only, and Secure Score must never be queried."""
    called_endpoints: list[str] = []

    async def mock_get(url, **kw):
        called_endpoints.append(url)
        return {"value": [{"skuPartNumber": "SPE_E5", "consumedUnits": 25}]}

    result = await _run_compliance_collector(mock_get)

    assert result["status"] in {"pass", "fail"}
    assert not any("secureScores" in endpoint for endpoint in called_endpoints)
    assert "subscribedSkus" in result["raw_value"]["graph_endpoint"]


# ─────────────────────────────────────────────────────────────────────────────
# emergency_access_accounts
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emergency_accounts_pass_via_cap_exclusion():
    from app.services.graph_cra_collector_service import collect_emergency_access_accounts

    tenant = _make_tenant()
    break_glass_id = "bg-user-001"
    cap_response = {
        "value": [
            {"state": "enabled", "conditions": {"users": {"excludeUsers": [break_glass_id]}}},
            {"state": "enabled", "conditions": {"users": {"excludeUsers": [break_glass_id]}}},
        ]
    }
    bg_user = {
        "id": break_glass_id,
        "displayName": "SVC_Admin_BreakGlass",
        "userPrincipalName": "bg@tenant.onmicrosoft.com",
        "accountEnabled": True,
        "onPremisesSyncEnabled": None,
        "assignedLicenses": [],
    }

    async def mock_get(url, **kw):
        if "directoryRoles" in url and "members" not in url:
            return {"value": [{"id": "role-001", "displayName": "Global Administrator"}]}
        if "members" in url:
            return {"value": [bg_user]}
        return {"value": []}

    client = MagicMock()
    client.get = mock_get

    with (
        patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)),
        patch("app.services.graph_cra_collector_service._conditional_access_policies", AsyncMock(return_value=cap_response)),
    ):
        result = await collect_emergency_access_accounts(tenant)

    assert result["status"] == "pass"
    assert result["raw_value"]["actual_value"]["emergency_access_accounts"] >= 1
    assert "Global Administrator" in result["evaluated_value"]
    assert ".onmicrosoft.com" in result["evaluated_value"]


@pytest.mark.asyncio
async def test_emergency_accounts_fail_when_nothing_found():
    from app.services.graph_cra_collector_service import collect_emergency_access_accounts

    tenant = _make_tenant()

    async def mock_get(url, **kw):
        if "directoryRoles" in url and "members" not in url:
            return {"value": [{"id": "role-001", "displayName": "Global Administrator"}]}
        if "members" in url:
            return {"value": [{"id": "u1", "displayName": "John Admin", "userPrincipalName": "john@example.com", "accountEnabled": True, "onPremisesSyncEnabled": None, "assignedLicenses": [{"skuId": "licensed"}]}]}
        return {"value": []}

    client = MagicMock()
    client.get = mock_get

    with (
        patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)),
        patch("app.services.graph_cra_collector_service._conditional_access_policies", AsyncMock(return_value={"value": []})),
    ):
        result = await collect_emergency_access_accounts(tenant)

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["emergency_access_accounts"] == 0


@pytest.mark.asyncio
async def test_emergency_accounts_name_alone_does_not_qualify():
    from app.services.graph_cra_collector_service import collect_emergency_access_accounts

    tenant = _make_tenant()

    async def mock_get(url, **kw):
        if "directoryRoles" in url and "members" not in url:
            return {"value": [{"id": "role-001", "displayName": "Global Administrator"}]}
        if "members" in url:
            return {"value": [
                    {"id": "u-bg", "displayName": "BreakGlass Account", "userPrincipalName": "breakglass@example.com", "accountEnabled": True, "onPremisesSyncEnabled": None, "assignedLicenses": [{"skuId": "licensed"}]},
            ]}
        return {"value": []}

    client = MagicMock()
    client.get = mock_get

    with (
        patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)),
        patch("app.services.graph_cra_collector_service._conditional_access_policies", AsyncMock(return_value={"value": []})),
    ):
        result = await collect_emergency_access_accounts(tenant)

    assert result["status"] == "fail"
    assert result["evaluated_value"] == "No break glass account is present"


@pytest.mark.asyncio
async def test_emergency_accounts_zero_license_qualifies():
    from app.services.graph_cra_collector_service import collect_emergency_access_accounts

    tenant = _make_tenant()
    candidate = {
        "id": "u-zero-license",
        "displayName": "Emergency Admin",
        "userPrincipalName": "emergency@tenant.onmicrosoft.com",
        "accountEnabled": True,
        "onPremisesSyncEnabled": None,
        "assignedLicenses": [],
    }

    async def mock_get(url, **kw):
        if "directoryRoles" in url and "members" not in url:
            return {"value": [{"id": "role-001", "displayName": "Global Administrator"}]}
        if "members" in url:
            return {"value": [candidate]}
        return {"value": []}

    client = MagicMock()
    client.get = mock_get
    with (
        patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)),
        patch("app.services.graph_cra_collector_service._conditional_access_policies", AsyncMock(return_value={"value": []})),
    ):
        result = await collect_emergency_access_accounts(tenant)

    assert result["status"] == "pass"
    assert result["raw_value"]["actual_value"]["emergency_access_accounts"] == 1


@pytest.mark.asyncio
async def test_emergency_accounts_synced_user_excluded_from_cap_heuristic():
    """On-prem synced accounts must NOT count as break-glass candidates."""
    from app.services.graph_cra_collector_service import collect_emergency_access_accounts

    tenant = _make_tenant()
    synced_user_id = "synced-user-001"
    cap_response = {
        "value": [
            {"state": "enabled", "conditions": {"users": {"excludeUsers": [synced_user_id]}}},
        ]
    }

    async def mock_get(url, **kw):
        if "directoryRoles" in url and "members" not in url:
            return {"value": [{"id": "role-001", "displayName": "Global Administrator"}]}
        if "members" in url:
            return {"value": [{"id": synced_user_id, "displayName": "Synced Admin", "accountEnabled": True, "onPremisesSyncEnabled": True, "assignedLicenses": []}]}
        return {"value": []}

    client = MagicMock()
    client.get = mock_get

    with (
        patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)),
        patch("app.services.graph_cra_collector_service._conditional_access_policies", AsyncMock(return_value=cap_response)),
    ):
        result = await collect_emergency_access_accounts(tenant)

    assert result["raw_value"]["actual_value"]["emergency_access_accounts"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# All 9 target collectors must be registered
# ─────────────────────────────────────────────────────────────────────────────

def test_all_nine_collectors_registered():
    from app.services.graph_cra_collector_service import GRAPH_COLLECTORS

    required = [
        "secure_score_percentage",
        "compliance_score_overview",
        "audit_log_retention_duration",
        "active_sites_count",
        "restricted_access_to_microsoft_entra_admin_centre",
        "self_service_password_reset_authentication_method",
        "user_consent_for_applications",
        "emergency_access_accounts",
        "custom_banned_password_list",
    ]
    missing = [k for k in required if k not in GRAPH_COLLECTORS]
    assert not missing, f"Missing from GRAPH_COLLECTORS: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# Wave 1 · Part 2 — Sensitivity labels: validate APPLICATION, not existence
#
# The collector combines configured labels (informationProtection/sensitivityLabels)
# with applied labels (/groups assignedLabels). PASS only when labels are both
# configured AND applied to at least one Microsoft 365 container.
# ─────────────────────────────────────────────────────────────────────────────

MOD = "app.services.graph_cra_collector_service"


async def _run_label_collector(*, label_response, groups_response=None, groups_exc=None):
    from app.services.graph_cra_collector_service import collect_sensitivity_labels_configured_and_applied

    get_all = AsyncMock(side_effect=groups_exc) if groups_exc else AsyncMock(return_value=groups_response or {"value": []})
    with (
        patch(f"{MOD}._graph_get_json_or_error", AsyncMock(return_value=label_response)),
        patch(f"{MOD}._graph_client", AsyncMock(return_value=MagicMock())),
        patch(f"{MOD}._get_all", get_all),
    ):
        return await collect_sensitivity_labels_configured_and_applied(_make_tenant())


@pytest.mark.asyncio
async def test_labels_pass_when_configured_and_applied():
    result = await _run_label_collector(
        label_response={"ok": True, "response": {"value": [{"name": "Confidential"}, {"name": "Public"}]}},
        groups_response={"value": [
            {"id": "g1", "displayName": "Team A", "assignedLabels": [{"displayName": "Confidential"}]},
            {"id": "g2", "displayName": "Team B", "assignedLabels": []},
        ]},
    )
    assert result["status"] == "pass"
    actual = result["raw_value"]["actual_value"]
    assert actual["configured_label_count"] == 2
    assert actual["applied_container_count"] == 1
    assert "applied" in result["evaluated_value"].lower()


@pytest.mark.asyncio
async def test_labels_fail_when_configured_but_not_applied():
    """The old false-PASS scenario: labels exist but are applied to nothing."""
    result = await _run_label_collector(
        label_response={"ok": True, "response": {"value": [{"name": "Confidential"}]}},
        groups_response={"value": [
            {"id": "g1", "displayName": "Team A", "assignedLabels": []},
            {"id": "g2", "displayName": "Team B", "assignedLabels": []},
        ]},
    )
    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["applied_container_count"] == 0
    assert "not" in result["evaluated_value"].lower()


@pytest.mark.asyncio
async def test_labels_fail_when_none_configured():
    result = await _run_label_collector(
        label_response={"ok": True, "response": {"value": []}},
        groups_response={"value": []},
    )
    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["configured_label_count"] == 0


@pytest.mark.asyncio
async def test_labels_licensing_failure_on_label_endpoint():
    result = await _run_label_collector(
        label_response={"ok": False, "status_code": 403, "error": {"message": "Purview Information Protection not licensed"}},
    )
    # _licensing_required_result → fail with a LICENSING_GAP marker in evidence/value.
    assert result["status"] == "fail"
    blob = json.dumps(result["raw_value"], default=str).upper()
    assert "LICENSING_GAP" in blob


@pytest.mark.asyncio
async def test_labels_permission_failure_on_groups():
    result = await _run_label_collector(
        label_response={"ok": True, "response": {"value": [{"name": "Confidential"}]}},
        groups_exc=_graph_error(403, "Authorization_RequestDenied"),
    )
    assert result["status"] == "collection_error"


@pytest.mark.asyncio
async def test_labels_collectors_share_one_implementation():
    """De-duplication: both keys route through the same helper."""
    import app.services.graph_cra_collector_service as mod
    src_a = mod.collect_sensitivity_labels_configured_and_applied.__code__.co_names
    src_b = mod.collect_information_protection_labels_applied.__code__.co_names
    assert "_sensitivity_label_graph_collector" in src_a
    assert "_sensitivity_label_graph_collector" in src_b


# ─────────────────────────────────────────────────────────────────────────────
# Wave 1 · Part 3 — Device compliance: deviceCompliancePolicies (Intune)
# ─────────────────────────────────────────────────────────────────────────────

async def _run_devices_collector(*, response=None, exc=None):
    from app.services.graph_cra_collector_service import collect_devices_without_compliance_policies

    get_all = AsyncMock(side_effect=exc) if exc else AsyncMock(return_value=response or {"value": []})
    with (
        patch(f"{MOD}._graph_client", AsyncMock(return_value=MagicMock())),
        patch(f"{MOD}._get_all", get_all),
    ):
        return await collect_devices_without_compliance_policies(_make_tenant())


@pytest.mark.asyncio
async def test_devices_pass_when_policy_exists():
    result = await _run_devices_collector(response={"value": [
        {"id": "p1", "displayName": "Windows baseline", "@odata.type": "#microsoft.graph.windows10CompliancePolicy"},
    ]})
    assert result["status"] == "pass"
    assert result["raw_value"]["actual_value"]["compliance_policy_count"] == 1
    assert "deviceCompliancePolicies" in result["raw_value"]["graph_endpoint"]
    # Must NOT read enrolled devices anymore.
    assert "managedDevices" not in result["raw_value"]["graph_endpoint"]


@pytest.mark.asyncio
async def test_devices_fail_when_no_policy():
    result = await _run_devices_collector(response={"value": []})
    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["compliance_policy_count"] == 0
    assert "no intune device compliance" in result["evaluated_value"].lower()


@pytest.mark.asyncio
async def test_devices_licensing_or_permission_failure():
    result = await _run_devices_collector(exc=_graph_error(403, "Application not licensed for Intune"))
    assert result["status"] == "fail"
    blob = json.dumps(result["raw_value"], default=str)
    assert "LICENSING_GAP" in blob.upper()
    assert "Intune" in blob


@pytest.mark.asyncio
async def test_devices_service_failure():
    result = await _run_devices_collector(exc=_graph_error(500, "Internal server error"))
    assert result["status"] == "collection_error"


@pytest.mark.asyncio
async def test_devices_severity_and_weight_consistent():
    result = await _run_devices_collector(response={"value": []})
    # fail → severity surfaces as the collector severity (medium), weight 3.0
    assert result["severity"] == "medium"
    assert result["score_contribution"] == 3.0


# ─────────────────────────────────────────────────────────────────────────────
# Users without MFA — User Registration Details export logic (isMfaCapable)
#
# Mirrors the manual portal check: Entra > Authentication methods > User
# registration details > Export. PASS only when every in-scope member user is
# MFA-capable; any user that is not MFA-capable is "without MFA".
# ─────────────────────────────────────────────────────────────────────────────

async def _run_mfa_collector(*, response=None, exc=None):
    from app.services.graph_cra_collector_service import collect_users_without_mfa

    get_all = AsyncMock(side_effect=exc) if exc else AsyncMock(return_value=response or {"value": []})
    with (
        patch(f"{MOD}._graph_client", AsyncMock(return_value=MagicMock())),
        patch(f"{MOD}._get_all", get_all),
    ):
        return await collect_users_without_mfa(_make_tenant())


@pytest.mark.asyncio
async def test_mfa_pass_when_all_capable():
    result = await _run_mfa_collector(response={"value": [
        {"id": "u1", "userPrincipalName": "a@x.com", "userType": "member", "isMfaCapable": True, "isMfaRegistered": True},
        {"id": "u2", "userPrincipalName": "b@x.com", "userType": "member", "isMfaCapable": True, "isMfaRegistered": True},
    ]})
    assert result["status"] == "pass"
    actual = result["raw_value"]["actual_value"]
    assert actual["users_without_mfa"] == 0
    assert actual["member_users"] == 2
    assert actual["mfa_capable_users"] == 2
    assert "userRegistrationDetails" in result["raw_value"]["graph_endpoint"]
    # Must NOT use the old per-user authentication/methods approach.
    assert "authentication/methods" not in result["raw_value"]["graph_endpoint"]


@pytest.mark.asyncio
async def test_mfa_fail_when_a_capable_user_is_missing_mfa():
    result = await _run_mfa_collector(response={"value": [
        {"id": "u1", "userPrincipalName": "a@x.com", "userType": "member", "isMfaCapable": True, "isMfaRegistered": True},
        {"id": "u2", "userPrincipalName": "gap@x.com", "userType": "member", "isMfaCapable": False, "isMfaRegistered": False},
    ]})
    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["users_without_mfa"] == 1
    assert "gap@x.com" in result["evaluated_value"]


@pytest.mark.asyncio
async def test_mfa_excludes_guests_from_scope():
    result = await _run_mfa_collector(response={"value": [
        {"id": "u1", "userPrincipalName": "a@x.com", "userType": "member", "isMfaCapable": True, "isMfaRegistered": True},
        {"id": "g1", "userPrincipalName": "guest@x.com", "userType": "guest", "isMfaCapable": False, "isMfaRegistered": False},
    ]})
    # Guest is not counted → all in-scope (member) users are capable → pass.
    assert result["status"] == "pass"
    assert result["raw_value"]["actual_value"]["member_users"] == 1
    assert result["raw_value"]["evidence"]["guests_excluded"] == 1


@pytest.mark.asyncio
async def test_mfa_licensing_failure_requires_p1():
    # 403 that explicitly cites licensing → licensing_required (fail + LICENSING_GAP).
    result = await _run_mfa_collector(exc=_graph_error(403, "Tenant is not licensed for this premium feature"))
    assert result["status"] == "fail"
    blob = json.dumps(result["raw_value"], default=str)
    assert "LICENSING_GAP" in blob.upper()
    assert "P1" in blob or "P2" in blob


@pytest.mark.asyncio
async def test_mfa_permission_failure_reported_distinctly():
    # 403 permission denial → collection_error citing the missing permission, NOT a license claim.
    result = await _run_mfa_collector(
        exc=_graph_error(403, "Authorization_RequestDenied: Insufficient privileges to complete the operation.")
    )
    assert result["status"] == "collection_error"
    blob = json.dumps(result["raw_value"], default=str)
    assert "AuditLog.Read.All" in blob
    assert "LICENSING_GAP" not in blob.upper()


@pytest.mark.asyncio
async def test_mfa_service_failure():
    result = await _run_mfa_collector(exc=_graph_error(500, "Internal server error"))
    assert result["status"] == "collection_error"
