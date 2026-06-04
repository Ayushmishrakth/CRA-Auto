from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, decode_access_token
from app.db.models.assessment import Assessment
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.audit_log import AuditLog
from app.db.models.user_session import UserSession
from app.main import app


PROTECTED_PATHS = [
    "/api/v1/tenants",
    "/api/v1/assessments/start",
    "/api/v1/admin/parameters",
]


async def test_route_architecture_has_no_duplicate_method_conflicts():
    seen = set()
    duplicates = []
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        for method in methods:
            key = (method, path)
            if key in seen:
                duplicates.append(key)
            seen.add(key)

    assert duplicates == []


async def test_openapi_security_and_tags(api_client: AsyncClient):
    response = await api_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    tags = {tag for path in schema["paths"].values() for op in path.values() for tag in op.get("tags", [])}
    assert {"Authentication", "Tenants", "Assessments", "Reports", "Admin", "Health"}.issubset(tags)


async def test_protected_routes_reject_missing_jwt(api_client: AsyncClient):
    for path in PROTECTED_PATHS:
        method = "post" if path.endswith("/start") else "get"
        if method == "post":
            response = await api_client.post(path, json={"tenant_id": "x"})
        else:
            response = await api_client.get(path)
        assert response.status_code in {401, 403}
        assert response.json()["success"] is False
        assert response.json()["request_id"]


async def test_invalid_malformed_and_expired_jwt_rejected(
    api_client: AsyncClient,
    auth_context: dict,
):
    bad_headers = [
        {"Authorization": "Bearer abc"},
        {"Authorization": "Bearer not.a.jwt"},
    ]
    expired = create_access_token(
        sub=str(auth_context["user"].id),
        tid=auth_context["tenant"].tenant_id,
        email=auth_context["user"].email,
        role=auth_context["user"].role,
        connected_tenants=[auth_context["tenant"].tenant_id],
        expires_delta=timedelta(seconds=-1),
    )
    bad_headers.append({"Authorization": f"Bearer {expired}"})

    for headers in bad_headers:
        response = await api_client.get("/api/v1/tenants", headers=headers)
        assert response.status_code == 401
        assert response.json()["success"] is False


async def test_revoked_session_jwt_rejected(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    payload = decode_access_token(auth_context["token"])
    result = await db_session.execute(
        select(UserSession).where(UserSession.jwt_jti == payload["jti"])
    )
    session = result.scalars().one()
    session.revoked_at = datetime.now(timezone.utc)
    await db_session.commit()

    response = await api_client.get("/api/v1/tenants", headers=auth_context["headers"])
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Token has been revoked"


async def test_cross_tenant_findings_and_reports_rejected(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    assessment = Assessment(
        tenant_id="tenant-b",
        triggered_by_user_id=auth_context["user"].id,
        status="queued",
        progress_pct=0,
    )
    db_session.add(assessment)
    await db_session.commit()

    for path in [
        f"/api/v1/assessments/{assessment.id}/findings",
        f"/api/v1/reports/assessments/{assessment.id}",
    ]:
        response = await api_client.get(path, headers=auth_context["headers"])
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_ACCESS_DENIED"


async def test_response_and_middleware_headers(api_client: AsyncClient):
    request_id = str(uuid.uuid4())
    response = await api_client.get("/api/v1/health", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert "X-Process-Time-MS" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    body = response.json()
    assert body["success"] is True
    assert body["request_id"] == request_id
    assert body["timestamp"]


async def test_cors_preflight(api_client: AsyncClient):
    response = await api_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_pagination_limit_offset_and_page(
    api_client: AsyncClient,
    auth_context: dict,
):
    tenant_id = auth_context["tenant"].tenant_id
    headers = auth_context["headers"]
    created_ids = []
    for _ in range(3):
        response = await api_client.post(
            "/api/v1/assessments/start",
            headers=headers,
            json={"tenant_id": tenant_id},
        )
        assert response.status_code == 202
        created_ids.append(response.json()["data"]["id"])

    offset_response = await api_client.get(
        f"/api/v1/tenants/{tenant_id}/assessments?limit=1&offset=1",
        headers=headers,
    )
    page_response = await api_client.get(
        f"/api/v1/tenants/{tenant_id}/assessments?limit=1&page=2",
        headers=headers,
    )
    assert offset_response.status_code == 200
    assert page_response.status_code == 200
    assert len(offset_response.json()["data"]) == 1
    assert offset_response.json()["data"][0]["id"] == page_response.json()["data"][0]["id"]


async def test_service_layer_boundary_no_direct_db_calls_in_api_routes():
    api_dir = Path("app/api/v1")
    violations = {}
    for path in api_dir.glob("*.py"):
        if path.name in {"router.py", "__init__.py"}:
            continue
        text = path.read_text()
        hits = [
            needle
            for needle in ["await db.", "db.execute", "db.add", "db.commit", "db.get"]
            if needle in text
        ]
        if hits:
            violations[str(path)] = hits
    assert violations == {}


async def test_async_architecture_no_sync_sqlalchemy_regression():
    backend_files = list(Path("app").rglob("*.py"))
    forbidden = ["create_engine(", "session.query", "from sqlalchemy.orm import Session"]
    violations = {}
    for path in backend_files:
        text = path.read_text()
        hits = [needle for needle in forbidden if needle in text]
        if re.search(r"^SessionLocal\s*=", text, re.MULTILINE):
            hits.append("SessionLocal =")
        if hits:
            violations[str(path)] = hits
    assert violations == {}


async def test_assessment_creation_is_audited(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    await api_client.post(
        "/api/v1/assessments/start",
        headers=auth_context["headers"],
        json={"tenant_id": auth_context["tenant"].tenant_id},
    )
    events = (await db_session.execute(select(AuditLog.event_type))).scalars().all()
    assert "ASSESSMENT_STARTED" in events


@pytest.mark.xfail(reason="Admin rule updates are not audited yet.")
async def test_admin_operations_are_audited(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    parameter = AssessmentParameter(
        parameter_key="audit_rule_update",
        parameter_name="Audit Rule Update",
        category="security",
        collection_method="graph",
    )
    db_session.add(parameter)
    await db_session.commit()
    response = await api_client.put(
        f"/api/v1/admin/parameters/{parameter.id}/rule",
        headers=auth_context["headers"],
        json={
            "rule_type": "boolean",
            "severity": "high",
            "scoring_weight": 1,
            "copilot_blocking": False,
        },
    )
    assert response.status_code == 200
    events = (await db_session.execute(select(AuditLog.event_type))).scalars().all()
    assert "ADMIN_RULE_UPDATED" in events


@pytest.mark.xfail(reason="/health/system does not include migration status yet.")
async def test_system_health_includes_migration_status(api_client: AsyncClient):
    response = await api_client.get("/api/v1/health/system")
    assert "migration" in response.json()["data"]["components"]


@pytest.mark.xfail(reason="sort_by/search params are accepted but not applied by assessment service yet.")
async def test_sorting_and_search_are_applied(
    api_client: AsyncClient,
    auth_context: dict,
):
    response = await api_client.get(
        f"/api/v1/tenants/{auth_context['tenant'].tenant_id}/assessments?sort_by=created_at&order=asc&search=queued",
        headers=auth_context["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"]["meta"]["sort_by"] == "created_at"
