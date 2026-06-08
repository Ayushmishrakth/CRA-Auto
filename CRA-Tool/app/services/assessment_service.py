"""
Assessment orchestration-ready business logic.
"""

import asyncio
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import BusinessLogicException, NotFoundException, TenantAccessException
from app.core.pagination import PaginationParams
from app.db.models.assessment import Assessment
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.assessment_event import AssessmentEvent
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob
from app.db.models.tenant import ConnectedTenant
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.user import User
from app.db.repositories.base_repository import TenantScopedRepository
from app.schemas.assessment import AssessmentStartRequest
from app.schemas.assessment_schema import AssessmentSummaryResponse
from app.services.audit_service import AuditEvent, audit_service
from app.services.graph_cra_collector_service import GRAPH_COLLECTORS
from app.services.runtime_recommendation_service import calculate_priority_score
from app.services.registry_service import get_registry
from app.services.runtime_assessment_service import run_assessment_job
from app.tasks.assessment_tasks import run_assessment_task

assessment_repository = TenantScopedRepository(Assessment)


SERVICE_LABELS = {
    "entra": "Entra ID",
    "exchange": "Exchange Online",
    "purview": "Microsoft Purview",
    "teams": "Microsoft Teams",
    "onedrive": "OneDrive",
    "sharepoint": "SharePoint Online",
    "licensing": "Licensing",
    "m365": "Microsoft 365",
}


def get_assessment_summary() -> AssessmentSummaryResponse:
    return AssessmentSummaryResponse(
        message="Assessment module ready for Phase 6 workflow implementation",
        module="assessment",
    )


def _assert_user_tenant(current_user: User, tenant_id: str) -> None:
    if current_user.microsoft_tid != tenant_id:
        raise TenantAccessException("Tenant is not available to the current user")


async def start_assessment(
    db: AsyncSession,
    *,
    current_user: User,
    payload: AssessmentStartRequest,
) -> Assessment:
    _assert_user_tenant(current_user, payload.tenant_id)
    result = await db.execute(select(ConnectedTenant).where(ConnectedTenant.tenant_id == payload.tenant_id))
    tenant = result.scalars().first()
    if tenant is None or tenant.status != "ACTIVE":
        raise BusinessLogicException(
            "CRA Access must be deployed and ACTIVE before starting an assessment",
            details={
                "tenant_id": payload.tenant_id,
                "tenant_status": tenant.status if tenant else "NOT_DEPLOYED",
            },
        )
    assessment = await assessment_repository.create_for_tenant(
        db,
        tenant_id=payload.tenant_id,
        obj_in={
            "triggered_by_user_id": current_user.id,
            "status": "queued",
            "progress_pct": 0.0,
        },
    )
    job = AssessmentJob(
        assessment_id=assessment.id,
        tenant_id=payload.tenant_id,
        status="queued",
        current_stage="queued",
        progress_pct=0.0,
        metadata_payload={"runtime": "phase7b_powershell", "enqueue_status": "pending"},
    )
    db.add(job)
    await db.flush()
    await audit_service.log_event(
        db,
        tenant_id=payload.tenant_id,
        event=AuditEvent.ASSESSMENT_STARTED,
        action="assessment.started",
        user_id=current_user.id,
        resource="assessments",
        metadata={"assessment_id": str(assessment.id), "job_id": str(job.id)},
        commit=True,
    )
    api_background_job_id: str | None = None
    if settings.celery_task_always_eager:
        job.metadata_payload = {
            **(job.metadata_payload or {}),
            "enqueue_status": "api_background",
            "worker_mode": "celery_eager_bypassed",
        }
        api_background_job_id = str(job.id)
    else:
        try:
            queued_task = run_assessment_task.apply_async(args=[str(job.id)], retry=False)
            job.metadata_payload = {
                **(job.metadata_payload or {}),
                "enqueue_status": "queued",
                "celery_task_id": queued_task.id,
            }
        except Exception as exc:
            job.metadata_payload = {
                **(job.metadata_payload or {}),
                "enqueue_status": "failed",
                "enqueue_error": str(exc),
            }
    await db.commit()
    if api_background_job_id:
        asyncio.create_task(run_assessment_job(api_background_job_id, worker_id="api-background"))
    await db.refresh(assessment)
    await db.refresh(job)
    assessment.job_id = job.id
    return assessment


async def get_assessment(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> Assessment:
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalars().first()
    if assessment is None:
        raise NotFoundException("Assessment not found")
    _assert_user_tenant(current_user, assessment.tenant_id)
    return assessment


async def list_tenant_assessments(
    db: AsyncSession,
    *,
    current_user: User,
    tenant_id: str,
    pagination: PaginationParams,
) -> list[Assessment]:
    _assert_user_tenant(current_user, tenant_id)
    return await assessment_repository.get_all_for_tenant(
        db,
        tenant_id=tenant_id,
        skip=pagination.resolved_offset,
        limit=pagination.limit,
    )


async def get_findings(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
    pagination: PaginationParams,
) -> list[AssessmentFinding]:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentFinding)
        .options(selectinload(AssessmentFinding.parameter))
        .where(AssessmentFinding.assessment_id == assessment.id)
        .offset(pagination.resolved_offset)
        .limit(pagination.limit)
    )
    return list(result.scalars().all())


async def get_events(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
    pagination: PaginationParams,
) -> list[AssessmentEvent]:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentEvent)
        .where(
            AssessmentEvent.assessment_id == assessment.id,
            AssessmentEvent.tenant_id == assessment.tenant_id,
        )
        .order_by(AssessmentEvent.created_at.desc())
        .offset(pagination.resolved_offset)
        .limit(pagination.limit)
    )
    return list(result.scalars().all())


async def get_job(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> AssessmentJob:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentJob)
        .where(
            AssessmentJob.assessment_id == assessment.id,
            AssessmentJob.tenant_id == assessment.tenant_id,
        )
        .order_by(AssessmentJob.created_at.desc())
        .limit(1)
    )
    job = result.scalars().first()
    if job is None:
        raise NotFoundException("Assessment job not found")
    return job


async def get_score(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    return {
        "assessment_id": assessment.id,
        "overall_score": assessment.overall_score,
        "categories": {
            "identity": assessment.identity_score,
            "security": assessment.security_score,
            "compliance": assessment.compliance_score,
            "collaboration": assessment.collaboration_score,
            "licensing": assessment.licensing_score,
        },
        "status": assessment.status,
    }


async def get_readiness_breakdown(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentFinding)
        .options(selectinload(AssessmentFinding.parameter))
        .where(AssessmentFinding.assessment_id == assessment.id)
    )
    findings = list(result.scalars().all())
    buckets = {
        "identity": {"score": assessment.identity_score, "total": 0, "pass": 0, "fail": 0, "warning": 0},
        "security": {"score": assessment.security_score, "total": 0, "pass": 0, "fail": 0, "warning": 0},
        "licensing": {"score": assessment.licensing_score, "total": 0, "pass": 0, "fail": 0, "warning": 0},
        "collaboration": {"score": assessment.collaboration_score, "total": 0, "pass": 0, "fail": 0, "warning": 0},
        "adoption": {"score": None, "total": 0, "pass": 0, "fail": 0, "warning": 0},
        "teams": {"score": None, "total": 0, "pass": 0, "fail": 0, "warning": 0},
    }
    adoption_keys = {
        "mailboxes_status_active_inactive",
        "mailbox_storage_usage",
        "number_of_emails_read_received",
        "number_of_emails_sent",
        "active_inactive_teams",
        "activer_inactive_teams_users",
        "active_sites_count",
        "active_users_on_sharepoint",
        "total_active_users_on_onedrive",
    }
    for finding in findings:
        key = (finding.raw_value or {}).get("parameter_key") or ""
        category = (getattr(finding.parameter, "category", "") or "").lower()
        if "license" in key:
            bucket = "licensing"
        elif "entra" in category or "identity" in category or getattr(finding.parameter, "category", "") == "Entra ID":
            bucket = "identity"
        elif "teams" in category or "teams" in key or "meeting" in key or key in {"minimum_number_of_owners", "orphan_teams", "third_party_apps_allowed", "guest_access_enabled_disabled", "copilot_integration_enabled"}:
            bucket = "teams"
        elif key in adoption_keys:
            bucket = "adoption"
        elif any(token in category for token in ["exchange", "sharepoint", "onedrive", "collaboration"]):
            bucket = "collaboration"
        else:
            bucket = "security"
        status = (finding.status or "warning").lower()
        buckets[bucket]["total"] += 1
        if status in {"pass", "fail", "warning"}:
            buckets[bucket][status] += 1
        if bucket in {"adoption", "teams"}:
            buckets["collaboration"]["total"] += 1
            if status in {"pass", "fail", "warning"}:
                buckets["collaboration"][status] += 1
    for bucket_name in ["adoption", "teams"]:
        bucket = buckets[bucket_name]
        bucket["score"] = round(bucket["pass"] / bucket["total"] * 100, 2) if bucket["total"] else None
    return {
        "assessment_id": assessment.id,
        "status": assessment.status,
        "overall_score": assessment.overall_score,
        "identity_readiness": buckets["identity"],
        "security_readiness": buckets["security"],
        "licensing_readiness": buckets["licensing"],
        "collaboration_readiness": buckets["collaboration"],
        "adoption_readiness": buckets["adoption"],
        "teams_readiness": buckets["teams"],
    }


async def get_recommendations(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentRecommendation)
        .where(
            AssessmentRecommendation.assessment_id == assessment.id,
            AssessmentRecommendation.tenant_id == assessment.tenant_id,
        )
        .order_by(AssessmentRecommendation.created_at.desc())
    )
    recommendations = result.scalars().all()
    return {
        "assessment_id": assessment.id,
        "recommendations": [
            {
                "id": item.id,
                "assessment_id": item.assessment_id,
                "parameter_key": item.parameter_key,
                "severity": item.severity,
                "title": item.title,
                "recommendation_text": item.recommendation_text,
                "remediation_steps": item.remediation_steps,
                "effort": item.effort,
                "impact": item.impact,
                "priority_score": calculate_priority_score(
                    severity=item.severity,
                    effort=item.effort,
                    copilot_impact=item.impact,
                ),
                "created_at": item.created_at,
            }
            for item in recommendations
        ],
    }


def _service_for_parameter(parameter_key: str, parameter: dict) -> str:
    technology = parameter.get("technology")
    if technology:
        if technology == "Teams":
            return "Microsoft Teams"
        if technology == "SharePoint":
            return "SharePoint Online"
        return str(technology)
    text = f"{parameter_key} {parameter.get('category') or ''} {parameter.get('domain') or ''}".lower()
    if any(token in text for token in ["entra", "mfa", "identity", "admin", "guest_users", "consent", "password"]):
        return "Entra ID"
    if any(token in text for token in ["exchange", "mailbox", "email", "calendar", "owa"]):
        return "Exchange Online"
    if any(token in text for token in ["purview", "audit", "dlp", "secure_score", "sensitivity", "retention", "lockbox"]):
        return "Microsoft Purview"
    if "teams" in text or "meeting" in text or "channel" in text:
        return "Microsoft Teams"
    if "onedrive" in text:
        return "OneDrive"
    if "sharepoint" in text or "site" in text or "sharing" in text:
        return "SharePoint Online"
    return "Microsoft 365"


def _status_label(status: str | None) -> str:
    if not status:
        return "NOT_COLLECTED"
    normalized = status.upper().replace(" ", "_")
    if normalized in {"COLLECTED", "SUCCESS"}:
        return "PASS"
    if normalized in {"FAILED", "ERROR", "EXECUTION_FAILED"}:
        return "FAILED"
    if normalized in {"FAILED_COLLECTOR", "COLLECTOR_FAILED"}:
        return "COLLECTION_ERROR"
    if normalized in {"COLLECTION_ERROR", "COLLECTION_FAILED"}:
        return "COLLECTION_ERROR"
    if normalized in {"LICENSING_REQUIRED", "LICENSING_LIMITATION", "LICENSING_GAP"}:
        return "FAIL"
    if normalized in {"MANUAL_VALIDATION", "MANUAL_VALIDATION_REQUIRED", "EVIDENCE_COLLECTED"}:
        return "FAIL"
    if normalized == "NOT_COLLECTED":
        return "NOT_COLLECTED"
    if normalized in {"NOT_SUPPORTED", "POWERSHELL_REQUIRED", "GRAPH_LIMITATION"}:
        return "COLLECTION_ERROR"
    if normalized in {"SERVICE_UNAVAILABLE", "SKIPPED"}:
        return "FAIL"
    return normalized


def _collector_status(
    artifact: AssessmentArtifact | None,
    finding: AssessmentFinding | None,
) -> str:
    if finding is not None:
        return _status_label(finding.status)
    if artifact is not None:
        payload = artifact.payload if isinstance(artifact.payload, dict) else {}
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        if artifact.status and artifact.status.lower() == "failed":
            return "FAILED"
        result_status = result.get("status")
        if result_status:
            return _status_label(result_status)
        return _status_label(artifact.status)
    return "NOT_COLLECTED"


def _failure_details(artifact: AssessmentArtifact | None) -> dict:
    if artifact is None:
        return {}
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    raw_evidence = artifact.raw_evidence_json if isinstance(artifact.raw_evidence_json, dict) else {}
    nested = raw_evidence.get("failure_details") if isinstance(raw_evidence.get("failure_details"), dict) else {}
    details = {**nested, **payload}
    return {
        "collector_error": details.get("collector_error") or details.get("error") or artifact.stderr,
        "exception_type": details.get("exception_type"),
        "exception_message": details.get("exception_message") or details.get("error") or artifact.stderr,
        "graph_error": (
            {
                "code": details["graph_error"].get("code"),
                "message": details["graph_error"].get("message"),
            }
            if isinstance(details.get("graph_error"), dict)
            else None
        ),
    }


def _failure_reason(
    artifact: AssessmentArtifact | None,
    finding: AssessmentFinding | None,
    status: str,
) -> str | None:
    if status != "FAILED":
        raw = finding.raw_value if finding else {}
        if isinstance(raw, dict):
            evidence = raw.get("evidence")
            if isinstance(evidence, dict):
                return evidence.get("collection_status") or evidence.get("reason")
        return None
    details = _failure_details(artifact)
    graph_error = details.get("graph_error")
    if isinstance(graph_error, dict):
        return graph_error.get("message") or graph_error.get("code")
    return (
        details.get("collector_error")
        or details.get("exception_message")
        or (artifact.stderr if artifact else None)
        or "Collector execution failed"
    )


def _collection_method(parameter: dict, collector: dict, artifact: AssessmentArtifact | None) -> str:
    if artifact and artifact.source_script:
        return "PowerShell"
    if artifact and artifact.graph_endpoint:
        return "Microsoft Graph"
    return (
        "Microsoft Graph" if parameter.get("graph_endpoint") else
        "PowerShell" if parameter.get("powershell_mapping") else
        "Automated"
    )


def _evidence_source(artifact: AssessmentArtifact | None, collector: dict) -> str | None:
    if artifact is None:
        return None
    if artifact.graph_endpoint:
        return "Microsoft Graph"
    if artifact.source_csv or artifact.source_script:
        return "PowerShell"
    return "Collector"


def _recommendation_payload(item: AssessmentRecommendation | None) -> dict | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "parameter_key": item.parameter_key,
        "severity": item.severity,
        "title": item.title,
        "recommendation_text": item.recommendation_text,
        "remediation_steps": item.remediation_steps,
        "effort": item.effort,
        "impact": item.impact,
        "priority_score": calculate_priority_score(
            severity=item.severity,
            effort=item.effort,
            copilot_impact=item.impact,
        ),
        "created_at": item.created_at,
    }


def _expected_value(parameter: dict, artifact: AssessmentArtifact | None, finding: AssessmentFinding | None) -> str | None:
    if artifact and artifact.expected_value:
        return artifact.expected_value
    raw = finding.raw_value if finding else {}
    if isinstance(raw, dict) and raw.get("expected_value"):
        return str(raw["expected_value"])
    pass_criteria = parameter.get("pass_criteria")
    return str(pass_criteria) if pass_criteria else None


def _actual_value(artifact: AssessmentArtifact | None, finding: AssessmentFinding | None):
    if artifact and artifact.actual_value is not None:
        return artifact.actual_value
    raw = finding.raw_value if finding else {}
    if isinstance(raw, dict):
        if "actual_value" in raw:
            return raw["actual_value"]
        evidence = raw.get("evidence")
        if isinstance(evidence, dict):
            for key in ["admin_count", "guest_count", "enabled_percent", "complete_users"]:
                if key in evidence:
                    return evidence[key]
    return None


def _evidence_json(artifact: AssessmentArtifact | None, finding: AssessmentFinding | None):
    if artifact and artifact.raw_evidence_json is not None:
        if not isinstance(artifact.raw_evidence_json, dict):
            return artifact.raw_evidence_json
        return artifact.raw_evidence_json.get("evidence") or {
            key: value
            for key, value in artifact.raw_evidence_json.items()
            if key not in {"raw_response", "graph_endpoint", "collector_contract", "failure_details"}
        }
    raw = finding.raw_value if finding else {}
    if isinstance(raw, dict):
        return {
            "evidence": raw.get("evidence"),
        }
    return None


async def get_evidence(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    registry = get_registry()

    finding_result = await db.execute(
        select(AssessmentFinding)
        .options(selectinload(AssessmentFinding.parameter))
        .where(AssessmentFinding.assessment_id == assessment.id)
    )
    findings = list(finding_result.scalars().all())
    finding_by_key = {finding.parameter_key: finding for finding in findings if finding.parameter_key}

    artifact_result = await db.execute(
        select(AssessmentArtifact)
        .where(
            AssessmentArtifact.assessment_id == assessment.id,
            AssessmentArtifact.tenant_id == assessment.tenant_id,
        )
        .order_by(AssessmentArtifact.created_at.asc())
    )
    artifacts = list(artifact_result.scalars().all())
    artifact_by_key = {artifact.parameter_key: artifact for artifact in artifacts}

    recommendation_result = await db.execute(
        select(AssessmentRecommendation).where(
            AssessmentRecommendation.assessment_id == assessment.id,
            AssessmentRecommendation.tenant_id == assessment.tenant_id,
        )
    )
    recommendations = list(recommendation_result.scalars().all())
    recommendation_by_key = {item.parameter_key: item for item in recommendations}

    parameters = []
    collected = 0
    failed = 0
    collection_error = 0
    licensing_required = 0
    manual_validation = 0
    not_collected = 0
    for parameter in registry.get_parameters():
        key = parameter["parameter_key"]
        collector = registry.get_collector_by_key(key) or {}
        finding = finding_by_key.get(key)
        artifact = artifact_by_key.get(key)
        status = _collector_status(artifact, finding)
        if status in {"PASS", "FAIL", "WARNING"}:
            collected += 1
        elif status in {"FAILED", "FAILED_COLLECTOR", "COLLECTION_ERROR"}:
            failed += 1
            if status == "COLLECTION_ERROR":
                collection_error += 1
        elif status == "NOT_COLLECTED":
            not_collected += 1
        else:
            # Legacy statuses (licensing_required, manual_validation) now map to FAIL above,
            # but count any unexpected status as collected to avoid coverage gaps.
            collected += 1
        reason = "Finding and artifact exist." if finding and artifact else (
            "Finding exists; collector artifact row is missing." if finding else (
                f"Artifact exists with status={artifact.status}; no finding was created." if artifact else
                "No finding row and no artifact row exist for this parameter in this assessment."
            )
        )
        failure_reason = _failure_reason(artifact, finding, status)
        parameters.append({
            "parameter_key": key,
            "parameter_name": parameter.get("display_name") or key,
            "service": _service_for_parameter(key, parameter),
            "collector": None,
            "status": status,
            "collector_status": status,
            "failure_reason": failure_reason,
            "collection_method": _collection_method(parameter, collector, artifact),
            "evidence_source": _evidence_source(artifact, collector),
            "severity": (
                finding.severity if finding and finding.severity else parameter.get("severity")
            ),
            "actual_value": _actual_value(artifact, finding),
            "expected_value": _expected_value(parameter, artifact, finding),
            "finding": finding.evaluated_value if finding else None,
            "recommendation": _recommendation_payload(recommendation_by_key.get(key)),
            "evidence": _evidence_json(artifact, finding),
            "artifact_json": None,
            "artifact_id": None,
            "collected_at": (
                artifact.collection_timestamp
                if artifact and artifact.collection_timestamp
                else finding.collected_at if finding else None
            ),
            "reason": reason,
            "failure_details": _failure_details(artifact) if status in {"FAILED", "COLLECTION_ERROR"} else None,
        })

    total = len(parameters)
    implemented_collectors = sum(
        1
        for parameter in registry.get_parameters()
        if parameter["parameter_key"] in GRAPH_COLLECTORS
        or registry.get_collector_by_key(parameter["parameter_key"])
    )
    return {
        "assessment_id": assessment.id,
        "tenant_id": assessment.tenant_id,
        "coverage": {
            "total_parameters": total,
            "implemented_collectors": implemented_collectors,
            "collected": collected,
            "failed": failed,
            "collection_error": collection_error,
            "licensing_required": licensing_required,
            "manual_validation": manual_validation,
            "not_collected": not_collected,
            "coverage_percent": round((collected / total * 100), 2) if total else 0.0,
        },
        "parameters": parameters,
    }


async def get_assessment_failures(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> list[dict]:
    evidence = await get_evidence(db, current_user=current_user, assessment_id=assessment_id)
    failures = []
    for item in evidence["parameters"]:
        if item["status"] not in {"FAILED", "COLLECTION_ERROR", "LICENSING_REQUIRED", "MANUAL_VALIDATION_REQUIRED"}:
            continue
        failures.append({
            "parameter": item["parameter_key"],
            "collector": None,
            "status": item["status"],
            "error": item.get("failure_reason") or item.get("reason"),
        })
    return failures


async def get_latest_assessment_debug(
    db: AsyncSession,
    *,
    current_user: User,
) -> dict:
    result = await db.execute(
        select(AssessmentJob)
        .where(AssessmentJob.tenant_id == current_user.microsoft_tid)
        .order_by(AssessmentJob.created_at.desc())
        .limit(1)
    )
    job = result.scalars().first()
    if job is None:
        return {
            "collectors_run": 0,
            "findings_created": 0,
            "scores_created": 0,
            "graph_calls": 0,
            "failures": [],
        }
    metadata = job.metadata_payload or {}
    findings_created = int(metadata.get("findings_created") or 0)
    scores_created = int(metadata.get("scores_created") or 0)
    if not findings_created:
        findings_created = int(
            await db.scalar(
                select(func.count())
                .select_from(AssessmentFinding)
                .where(AssessmentFinding.assessment_id == job.assessment_id)
            )
            or 0
        )
    if not scores_created:
        assessment = await db.get(Assessment, job.assessment_id)
        scores_created = 1 if assessment and assessment.overall_score is not None else 0
    evidence = await get_evidence(db, current_user=current_user, assessment_id=job.assessment_id)
    return {
        "collectors_run": int(metadata.get("collector_total") or 0),
        "findings_created": findings_created,
        "scores_created": scores_created,
        "graph_calls": int(metadata.get("graph_calls") or 0),
        "failures": metadata.get("failures") or [],
        "coverage": evidence["coverage"],
    }
