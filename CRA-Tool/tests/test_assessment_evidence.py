from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import Assessment
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.services import graph_cra_collector_service


class FakeGraphClient:
    async def get(self, path, *, params=None):
        if path == "/users":
            return {
                "value": [
                    {
                        "id": "user-1",
                        "displayName": "Member One",
                        "userPrincipalName": "member@example.com",
                        "mail": "member@example.com",
                        "userType": "Member",
                        "accountEnabled": True,
                    },
                    {
                        "id": "guest-1",
                        "displayName": "Guest One",
                        "userPrincipalName": "guest_example.com#EXT#@tenant.onmicrosoft.com",
                        "mail": "guest@example.com",
                        "userType": "Guest",
                        "accountEnabled": True,
                    },
                ]
            }
        raise AssertionError(f"Unexpected Graph path: {path}")


async def test_guest_users_count_collector_uses_real_graph_response(monkeypatch):
    tenant = type("Tenant", (), {"tenant_id": "tenant-id"})()

    async def fake_graph_client(_tenant):
        return FakeGraphClient()

    monkeypatch.setattr(graph_cra_collector_service, "_graph_client", fake_graph_client)

    result = await graph_cra_collector_service.collect_guest_users_count(tenant)

    assert result["parameter_key"] == "guest_users_count"
    assert result["status"] == "fail"
    assert result["raw_value"]["actual_value"]["guest_count"] == 1
    assert result["raw_value"]["actual_value"]["total_users"] == 2
    assert result["raw_value"]["evidence"]["guests"][0]["displayName"] == "Guest One"


async def test_assessment_evidence_endpoint_returns_persisted_artifact_and_finding(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    tenant_id = auth_context["tenant"].tenant_id
    assessment = Assessment(
        tenant_id=tenant_id,
        triggered_by_user_id=auth_context["user"].id,
        status="completed",
        progress_pct=100,
        overall_score=59,
    )
    parameter = AssessmentParameter(
        parameter_key="global_administrator_accounts",
        parameter_name="Global Administrator Accounts",
        category="Entra ID",
        collection_method="graph",
        collector_module="graph.global_administrator_accounts",
        graph_endpoint="/directoryRoles/{id}/members",
        is_active=True,
    )
    db_session.add_all([assessment, parameter])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    finding = AssessmentFinding(
        assessment_id=assessment.id,
        parameter_id=parameter.id,
        status="pass",
        raw_value={
            "parameter_key": "global_administrator_accounts",
            "actual_value": 3,
            "expected_value": "2-5 Global Administrator accounts",
            "evidence": {"members": [{"displayName": "Admin One"}]},
            "graph_endpoint": "/directoryRoles/{id}/members",
        },
        evaluated_value="3 Global Administrator account(s) found",
        severity="info",
        score_contribution=0,
        collected_at=now,
        evaluated_at=now,
    )
    artifact = AssessmentArtifact(
        assessment_id=assessment.id,
        tenant_id=tenant_id,
        parameter_key="global_administrator_accounts",
        parameter_name="Global Administrator Accounts",
        service="Entra ID",
        collector_name="graph.global_administrator_accounts",
        graph_endpoint="/directoryRoles/{id}/members",
        artifact_type="collector_execution",
        status="collected",
        actual_value=3,
        expected_value="2-5 Global Administrator accounts",
        raw_evidence_json={"evidence": {"members": [{"displayName": "Admin One"}]}},
        collection_timestamp=now,
        payload={"result": {"status": "pass"}},
    )
    recommendation = AssessmentRecommendation(
        assessment_id=assessment.id,
        tenant_id=tenant_id,
        parameter_key="global_administrator_accounts",
        severity="info",
        title="Maintain Global Administrator Accounts",
        recommendation_text="Maintain the current administrator count.",
        remediation_steps=[],
        effort="low",
        impact="low",
    )
    db_session.add_all([finding, artifact, recommendation])
    await db_session.commit()

    response = await api_client.get(
        f"/api/v1/assessments/{assessment.id}/evidence",
        headers=auth_context["headers"],
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["coverage"]["collected"] == 1
    row = next(item for item in data["parameters"] if item["parameter_key"] == "global_administrator_accounts")
    assert row["status"] == "PASS"
    assert row["actual_value"] == 3
    assert row["artifact_id"] is None
    assert row["collector"] is None
    assert row["evidence"]["members"][0]["displayName"] == "Admin One"
    assert row["recommendation"]["recommendation_text"] == "Maintain the current administrator count."


async def test_assessment_evidence_surfaces_failed_artifact_without_finding(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    tenant_id = auth_context["tenant"].tenant_id
    assessment = Assessment(
        tenant_id=tenant_id,
        triggered_by_user_id=auth_context["user"].id,
        status="completed",
        progress_pct=100,
        overall_score=59,
    )
    db_session.add(assessment)
    await db_session.flush()

    artifact = AssessmentArtifact(
        assessment_id=assessment.id,
        tenant_id=tenant_id,
        parameter_key="external_storage_providers_in_owa",
        parameter_name="External Storage Providers in OWA",
        service="Exchange Online",
        collector_name="powershell.external_storage_providers_in_owa",
        artifact_type="collector_execution",
        status="failed",
        stderr="ExchangeOnlineManagement module missing",
        raw_evidence_json={
            "failure_details": {
                "collector_error": "ExchangeOnlineManagement module missing",
                "exception_type": "RuntimeError",
                "exception_message": "ExchangeOnlineManagement module missing",
                "powershell_output": {
                    "stdout": "",
                    "stderr": "ExchangeOnlineManagement module missing",
                    "exit_code": None,
                },
                "graph_error": None,
            }
        },
        payload={
            "collector_error": "ExchangeOnlineManagement module missing",
            "exception_type": "RuntimeError",
            "exception_message": "ExchangeOnlineManagement module missing",
            "powershell_output": {
                "stdout": "",
                "stderr": "ExchangeOnlineManagement module missing",
                "exit_code": None,
            },
            "graph_error": None,
        },
    )
    db_session.add(artifact)
    await db_session.commit()

    response = await api_client.get(
        f"/api/v1/assessments/{assessment.id}/evidence",
        headers=auth_context["headers"],
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["coverage"]["failed"] == 1
    row = next(item for item in data["parameters"] if item["parameter_key"] == "external_storage_providers_in_owa")
    assert row["status"] == "FAILED"
    assert row["failure_reason"] == "ExchangeOnlineManagement module missing"
    assert row["failure_details"]["exception_type"] == "RuntimeError"

    failures_response = await api_client.get(
        f"/api/v1/assessment-failures/{assessment.id}",
        headers=auth_context["headers"],
    )

    assert failures_response.status_code == 200
    failures = failures_response.json()["data"]
    assert failures == [
        {
            "parameter": "external_storage_providers_in_owa",
            "collector": None,
            "status": "FAILED",
            "error": "ExchangeOnlineManagement module missing",
        }
    ]
