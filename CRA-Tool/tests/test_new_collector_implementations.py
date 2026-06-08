"""
Tests for the two improved collectors:
  - collect_compliance_score_overview  (replaced manual_validation_required stub)
  - collect_emergency_access_accounts  (replaced name-only heuristic with CAP exclusion)
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_tenant() -> Any:
    t = SimpleNamespace()
    t.tenant_id = "fe4eff9a-f69c-48c0-921d-8006a6d5beb2"
    t.app_client_id = "fake-client-id"
    t.encrypted_client_secret = b"fake-secret"
    t.secret_version = 1
    return t


# ─────────────────────────────────────────────────────────────────────────────
# compliance_score_overview
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compliance_score_pass_above_80():
    from app.services.graph_cra_collector_service import collect_compliance_score_overview

    tenant = _make_tenant()

    async def mock_get(url, **kw):
        return {"value": [{"currentScore": 85.0, "maxScore": 100.0}]}

    client = MagicMock()
    client.get = mock_get

    with patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)):
        result = await collect_compliance_score_overview(tenant)

    assert result["status"] == "pass"
    assert result["parameter_key"] == "compliance_score_overview"
    actual = result["raw_value"]["actual_value"]
    assert actual["compliance_score_proxy"] == 85.0
    assert actual["source"] == "Secure Score proxy"


@pytest.mark.asyncio
async def test_compliance_score_fail_below_80():
    from app.services.graph_cra_collector_service import collect_compliance_score_overview

    tenant = _make_tenant()

    async def mock_get(url, **kw):
        return {"value": [{"currentScore": 60.0, "maxScore": 100.0}]}

    client = MagicMock()
    client.get = mock_get

    with patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)):
        result = await collect_compliance_score_overview(tenant)

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["compliance_score_proxy"] == 60.0


@pytest.mark.asyncio
async def test_compliance_score_no_data_returns_fail():
    from app.services.graph_cra_collector_service import collect_compliance_score_overview

    tenant = _make_tenant()

    async def mock_get(url, **kw):
        return {"value": []}

    client = MagicMock()
    client.get = mock_get

    with patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)):
        result = await collect_compliance_score_overview(tenant)

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["compliance_score_proxy"] == 0.0


@pytest.mark.asyncio
async def test_compliance_score_uses_graph_not_manual_validation():
    """The old stub returned manual_validation_required — verify it no longer does."""
    from app.services.graph_cra_collector_service import collect_compliance_score_overview

    tenant = _make_tenant()

    async def mock_get(url, **kw):
        return {"value": [{"currentScore": 90.0, "maxScore": 100.0}]}

    client = MagicMock()
    client.get = mock_get

    with patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)):
        result = await collect_compliance_score_overview(tenant)

    assert result["status"] != "manual_validation_required"
    assert "/security/secureScores" in result["raw_value"]["graph_endpoint"]


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
        "userPrincipalName": "bg@example.com",
        "accountEnabled": True,
        "onPremisesSyncEnabled": None,
    }

    async def mock_get(url, **kw):
        if "directoryRoles" in url and "members" not in url:
            return {"value": [{"id": "role-001", "displayName": "Global Administrator"}]}
        if "members" in url:
            return {"value": []}
        if break_glass_id in url:
            return bg_user
        return {"value": []}

    client = MagicMock()
    client.get = mock_get

    with (
        patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)),
        patch("app.services.graph_cra_collector_service._conditional_access_policies", AsyncMock(return_value=cap_response)),
    ):
        result = await collect_emergency_access_accounts(tenant)

    assert result["status"] == "pass"
    assert result["raw_value"]["actual_value"]["cap_exclusion_count"] == 1
    assert result["raw_value"]["actual_value"]["emergency_access_accounts"] >= 1


@pytest.mark.asyncio
async def test_emergency_accounts_fail_when_nothing_found():
    from app.services.graph_cra_collector_service import collect_emergency_access_accounts

    tenant = _make_tenant()

    async def mock_get(url, **kw):
        if "directoryRoles" in url and "members" not in url:
            return {"value": [{"id": "role-001", "displayName": "Global Administrator"}]}
        if "members" in url:
            return {"value": [{"id": "u1", "displayName": "John Admin", "userPrincipalName": "john@example.com", "accountEnabled": True, "onPremisesSyncEnabled": None}]}
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
async def test_emergency_accounts_name_heuristic_fallback():
    from app.services.graph_cra_collector_service import collect_emergency_access_accounts

    tenant = _make_tenant()

    async def mock_get(url, **kw):
        if "directoryRoles" in url and "members" not in url:
            return {"value": [{"id": "role-001", "displayName": "Global Administrator"}]}
        if "members" in url:
            return {"value": [
                {"id": "u-bg", "displayName": "BreakGlass Account", "userPrincipalName": "breakglass@example.com", "accountEnabled": True, "onPremisesSyncEnabled": None},
            ]}
        return {"value": []}

    client = MagicMock()
    client.get = mock_get

    with (
        patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)),
        patch("app.services.graph_cra_collector_service._conditional_access_policies", AsyncMock(return_value={"value": []})),
    ):
        result = await collect_emergency_access_accounts(tenant)

    assert result["status"] == "pass"
    assert result["raw_value"]["actual_value"]["name_heuristic_count"] == 1


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
            return {"value": []}
        if synced_user_id in url:
            return {"id": synced_user_id, "displayName": "Synced Admin", "accountEnabled": True, "onPremisesSyncEnabled": True}
        return {"value": []}

    client = MagicMock()
    client.get = mock_get

    with (
        patch("app.services.graph_cra_collector_service._graph_client", AsyncMock(return_value=client)),
        patch("app.services.graph_cra_collector_service._conditional_access_policies", AsyncMock(return_value=cap_response)),
    ):
        result = await collect_emergency_access_accounts(tenant)

    assert result["raw_value"]["actual_value"]["cap_exclusion_count"] == 0


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
