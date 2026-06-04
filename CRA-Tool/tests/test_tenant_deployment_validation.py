from datetime import datetime, timedelta, timezone

import pytest

from app.db.models.tenant import ConnectedTenant
from app.services import graph_deployment_validation_service as validation_service
from app.services.graph_deployment_validation_service import validate_deployment_once
from app.services.graph_permission_service import MICROSOFT_GRAPH_APP_ID, REQUIRED_APPLICATION_PERMISSIONS


class FakeGraphClient:
    pass


async def test_deployment_validation_requires_all_graph_confirmations(monkeypatch: pytest.MonkeyPatch):
    tenant = ConnectedTenant(
        tenant_id="tenant-1",
        tenant_name="Tenant 1",
        app_registration_id="app-object-id",
        app_client_id="client-id",
        service_principal_id="sp-object-id",
        secret_id="secret-key-id",
        deployment_status="VALIDATING",
        status="VALIDATING",
    )
    permission_ids = {name: {"id": f"role-{index}"} for index, name in enumerate(REQUIRED_APPLICATION_PERMISSIONS)}
    required_ids = {item["id"] for item in permission_ids.values()}

    async def fake_get_application(client, *, application_object_id):
        assert application_object_id == tenant.app_registration_id
        return {
            "id": tenant.app_registration_id,
            "appId": tenant.app_client_id,
            "requiredResourceAccess": [
                {
                    "resourceAppId": MICROSOFT_GRAPH_APP_ID,
                    "resourceAccess": [{"id": role_id, "type": "Role"} for role_id in required_ids],
                }
            ],
            "passwordCredentials": [
                {
                    "keyId": tenant.secret_id,
                    "endDateTime": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                }
            ],
        }

    async def fake_get_service_principal(client, *, service_principal_id):
        assert service_principal_id == tenant.service_principal_id
        return {"id": tenant.service_principal_id, "appId": tenant.app_client_id}

    async def fake_get_graph_service_principal(client):
        return {"id": "graph-sp-id", "appId": MICROSOFT_GRAPH_APP_ID}

    async def fake_get_required_app_roles(client):
        return permission_ids

    async def fake_get_app_role_assignments(client, *, service_principal_id):
        return [{"appRoleId": role_id, "resourceId": "graph-sp-id"} for role_id in required_ids]

    monkeypatch.setattr(validation_service, "get_application", fake_get_application)
    monkeypatch.setattr(validation_service, "get_service_principal", fake_get_service_principal)
    monkeypatch.setattr(validation_service, "get_graph_service_principal", fake_get_graph_service_principal)
    monkeypatch.setattr(validation_service, "get_required_app_roles", fake_get_required_app_roles)
    monkeypatch.setattr(validation_service, "_get_app_role_assignments", fake_get_app_role_assignments)

    result = await validate_deployment_once(FakeGraphClient(), tenant)

    assert result.app_registration_exists is True
    assert result.service_principal_exists is True
    assert result.secret_exists is True
    assert result.permissions_assigned is True
    assert result.admin_consent_granted is True
    assert result.is_active is True


async def test_deployment_validation_rejects_missing_admin_consent(monkeypatch: pytest.MonkeyPatch):
    tenant = ConnectedTenant(
        tenant_id="tenant-1",
        tenant_name="Tenant 1",
        app_registration_id="app-object-id",
        app_client_id="client-id",
        service_principal_id="sp-object-id",
        secret_id="secret-key-id",
        deployment_status="VALIDATING",
        status="VALIDATING",
    )
    permission_ids = {name: {"id": f"role-{index}"} for index, name in enumerate(REQUIRED_APPLICATION_PERMISSIONS)}
    required_ids = {item["id"] for item in permission_ids.values()}

    async def fake_get_application(client, *, application_object_id):
        return {
            "id": tenant.app_registration_id,
            "appId": tenant.app_client_id,
            "requiredResourceAccess": [
                {
                    "resourceAppId": MICROSOFT_GRAPH_APP_ID,
                    "resourceAccess": [{"id": role_id, "type": "Role"} for role_id in required_ids],
                }
            ],
            "passwordCredentials": [
                {
                    "keyId": tenant.secret_id,
                    "endDateTime": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                }
            ],
        }

    async def fake_get_service_principal(client, *, service_principal_id):
        return {"id": tenant.service_principal_id, "appId": tenant.app_client_id}

    async def fake_get_graph_service_principal(client):
        return {"id": "graph-sp-id", "appId": MICROSOFT_GRAPH_APP_ID}

    async def fake_get_required_app_roles(client):
        return permission_ids

    async def fake_get_app_role_assignments(client, *, service_principal_id):
        return []

    monkeypatch.setattr(validation_service, "get_application", fake_get_application)
    monkeypatch.setattr(validation_service, "get_service_principal", fake_get_service_principal)
    monkeypatch.setattr(validation_service, "get_graph_service_principal", fake_get_graph_service_principal)
    monkeypatch.setattr(validation_service, "get_required_app_roles", fake_get_required_app_roles)
    monkeypatch.setattr(validation_service, "_get_app_role_assignments", fake_get_app_role_assignments)

    result = await validate_deployment_once(FakeGraphClient(), tenant)

    assert result.app_registration_exists is True
    assert result.service_principal_exists is True
    assert result.secret_exists is True
    assert result.permissions_assigned is True
    assert result.admin_consent_granted is False
    assert result.is_active is False
