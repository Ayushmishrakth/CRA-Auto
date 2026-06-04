import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.models.assessment import Assessment
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.assessment_event import AssessmentEvent
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.assessment_report import AssessmentReport
from app.db.models.assessment_rule import AssessmentRule
from app.db.models.audit_log import AuditLog
from app.services.admin_service import reset_tenant_assessment_data


async def _count(db, model, *criteria):
    statement = select(func.count()).select_from(model)
    for condition in criteria:
        statement = statement.where(condition)
    return int(await db.scalar(statement) or 0)


async def _seed_runtime(db, *, tenant_id: str, user_id):
    parameter = AssessmentParameter(
        parameter_key=f"runtime_test_{tenant_id[:8]}",
        parameter_name="Runtime Test",
        category="Test",
        collection_method="powershell",
        is_active=True,
    )
    db.add(parameter)
    await db.flush()
    rule = AssessmentRule(
        parameter_id=parameter.id,
        rule_type="configuration_value_check",
        severity="low",
        scoring_weight=1.0,
        pass_condition={},
    )
    assessment = Assessment(
        tenant_id=tenant_id,
        triggered_by_user_id=user_id,
        status="completed",
        progress_pct=100,
        total_findings=1,
    )
    db.add_all([rule, assessment])
    await db.flush()
    job = AssessmentJob(
        tenant_id=tenant_id,
        assessment_id=assessment.id,
        status="completed",
        progress_pct=100,
        completed_at=datetime.now(timezone.utc),
    )
    finding = AssessmentFinding(
        assessment_id=assessment.id,
        parameter_id=parameter.id,
        status="pass",
        raw_value={"value": 1},
        severity="low",
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc),
    )
    recommendation = AssessmentRecommendation(
        tenant_id=tenant_id,
        assessment_id=assessment.id,
        parameter_key=parameter.parameter_key,
        severity="low",
        title="Runtime Test",
        recommendation_text="No action.",
    )
    artifact = AssessmentArtifact(
        tenant_id=tenant_id,
        assessment_id=assessment.id,
        job_id=job.id,
        parameter_key=parameter.parameter_key,
        artifact_type="collector_execution",
        status="collected",
    )
    event = AssessmentEvent(
        tenant_id=tenant_id,
        assessment_id=assessment.id,
        event_type="assessment.completed",
        severity="info",
        event_payload={},
    )
    report = AssessmentReport(
        assessment_id=assessment.id,
        report_type="pdf",
        report_status="generated",
        storage_path=f"storage/reports/{assessment.id}/report.pdf",
    )
    assessment_log = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="ASSESSMENT_COMPLETED",
        action="assessment.completed",
        resource="assessments",
    )
    login_log = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="LOGIN_SUCCESS",
        action="auth.login",
        resource="users",
    )
    db.add_all([job, finding, recommendation, artifact, event, report, assessment_log, login_log])
    await db.commit()
    return assessment, parameter


async def test_reset_tenant_assessment_data_removes_only_selected_runtime_rows(
    db_session,
    auth_context,
):
    target_tenant = auth_context["tenant"].tenant_id
    other_tenant = str(uuid.uuid4())
    user_id = auth_context["user"].id

    target_assessment, target_parameter = await _seed_runtime(
        db_session,
        tenant_id=target_tenant,
        user_id=user_id,
    )
    other_assessment, _ = await _seed_runtime(
        db_session,
        tenant_id=other_tenant,
        user_id=user_id,
    )

    result = await reset_tenant_assessment_data(db_session, tenant_id=target_tenant)

    assert result["tenant_id"] == target_tenant
    assert result["status"] == "success"
    assert result["assessments_deleted"] == 1
    assert result["findings_deleted"] == 1
    assert result["recommendations_deleted"] == 1
    assert result["artifacts_deleted"] == 1
    assert result["reports_deleted"] == 1
    assert result["jobs_deleted"] == 1
    assert result["events_deleted"] == 1
    assert result["assessment_audit_logs_deleted"] == 1

    assert await _count(db_session, Assessment, Assessment.tenant_id == target_tenant) == 0
    assert await _count(db_session, AssessmentFinding, AssessmentFinding.assessment_id == target_assessment.id) == 0
    assert await _count(db_session, AssessmentRecommendation, AssessmentRecommendation.tenant_id == target_tenant) == 0
    assert await _count(db_session, AssessmentArtifact, AssessmentArtifact.tenant_id == target_tenant) == 0
    assert await _count(db_session, AssessmentReport, AssessmentReport.assessment_id == target_assessment.id) == 0
    assert await _count(db_session, AssessmentJob, AssessmentJob.tenant_id == target_tenant) == 0
    assert await _count(db_session, AssessmentEvent, AssessmentEvent.tenant_id == target_tenant) == 0
    assert await _count(db_session, AuditLog, AuditLog.tenant_id == target_tenant, AuditLog.action == "assessment.completed") == 0
    assert await _count(db_session, AuditLog, AuditLog.tenant_id == target_tenant, AuditLog.action == "auth.login") == 1

    assert await _count(db_session, Assessment, Assessment.id == other_assessment.id) == 1
    assert await _count(db_session, AuditLog, AuditLog.tenant_id == other_tenant, AuditLog.action == "assessment.completed") == 1
    assert await _count(db_session, AssessmentParameter, AssessmentParameter.id == target_parameter.id) == 1
    assert await _count(db_session, AssessmentRule) == 2
