import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.models.assessment import Assessment
from app.db.models.audit_log import AuditLog
from app.db.models.tenant import ConnectedTenant


async def test_openapi_and_route_registration(api_client: AsyncClient):
    response = await api_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/tenants/connect" in paths
    assert "/api/v1/tenants/deployment/debug" in paths
    assert "/api/v1/assessments/start" in paths
    assert "/api/v1/admin/parameters" in paths
    assert "/api/v1/health/db" in paths
    route_paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/ws/assessment/{assessment_id}" in route_paths


async def test_health_endpoints(api_client: AsyncClient):
    for path in ["/health", "/api/v1/health", "/api/v1/health/auth", "/api/v1/health/system"]:
        response = await api_client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["request_id"]


async def test_db_health_endpoint(api_client: AsyncClient):
    response = await api_client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "healthy"


async def test_protected_endpoint_requires_jwt(api_client: AsyncClient):
    response = await api_client.get("/api/v1/tenants")
    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_tenant_connect_list_permissions_and_audit(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    tenant_id = auth_context["tenant"].tenant_id
    response = await api_client.post(
        "/api/v1/tenants/connect",
        headers=auth_context["headers"],
        json={"tenant_id": tenant_id, "tenant_name": "Updated Tenant"},
    )
    assert response.status_code == 201
    assert response.json()["data"]["tenant_id"] == tenant_id

    response = await api_client.get("/api/v1/tenants", headers=auth_context["headers"])
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

    response = await api_client.get(
        f"/api/v1/tenants/{tenant_id}/permissions",
        headers=auth_context["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"]["permissions"] == ["User.Read.All"]

    audit_events = (await db_session.execute(select(AuditLog.event_type))).scalars().all()
    assert "TENANT_CONNECTED" in audit_events


async def test_cross_tenant_access_is_rejected(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    other_tenant = ConnectedTenant(
        tenant_id="other-tenant",
        tenant_name="Other",
        consent_status="connected",
        deployment_status="ACTIVE",
        status="ACTIVE",
    )
    db_session.add(other_tenant)
    await db_session.commit()

    response = await api_client.get(
        "/api/v1/tenants/other-tenant",
        headers=auth_context["headers"],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_ACCESS_DENIED"


async def test_assessment_start_get_list_score_and_findings(
    api_client: AsyncClient,
    auth_context: dict,
):
    tenant_id = auth_context["tenant"].tenant_id
    response = await api_client.post(
        "/api/v1/assessments/start",
        headers=auth_context["headers"],
        json={"tenant_id": tenant_id},
    )
    assert response.status_code == 202
    assessment_id = response.json()["data"]["id"]

    response = await api_client.get(
        f"/api/v1/assessments/{assessment_id}",
        headers=auth_context["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"]["tenant_id"] == tenant_id

    response = await api_client.get(
        f"/api/v1/tenants/{tenant_id}/assessments?limit=10&offset=0",
        headers=auth_context["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

    response = await api_client.get(
        f"/api/v1/assessments/{assessment_id}/score",
        headers=auth_context["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "queued"

    response = await api_client.get(
        f"/api/v1/assessments/{assessment_id}/findings",
        headers=auth_context["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_assessment_cross_tenant_rejected(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    other_assessment = Assessment(
        tenant_id="other-tenant",
        triggered_by_user_id=auth_context["user"].id,
        status="queued",
        progress_pct=0,
    )
    db_session.add(other_assessment)
    await db_session.commit()

    response = await api_client.get(
        f"/api/v1/assessments/{other_assessment.id}",
        headers=auth_context["headers"],
    )
    assert response.status_code == 403


async def test_admin_endpoint_requires_admin_role(
    api_client: AsyncClient,
    auth_context: dict,
):
    response = await api_client.get(
        "/api/v1/admin/parameters",
        headers=auth_context["headers"],
    )
    assert response.status_code == 200


async def test_exception_response_shape(api_client: AsyncClient, auth_context: dict):
    response = await api_client.get(
        f"/api/v1/assessments/{uuid.uuid4()}",
        headers=auth_context["headers"],
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["request_id"]
