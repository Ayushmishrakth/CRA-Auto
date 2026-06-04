import pytest

from app.db.models.tenant import ConnectedTenant
from app.services import graph_cra_collector_service as collectors


def _tenant() -> ConnectedTenant:
    return ConnectedTenant(
        tenant_id="tenant-1",
        tenant_name="Tenant",
        app_client_id="client",
        encrypted_client_secret="secret",
    )


@pytest.mark.asyncio
async def test_custom_banned_password_list_passes_with_real_custom_words(monkeypatch):
    async def fake_graph_get_json_or_error(tenant, endpoint):
        return {
            "ok": True,
            "response": {
                "isCustomBannedPasswordListEnabled": True,
                "enforcementMode": "Enforced",
                "customBannedPasswords": ["contoso", "password2026"],
            },
        }

    monkeypatch.setattr(collectors, "_graph_get_json_or_error", fake_graph_get_json_or_error)

    result = await collectors.collect_custom_banned_password_list(_tenant())

    actual = result["raw_value"]["actual_value"]
    evidence = result["raw_value"]["evidence"]
    assert result["status"] == "pass"
    assert actual["enabled"] is True
    assert actual["custom_word_count"] == 2
    assert evidence["custom_banned_password_terms"] == ["contoso", "password2026"]


@pytest.mark.asyncio
async def test_custom_banned_password_list_fails_when_enabled_but_empty(monkeypatch):
    async def fake_graph_get_json_or_error(tenant, endpoint):
        return {
            "ok": True,
            "response": {
                "isCustomBannedPasswordListEnabled": True,
                "enforcementMode": "Enforced",
                "customBannedPasswords": [],
            },
        }

    monkeypatch.setattr(collectors, "_graph_get_json_or_error", fake_graph_get_json_or_error)

    result = await collectors.collect_custom_banned_password_list(_tenant())

    actual = result["raw_value"]["actual_value"]
    assert result["status"] == "fail"
    assert actual["enabled"] is True
    assert actual["custom_word_count"] == 0


@pytest.mark.asyncio
async def test_custom_banned_password_list_manual_when_graph_does_not_expose_fields(monkeypatch):
    async def fake_graph_get_json_or_error(tenant, endpoint):
        return {
            "ok": True,
            "response": {
                "id": "password",
                "state": "enabled",
            },
        }

    monkeypatch.setattr(collectors, "_graph_get_json_or_error", fake_graph_get_json_or_error)

    result = await collectors.collect_custom_banned_password_list(_tenant())

    assert result["status"] == "manual_validation_required"
    assert result["raw_value"]["actual_value"]["enabled"] is None
    assert "did not expose" in result["evaluated_value"]
