from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


def _tenant():
    return SimpleNamespace(tenant_id="tenant-id")


def _authorization_policy(assignments):
    return {
        "id": "authorizationPolicy",
        "defaultUserRolePermissions": {
            "allowedToCreateApps": True,
            "permissionGrantPoliciesAssigned": assignments,
        },
    }


async def _collect(policy):
    from app.services.graph_cra_collector_service import collect_entra_third_party_app_integrations

    with patch(
        "app.services.graph_cra_collector_service._authorization_policy",
        AsyncMock(return_value=policy),
    ):
        return await collect_entra_third_party_app_integrations(_tenant())


@pytest.mark.asyncio
async def test_third_party_integrations_fail_when_user_consent_is_disabled():
    result = await _collect(_authorization_policy([]))

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["user_consent_enabled"] is False
    assert result["raw_value"]["actual_value"]["portal_configuration"] == "Do not allow user consent"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("assignment", "configuration"),
    [
        (
            "ManagePermissionGrantsForSelf.microsoft-user-default-low",
            "Allow user consent for apps from verified publishers, for selected permissions",
        ),
        (
            "managePermissionGrantsForSelf.microsoft-user-default-recommended",
            "Let Microsoft manage your consent settings",
        ),
    ],
)
async def test_third_party_integrations_pass_for_assigned_user_consent_policy(assignment, configuration):
    result = await _collect(_authorization_policy([assignment]))

    assert result["status"] == "pass"
    assert result["raw_value"]["actual_value"]["user_consent_enabled"] is True
    assert result["raw_value"]["actual_value"]["portal_configuration"] == configuration


@pytest.mark.asyncio
async def test_owned_resource_policy_does_not_enable_default_user_consent_and_fails():
    result = await _collect(
        _authorization_policy(
            ["ManagePermissionGrantsForOwnedResource.microsoft-pre-approval-apps-for-group"]
        )
    )

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["user_consent_enabled"] is False


@pytest.mark.asyncio
async def test_custom_policy_passes_when_user_consent_is_enabled():
    result = await _collect(
        _authorization_policy(["ManagePermissionGrantsForSelf.cipp-consent-policy"])
    )

    assert result["status"] == "pass"
    assert result["raw_value"]["actual_value"]["user_consent_enabled"] is True
    assert result["raw_value"]["actual_value"]["supported_enabled_option_selected"] is False
    assert result["evaluated_value"] == "Third-party app integrations are enabled through custom user consent policy: cipp-consent-policy."


@pytest.mark.asyncio
async def test_missing_consent_property_fails_closed_without_guessing():
    result = await _collect({"id": "authorizationPolicy", "defaultUserRolePermissions": {}})

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["configuration_validated"] is False
    assert result["evaluated_value"] == "Unable to validate the tenant configuration for third-party app integrations."


@pytest.mark.asyncio
async def test_graph_failure_returns_fail_only():
    from app.services.graph_cra_collector_service import collect_entra_third_party_app_integrations

    with patch(
        "app.services.graph_cra_collector_service._authorization_policy",
        AsyncMock(side_effect=RuntimeError("Graph unavailable")),
    ):
        result = await collect_entra_third_party_app_integrations(_tenant())

    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["configuration_validated"] is False
