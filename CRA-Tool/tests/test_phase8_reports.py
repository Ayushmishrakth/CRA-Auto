import uuid
from pathlib import Path
from zipfile import ZipFile

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.assessment_report import AssessmentReport
from app.services.reporting import cra_report_service


async def _create_completed_assessment(db: AsyncSession, auth_context: dict) -> Assessment:
    assessment = Assessment(
        tenant_id=auth_context["tenant"].tenant_id,
        triggered_by_user_id=auth_context["user"].id,
        status="completed",
        progress_pct=100,
        overall_score=72.5,
        security_score=70,
        compliance_score=76,
        collaboration_score=74,
        identity_score=68,
        licensing_score=90,
        total_findings=2,
        critical_findings=1,
        high_findings=1,
    )
    db.add(assessment)
    await db.flush()

    parameter = AssessmentParameter(
        parameter_key="users_without_mfa",
        parameter_name="Users without MFA",
        category="Security",
        collection_method="powershell",
        collector_module="powershell.users_without_mfa",
        copilot_relevance="MFA protects Copilot access from account compromise.",
        is_active=True,
    )
    db.add(parameter)
    await db.flush()

    db.add(
        AssessmentFinding(
            assessment_id=assessment.id,
            parameter_id=parameter.id,
            status="fail",
            raw_value={"parameter_key": "users_without_mfa", "evidence": {"users": 4}},
            evaluated_value="Four capable users do not have MFA registration.",
            severity="critical",
            score_contribution=5,
        )
    )
    db.add(
        AssessmentRecommendation(
            assessment_id=assessment.id,
            tenant_id=assessment.tenant_id,
            parameter_key="users_without_mfa",
            severity="critical",
            title="Enforce MFA registration",
            recommendation_text="Require MFA registration for all capable users before Copilot rollout.",
            remediation_steps=["Enable registration campaign", "Review authentication methods"],
            effort="medium",
            impact="Reduces unauthorized Copilot access risk.",
        )
    )
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def test_phase8_report_service_generates_pdf_docx_and_metadata(
    db_session: AsyncSession,
    auth_context: dict,
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(cra_report_service, "REPORT_ROOT", tmp_path)
    assessment = await _create_completed_assessment(db_session, auth_context)

    payload = await cra_report_service.generate_report_bundle(
        db_session,
        current_user=auth_context["user"],
        assessment_id=assessment.id,
    )

    assert payload["status"] == "generated"
    assert len(payload["artifacts"]) == 2
    paths = {item["report_type"]: Path(item["storage_path"]) for item in payload["artifacts"]}
    pdf_bytes = paths["pdf"].read_bytes()
    assert pdf_bytes.startswith(b"%PDF")
    assert b"Copilot Readiness Assessment" in pdf_bytes
    with ZipFile(paths["docx"]) as docx:
        assert "word/document.xml" in docx.namelist()

    stored = (
        await db_session.execute(
            select(AssessmentReport).where(AssessmentReport.assessment_id == assessment.id)
        )
    ).scalars().all()
    assert {item.report_type for item in stored} == {"pdf", "docx"}


async def test_phase8_report_api_status_generate_and_download(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(cra_report_service, "REPORT_ROOT", tmp_path)
    assessment = await _create_completed_assessment(db_session, auth_context)

    status_response = await api_client.get(
        f"/api/v1/assessments/{assessment.id}/report",
        headers=auth_context["headers"],
    )
    assert status_response.status_code == 200
    assert status_response.json()["data"]["download_ready"] is False

    generate_response = await api_client.post(
        f"/api/v1/assessments/{assessment.id}/generate-report",
        headers=auth_context["headers"],
    )
    assert generate_response.status_code == 200
    assert generate_response.json()["data"]["status"] == "generated"

    for report_type, content_type in [
        ("pdf", "application/pdf"),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ]:
        download = await api_client.get(
            f"/api/v1/assessments/{assessment.id}/report/download?report_type={report_type}",
            headers=auth_context["headers"],
        )
        assert download.status_code == 200
        assert content_type in download.headers["content-type"]
        assert len(download.content) > 100


async def test_phase8_report_endpoints_are_tenant_scoped(
    api_client: AsyncClient,
    db_session: AsyncSession,
    auth_context: dict,
):
    other = Assessment(
        tenant_id="tenant-b",
        triggered_by_user_id=auth_context["user"].id,
        status="completed",
        progress_pct=100,
    )
    db_session.add(other)
    await db_session.commit()

    for method, path in [
        ("get", f"/api/v1/assessments/{other.id}/report"),
        ("post", f"/api/v1/assessments/{other.id}/generate-report"),
        ("get", f"/api/v1/assessments/{other.id}/report/download"),
    ]:
        response = await getattr(api_client, method)(path, headers=auth_context["headers"])
        assert response.status_code == 403
