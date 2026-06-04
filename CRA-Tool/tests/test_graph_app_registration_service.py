import pytest
import httpx
from urllib.parse import parse_qs, urlparse

from app.core.exceptions import BusinessLogicException, DeploymentValidationError
from app.services import tenant_deployment_service
from app.services.graph_app_registration_service import (
    build_redirect_uri,
    create_application,
    ensure_application_redirect_uri,
    get_application_by_app_id,
)
from app.services.graph_service_principal_service import ensure_service_principal
from app.services.graph_consent_service import build_admin_consent_url


@pytest.fixture(autouse=True)
def fake_permission_access_validation(monkeypatch: pytest.MonkeyPatch):
    async def fake_ensure_application_required_resource_access(
        client,
        *,
        application_object_id,
        required_resource_access,
    ):
        application_client_id = (
            "new-client-id" if application_object_id == "new-object-id" else "application-client-id"
        )
        return (
            {
                "id": application_object_id,
                "appId": application_client_id,
                "requiredResourceAccess": required_resource_access,
            },
            None,
        )

    monkeypatch.setattr(
        tenant_deployment_service,
        "ensure_application_required_resource_access",
        fake_ensure_application_required_resource_access,
    )


class RecordingGraphClient:
    def __init__(self, *, stored_redirect_uris=None):
        self.posts = []
        self.patches = []
        self.stored_redirect_uris = stored_redirect_uris or []

    async def post(self, path, *, json=None):
        self.posts.append({"path": path, "json": json})
        return {"id": "application-object-id", "appId": "application-client-id"}

    async def get(self, path, *, params=None):
        if path == "/applications":
            if params == {
                "$filter": "appId eq 'application-client-id'",
                "$select": "id,appId,displayName,requiredResourceAccess,passwordCredentials,web",
            }:
                return {
                    "value": [
                        {
                            "id": "application-object-id",
                            "appId": "application-client-id",
                            "web": {"redirectUris": self.stored_redirect_uris},
                        }
                    ]
                }
            return {"value": []}
        if path == "/servicePrincipals":
            if params == {
                "$filter": "appId eq 'application-client-id'",
                "$select": "id,appId,displayName,appRoleAssignments",
            }:
                return {"value": [{"id": "service-principal-id", "appId": "application-client-id"}]}
            return {"value": []}
        return {
            "id": "application-object-id",
            "appId": "application-client-id",
            "web": {"redirectUris": self.stored_redirect_uris},
        }

    async def patch(self, path, *, json=None):
        self.patches.append({"path": path, "json": json})
        self.stored_redirect_uris = list((json.get("web") or {}).get("redirectUris") or [])
        return {}


async def test_create_application_stores_supplied_redirect_uri():
    redirect_uri = "http://localhost:3000/tenant/deployment-success"
    client = RecordingGraphClient()

    app = await create_application(
        client,
        required_resource_access=[],
        redirect_uri=redirect_uri,
    )

    assert app["appId"] == "application-client-id"
    assert client.posts[0]["path"] == "/applications"
    assert client.posts[0]["json"]["web"]["redirectUris"] == [redirect_uri]


async def test_verify_application_redirect_uri_accepts_persisted_uri():
    redirect_uri = "https://cra.example.com/tenant/deployment-success"
    client = RecordingGraphClient(stored_redirect_uris=[redirect_uri])

    app, patch_result, attempts = await ensure_application_redirect_uri(
        client,
        application_object_id="application-object-id",
        redirect_uri=redirect_uri,
        initial_delay_seconds=0,
    )

    assert app["web"]["redirectUris"] == [redirect_uri]
    assert patch_result is None
    assert attempts == 1


async def test_ensure_application_redirect_uri_patches_and_verifies_missing_uri():
    redirect_uri = "https://cra.example.com/tenant/deployment-success"
    client = RecordingGraphClient(stored_redirect_uris=[])

    app, patch_result, attempts = await ensure_application_redirect_uri(
        client,
        application_object_id="application-object-id",
        redirect_uri=redirect_uri,
        initial_delay_seconds=0,
    )

    assert app["web"]["redirectUris"] == [redirect_uri]
    assert patch_result == {"payload": {"web": {"redirectUris": [redirect_uri]}}, "response": {}}
    assert client.patches[0]["path"] == "/applications/application-object-id"
    assert attempts == 2


def test_consent_url_generation_includes_supplied_redirect_uri():
    redirect_uri = "https://cra.example.com/tenant/deployment-success"

    url = build_admin_consent_url(
        tenant_id="tenant-id",
        client_id="application-client-id",
        redirect_uri=redirect_uri,
    )

    assert "client_id=application-client-id" in url
    assert "redirect_uri=https%3A%2F%2Fcra.example.com%2Ftenant%2Fdeployment-success" in url


async def test_create_application_rejects_missing_redirect_uri():
    client = RecordingGraphClient()

    with pytest.raises(BusinessLogicException, match="Deployment redirect URI is required"):
        await create_application(
            client,
            required_resource_access=[],
            redirect_uri="",
        )


async def test_deployment_start_rejects_missing_redirect_uri_before_graph():
    assert build_redirect_uri("https://cra.example.com") == "https://cra.example.com/tenant/deployment-success"


async def test_verify_application_redirect_uri_rejects_missing_persisted_uri():
    class NeverPersistingGraphClient(RecordingGraphClient):
        async def patch(self, path, *, json=None):
            self.patches.append({"path": path, "json": json})

    client = NeverPersistingGraphClient(stored_redirect_uris=[])

    with pytest.raises(BusinessLogicException, match="Azure App Registration redirect URI configuration failed"):
        await ensure_application_redirect_uri(
            client,
            application_object_id="application-object-id",
            redirect_uri="http://localhost:3000/tenant/deployment-success",
            max_attempts=2,
            initial_delay_seconds=0,
        )


async def test_application_lookup_by_app_id_returns_created_application():
    client = RecordingGraphClient(stored_redirect_uris=["http://localhost:3000/tenant/deployment-success"])

    app = await get_application_by_app_id(client, application_client_id="application-client-id")

    assert app["id"] == "application-object-id"
    assert app["appId"] == "application-client-id"


async def test_service_principal_lookup_by_app_id_reuses_existing_principal():
    client = RecordingGraphClient()

    service_principal = await ensure_service_principal(client, app_id="application-client-id")

    assert service_principal["id"] == "service-principal-id"
    assert service_principal["appId"] == "application-client-id"
    assert client.posts == []


async def test_deployment_persists_verified_redirect_uri_and_generates_consent_url(
    db_session,
    auth_context,
    monkeypatch: pytest.MonkeyPatch,
):
    expected_redirect_uri = "http://localhost:3000/tenant/deployment-success"

    async def fake_assert_graph_token(client, *, access_token, tenant_id):
        return {
            "organization": {"id": tenant_id, "displayName": "Tenant"},
            "scopes": ["Application.ReadWrite.All"],
            "diagnostics": {"audience": "https://graph.microsoft.com"},
        }

    async def fake_build_required_resource_access(client):
        return []

    async def fake_create_application(client, *, display_name, required_resource_access, redirect_uri):
        assert redirect_uri == expected_redirect_uri
        return {
            "id": "application-object-id",
            "appId": "application-client-id",
            "_graph_create_payload": {
                "displayName": display_name,
                "web": {"redirectUris": [redirect_uri]},
            },
        }

    async def fake_ensure_application_redirect_uri(client, *, application_object_id, redirect_uri):
        assert application_object_id == "application-object-id"
        assert redirect_uri == expected_redirect_uri
        return (
            {"id": application_object_id, "appId": "application-client-id", "web": {"redirectUris": [redirect_uri]}},
            {"payload": {"web": {"redirectUris": [redirect_uri]}}, "response": {}},
            2,
        )

    async def fake_get_application(client, *, application_object_id):
        assert application_object_id == "application-object-id"
        return {
            "id": "application-object-id",
            "appId": "application-client-id",
            "web": {"redirectUris": [expected_redirect_uri]},
        }

    async def fake_get_application_by_app_id(client, *, application_client_id):
        assert application_client_id == "application-client-id"
        return {
            "id": "application-object-id",
            "appId": "application-client-id",
            "web": {"redirectUris": [expected_redirect_uri]},
        }

    async def fake_ensure_service_principal(client, *, app_id):
        assert app_id == "application-client-id"
        return {"id": "service-principal-id", "appId": "application-client-id"}

    async def fake_create_client_secret(client, *, application_object_id):
        return {
            "secretText": "real-secret-value",
            "keyId": "secret-id",
            "endDateTime": "2028-05-29T17:18:52.2994169+00:00",
        }

    monkeypatch.setattr(tenant_deployment_service, "_assert_graph_token", fake_assert_graph_token)
    monkeypatch.setattr(tenant_deployment_service, "build_required_resource_access", fake_build_required_resource_access)
    monkeypatch.setattr(tenant_deployment_service, "create_application", fake_create_application)
    monkeypatch.setattr(tenant_deployment_service, "ensure_application_redirect_uri", fake_ensure_application_redirect_uri)
    monkeypatch.setattr(tenant_deployment_service, "get_application", fake_get_application)
    monkeypatch.setattr(tenant_deployment_service, "get_application_by_app_id", fake_get_application_by_app_id)
    monkeypatch.setattr(tenant_deployment_service, "ensure_service_principal", fake_ensure_service_principal)
    monkeypatch.setattr(tenant_deployment_service, "create_client_secret", fake_create_client_secret)

    result = await tenant_deployment_service.deploy_tenant_access(
        db_session,
        current_user=auth_context["user"],
        tenant_id=auth_context["tenant"].tenant_id,
        graph_access_token="header.payload.signature",
        redirect_uri=expected_redirect_uri,
    )

    assert result["application_client_id"] == "application-client-id"
    assert result["application_object_id"] == "application-object-id"
    assert result["service_principal_id"] == "service-principal-id"
    assert result["redirect_uri"] == expected_redirect_uri
    assert result["deployment_status"] == "CONSENT_REQUIRED"
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Ftenant%2Fdeployment-success" in result["admin_consent_url"]
    consent_query = parse_qs(urlparse(result["admin_consent_url"]).query)
    assert consent_query["client_id"] == ["application-client-id"]
    assert consent_query["client_id"] != ["application-object-id"]
    assert consent_query["client_id"] != ["service-principal-id"]
    assert consent_query["client_id"] != ["secret-id"]
    assert result["deployment_diagnostics"]["redirect_uri_requested"] == expected_redirect_uri
    assert result["deployment_diagnostics"]["redirect_uri_verified"] is True
    assert result["deployment_diagnostics"]["graph_create_payload"]["web"]["redirectUris"] == [expected_redirect_uri]
    assert result["deployment_diagnostics"]["graph_patch_payload"]["web"]["redirectUris"] == [expected_redirect_uri]
    assert result["deployment_diagnostics"]["graph_patch_response"] == {}
    assert result["deployment_diagnostics"]["graph_read_response"]["web"]["redirectUris"] == [expected_redirect_uri]
    assert result["deployment_diagnostics"]["graph_consent_application_read_response"]["appId"] == "application-client-id"
    assert result["deployment_diagnostics"]["graph_consent_application_appid_lookup_response"]["appId"] == "application-client-id"
    assert result["deployment_diagnostics"]["CONSENT_CLIENT_ID"] == "application-client-id"
    assert result["deployment_diagnostics"]["CONSENT_URL"] == result["admin_consent_url"]
    assert result["deployment_diagnostics"]["TENANT_ID"] == auth_context["tenant"].tenant_id
    assert result["deployment_diagnostics"]["consent_client_id"] == "application-client-id"
    assert result["deployment_diagnostics"]["consent_url_generated"] is True
    assert result["deployment_diagnostics"]["stale_consent_url_cleared"] is True


def test_consent_url_identifier_validation_rejects_object_id():
    url = build_admin_consent_url(
        tenant_id="tenant-id",
        client_id="application-object-id",
        redirect_uri="http://localhost:3000/tenant/deployment-success",
    )

    with pytest.raises(DeploymentValidationError, match="Consent URL is using wrong Azure identifier"):
        tenant_deployment_service._validate_consent_client_id(url, "application-client-id")


async def test_consent_application_verification_fails_when_app_id_lookup_missing(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_application(client, *, application_object_id):
        assert application_object_id == "application-object-id"
        return {"id": "application-object-id", "appId": "application-client-id"}

    async def fake_get_application_by_app_id(client, *, application_client_id):
        assert application_client_id == "application-client-id"
        return None

    monkeypatch.setattr(tenant_deployment_service, "get_application", fake_get_application)
    monkeypatch.setattr(tenant_deployment_service, "get_application_by_app_id", fake_get_application_by_app_id)

    with pytest.raises(DeploymentValidationError, match="Azure application lookup by client ID failed"):
        await tenant_deployment_service._verify_consent_application(
            object(),
            application_object_id="application-object-id",
            application_client_id="application-client-id",
        )


async def test_deployment_clears_stale_app_registration_and_creates_new_app(
    db_session,
    auth_context,
    monkeypatch: pytest.MonkeyPatch,
):
    expected_redirect_uri = "http://localhost:3000/tenant/deployment-success"
    tenant = auth_context["tenant"]
    tenant.app_registration_id = "old-object-id"
    tenant.app_client_id = "old-client-id"
    tenant.service_principal_id = "old-service-principal-id"
    tenant.admin_consent_url = (
        "https://login.microsoftonline.com/tenant-id/adminconsent"
        "?client_id=old-client-id&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Ftenant%2Fdeployment-success"
    )
    await db_session.commit()

    async def fake_assert_graph_token(client, *, access_token, tenant_id):
        return {
            "organization": {"id": tenant_id, "displayName": "Tenant"},
            "scopes": ["Application.ReadWrite.All"],
            "diagnostics": {"audience": "https://graph.microsoft.com"},
        }

    async def fake_build_required_resource_access(client):
        return []

    async def fake_get_application(client, *, application_object_id):
        if application_object_id == "old-object-id":
            request = httpx.Request("GET", "https://graph.microsoft.com/v1.0/applications/old-object-id")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("not found", request=request, response=response)
        assert application_object_id == "new-object-id"
        return {
            "id": "new-object-id",
            "appId": "new-client-id",
            "web": {"redirectUris": [expected_redirect_uri]},
        }

    async def fake_get_application_by_app_id(client, *, application_client_id):
        if application_client_id == "old-client-id":
            return None
        assert application_client_id == "new-client-id"
        return {
            "id": "new-object-id",
            "appId": "new-client-id",
            "web": {"redirectUris": [expected_redirect_uri]},
        }

    async def fake_create_application(client, *, display_name, required_resource_access, redirect_uri):
        assert redirect_uri == expected_redirect_uri
        return {
            "id": "new-object-id",
            "appId": "new-client-id",
            "_graph_create_payload": {
                "displayName": display_name,
                "web": {"redirectUris": [redirect_uri]},
            },
        }

    async def fake_ensure_application_redirect_uri(client, *, application_object_id, redirect_uri):
        assert application_object_id == "new-object-id"
        return (
            {"id": "new-object-id", "appId": "new-client-id", "web": {"redirectUris": [redirect_uri]}},
            None,
            1,
        )

    async def fake_ensure_service_principal(client, *, app_id):
        assert app_id == "new-client-id"
        return {"id": "new-service-principal-id", "appId": "new-client-id"}

    async def fake_create_client_secret(client, *, application_object_id):
        assert application_object_id == "new-object-id"
        return {
            "secretText": "real-secret-value",
            "keyId": "new-secret-id",
            "endDateTime": "2028-05-29T17:18:52.2994169+00:00",
        }

    monkeypatch.setattr(tenant_deployment_service, "_assert_graph_token", fake_assert_graph_token)
    monkeypatch.setattr(tenant_deployment_service, "build_required_resource_access", fake_build_required_resource_access)
    monkeypatch.setattr(tenant_deployment_service, "get_application", fake_get_application)
    monkeypatch.setattr(tenant_deployment_service, "get_application_by_app_id", fake_get_application_by_app_id)
    monkeypatch.setattr(tenant_deployment_service, "create_application", fake_create_application)
    monkeypatch.setattr(tenant_deployment_service, "ensure_application_redirect_uri", fake_ensure_application_redirect_uri)
    monkeypatch.setattr(tenant_deployment_service, "ensure_service_principal", fake_ensure_service_principal)
    monkeypatch.setattr(tenant_deployment_service, "create_client_secret", fake_create_client_secret)

    result = await tenant_deployment_service.deploy_tenant_access(
        db_session,
        current_user=auth_context["user"],
        tenant_id=auth_context["tenant"].tenant_id,
        graph_access_token="header.payload.signature",
        redirect_uri=expected_redirect_uri,
    )

    consent_query = parse_qs(urlparse(result["admin_consent_url"]).query)
    assert result["application_client_id"] == "new-client-id"
    assert result["application_object_id"] == "new-object-id"
    assert result["service_principal_id"] == "new-service-principal-id"
    assert consent_query["client_id"] == ["new-client-id"]
    assert consent_query["client_id"] != ["old-client-id"]
    assert result["deployment_diagnostics"]["stale_deployment_record_cleared"] is True
    assert result["deployment_diagnostics"]["stale_application_client_id"] == "old-client-id"


async def test_deployment_debug_endpoint_returns_persisted_redirect_diagnostics(
    api_client,
    db_session,
    auth_context,
):
    tenant = auth_context["tenant"]
    tenant.app_registration_id = "application-object-id"
    tenant.app_client_id = "application-client-id"
    tenant.service_principal_id = "service-principal-id"
    tenant.secret_id = "secret-id"
    tenant.redirect_uri = "http://localhost:3000/tenant/deployment-success"
    tenant.admin_consent_url = (
        "https://login.microsoftonline.com/tenant-id/adminconsent"
        "?client_id=application-client-id&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Ftenant%2Fdeployment-success"
    )
    tenant.deployment_status = "CONSENT_REQUIRED"
    tenant.deployment_step = "CONSENT_GENERATION"
    tenant.deployment_diagnostics = {
        "graph_read_response": {
            "web": {
                "redirectUris": ["http://localhost:3000/tenant/deployment-success"],
            }
        }
    }
    await db_session.commit()

    response = await api_client.get(
        "/api/v1/tenants/deployment/debug",
        headers=auth_context["headers"],
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["tenant_id"] == tenant.tenant_id
    assert data["application_client_id"] == "application-client-id"
    assert data["application_object_id"] == "application-object-id"
    assert data["consent_url"] == tenant.admin_consent_url
    assert data["redirect_uri"] == "http://localhost:3000/tenant/deployment-success"
    assert data["application_id"] == "application-object-id"
    assert data["client_id"] == "application-client-id"
    assert data["redirect_uri_expected"] == "http://localhost:3000/tenant/deployment-success"
    assert data["redirect_uri_actual"] == ["http://localhost:3000/tenant/deployment-success"]
    assert data["service_principal_id"] == "service-principal-id"
    assert "secret_id" not in data
    assert data["deployment_status"] == "CONSENT_REQUIRED"
    assert data["deployment_step"] == "CONSENT_GENERATION"


async def test_deployment_runtime_debug_returns_consent_identifier_state(
    api_client,
    db_session,
    auth_context,
):
    tenant = auth_context["tenant"]
    tenant.app_registration_id = "application-object-id"
    tenant.app_client_id = "application-client-id"
    tenant.service_principal_id = "service-principal-id"
    tenant.redirect_uri = "http://localhost:3000/tenant/deployment-success"
    tenant.admin_consent_url = (
        "https://login.microsoftonline.com/tenant-id/adminconsent"
        "?client_id=application-client-id&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Ftenant%2Fdeployment-success"
    )
    tenant.deployment_status = "CONSENT_REQUIRED"
    tenant.consent_status = "pending_admin_consent"
    await db_session.commit()

    response = await api_client.get(
        "/api/v1/tenants/deployment/runtime-debug",
        headers=auth_context["headers"],
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["application_client_id"] == "application-client-id"
    assert data["application_object_id"] == "application-object-id"
    assert data["service_principal_id"] == "service-principal-id"
    assert data["tenant_id"] == tenant.tenant_id
    assert data["redirect_uri"] == "http://localhost:3000/tenant/deployment-success"
    assert data["consent_url"] == tenant.admin_consent_url
    assert data["deployment_status"] == "CONSENT_REQUIRED"
    assert data["consent_status"] == "pending_admin_consent"
    assert data["consent_url_client_id"] == "application-client-id"
    assert data["consent_url_matches_application_client_id"] is True
    assert data["deployment_service_version"] == tenant_deployment_service.DEPLOYMENT_SERVICE_VERSION


def _not_found(path: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", f"https://graph.microsoft.com/v1.0{path}")
    response = httpx.Response(404, request=request)
    return httpx.HTTPStatusError("not found", request=request, response=response)


def _install_validate_recovery_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    existing_app,
    existing_app_by_app_id,
    existing_service_principal=None,
):
    expected_redirect_uri = "http://localhost:3000/tenant/deployment-success"

    async def fake_assert_graph_token(client, *, access_token, tenant_id):
        return {
            "organization": {"id": tenant_id, "displayName": "Tenant"},
            "scopes": ["Application.ReadWrite.All"],
            "diagnostics": {"audience": "https://graph.microsoft.com"},
        }

    async def fake_build_required_resource_access(client):
        return []

    async def fake_get_application(client, *, application_object_id):
        if application_object_id == "new-object-id":
            return {"id": "new-object-id", "appId": "new-client-id", "web": {"redirectUris": [expected_redirect_uri]}}
        if isinstance(existing_app, Exception):
            raise existing_app
        return existing_app

    async def fake_get_application_by_app_id(client, *, application_client_id):
        if application_client_id == "new-client-id":
            return {"id": "new-object-id", "appId": "new-client-id", "web": {"redirectUris": [expected_redirect_uri]}}
        return existing_app_by_app_id

    async def fake_create_application(client, *, display_name, required_resource_access, redirect_uri):
        assert redirect_uri == expected_redirect_uri
        return {
            "id": "new-object-id",
            "appId": "new-client-id",
            "_graph_create_payload": {"displayName": display_name, "web": {"redirectUris": [redirect_uri]}},
        }

    async def fake_ensure_application_redirect_uri(client, *, application_object_id, redirect_uri):
        if application_object_id == "new-object-id":
            app_id = "new-client-id"
        else:
            app_id = "application-client-id"
        return {"id": application_object_id, "appId": app_id, "web": {"redirectUris": [redirect_uri]}}, None, 1

    async def fake_get_service_principal(client, *, service_principal_id):
        if isinstance(existing_service_principal, Exception):
            raise existing_service_principal
        if existing_service_principal is not None:
            return existing_service_principal
        return {"id": service_principal_id, "appId": "application-client-id"}

    async def fake_ensure_service_principal(client, *, app_id):
        return {"id": f"{app_id}-service-principal-id", "appId": app_id}

    async def fake_create_client_secret(client, *, application_object_id):
        return {
            "secretText": "real-secret-value",
            "keyId": "validation-secret-id",
            "endDateTime": "2028-05-29T17:18:52.2994169+00:00",
        }

    monkeypatch.setattr(tenant_deployment_service, "_assert_graph_token", fake_assert_graph_token)
    monkeypatch.setattr(tenant_deployment_service, "build_required_resource_access", fake_build_required_resource_access)
    monkeypatch.setattr(tenant_deployment_service, "get_application", fake_get_application)
    monkeypatch.setattr(tenant_deployment_service, "get_application_by_app_id", fake_get_application_by_app_id)
    monkeypatch.setattr(tenant_deployment_service, "create_application", fake_create_application)
    monkeypatch.setattr(tenant_deployment_service, "ensure_application_redirect_uri", fake_ensure_application_redirect_uri)
    monkeypatch.setattr(tenant_deployment_service, "get_service_principal", fake_get_service_principal)
    monkeypatch.setattr(tenant_deployment_service, "ensure_service_principal", fake_ensure_service_principal)
    monkeypatch.setattr(tenant_deployment_service, "create_client_secret", fake_create_client_secret)


async def test_deployment_validate_recovers_deleted_application(db_session, auth_context, monkeypatch):
    tenant = auth_context["tenant"]
    tenant.app_registration_id = "old-object-id"
    tenant.app_client_id = "old-client-id"
    tenant.service_principal_id = "old-service-principal-id"
    tenant.redirect_uri = "http://localhost:3000/tenant/deployment-success"
    await db_session.commit()
    _install_validate_recovery_fakes(
        monkeypatch,
        existing_app=_not_found("/applications/old-object-id"),
        existing_app_by_app_id=None,
    )

    result = await tenant_deployment_service.validate_tenant_deployment(
        db_session,
        current_user=auth_context["user"],
        graph_access_token="header.payload.signature",
    )

    assert result["deployment_valid"] is True
    assert result["app_exists"] is True
    assert result["app_id"] == "new-client-id"
    assert result["object_id"] == "new-object-id"
    assert result["service_principal_exists"] is True
    assert parse_qs(urlparse(result["consent_url"]).query)["client_id"] == ["new-client-id"]
    assert tenant.deployment_diagnostics["deployment_invalid_reason"]
    assert tenant.deployment_diagnostics["stale_application_client_id"] == "old-client-id"


async def test_deployment_validate_recovers_stale_client_id(db_session, auth_context, monkeypatch):
    tenant = auth_context["tenant"]
    tenant.app_registration_id = "old-object-id"
    tenant.app_client_id = "old-client-id"
    tenant.redirect_uri = "http://localhost:3000/tenant/deployment-success"
    await db_session.commit()
    _install_validate_recovery_fakes(
        monkeypatch,
        existing_app={"id": "old-object-id", "appId": "actual-client-id", "web": {"redirectUris": [tenant.redirect_uri]}},
        existing_app_by_app_id=None,
    )

    result = await tenant_deployment_service.validate_tenant_deployment(
        db_session,
        current_user=auth_context["user"],
        graph_access_token="header.payload.signature",
    )

    assert result["app_id"] == "new-client-id"
    assert result["object_id"] == "new-object-id"
    assert parse_qs(urlparse(result["consent_url"]).query)["client_id"] == ["new-client-id"]


async def test_deployment_validate_recovers_stale_object_id(db_session, auth_context, monkeypatch):
    tenant = auth_context["tenant"]
    tenant.app_registration_id = "old-object-id"
    tenant.app_client_id = "application-client-id"
    tenant.redirect_uri = "http://localhost:3000/tenant/deployment-success"
    await db_session.commit()
    _install_validate_recovery_fakes(
        monkeypatch,
        existing_app={"id": "old-object-id", "appId": "application-client-id", "web": {"redirectUris": [tenant.redirect_uri]}},
        existing_app_by_app_id={"id": "different-object-id", "appId": "application-client-id"},
    )

    result = await tenant_deployment_service.validate_tenant_deployment(
        db_session,
        current_user=auth_context["user"],
        graph_access_token="header.payload.signature",
    )

    assert result["deployment_valid"] is True
    assert result["app_id"] == "new-client-id"
    assert result["object_id"] == "new-object-id"


async def test_deployment_validate_recovers_deleted_service_principal(db_session, auth_context, monkeypatch):
    tenant = auth_context["tenant"]
    tenant.app_registration_id = "application-object-id"
    tenant.app_client_id = "application-client-id"
    tenant.service_principal_id = "deleted-service-principal-id"
    tenant.redirect_uri = "http://localhost:3000/tenant/deployment-success"
    tenant.secret_id = "existing-secret-id"
    await db_session.commit()
    _install_validate_recovery_fakes(
        monkeypatch,
        existing_app={
            "id": "application-object-id",
            "appId": "application-client-id",
            "web": {"redirectUris": [tenant.redirect_uri]},
        },
        existing_app_by_app_id={"id": "application-object-id", "appId": "application-client-id"},
        existing_service_principal=_not_found("/servicePrincipals/deleted-service-principal-id"),
    )

    result = await tenant_deployment_service.validate_tenant_deployment(
        db_session,
        current_user=auth_context["user"],
        graph_access_token="header.payload.signature",
    )

    assert result["deployment_valid"] is True
    assert result["app_id"] == "application-client-id"
    assert result["service_principal_exists"] is True
    assert tenant.service_principal_id == "application-client-id-service-principal-id"


async def test_deployment_validate_endpoint_returns_validation_payload(api_client, db_session, auth_context, monkeypatch):
    tenant = auth_context["tenant"]
    tenant.app_registration_id = "application-object-id"
    tenant.app_client_id = "application-client-id"
    tenant.service_principal_id = "service-principal-id"
    tenant.redirect_uri = "http://localhost:3000/tenant/deployment-success"
    tenant.secret_id = "existing-secret-id"
    await db_session.commit()
    _install_validate_recovery_fakes(
        monkeypatch,
        existing_app={
            "id": "application-object-id",
            "appId": "application-client-id",
            "web": {"redirectUris": [tenant.redirect_uri]},
        },
        existing_app_by_app_id={"id": "application-object-id", "appId": "application-client-id"},
        existing_service_principal={"id": "service-principal-id", "appId": "application-client-id"},
    )

    response = await api_client.get(
        "/api/v1/tenants/deployment/validate",
        headers={**auth_context["headers"], "X-Graph-Access-Token": "header.payload.signature"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "tenant_id": tenant.tenant_id,
        "deployment_valid": True,
        "app_exists": True,
        "app_id": "application-client-id",
        "object_id": "application-object-id",
        "service_principal_exists": True,
        "redirect_uri_valid": True,
        "consent_url": tenant.admin_consent_url,
    }
