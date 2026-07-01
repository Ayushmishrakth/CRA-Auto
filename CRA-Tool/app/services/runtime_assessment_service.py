"""
Phase 7 assessment runtime orchestration.

Phase 7B keeps the lifecycle intact and swaps collector execution to the
PowerShell runtime. Microsoft Graph collectors plug into this lifecycle later.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
import traceback
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.assessment import Assessment
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.assessment_rule import AssessmentRule
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User
from app.db.session import AsyncSessionLocal
from app.services.audit_service import AuditEvent, audit_service
from app.services.event_bus import emit_event
from app.services.exchange_token_service import get_exchange_access_token
from app.services.graph_cra_collector_service import GRAPH_COLLECTORS
from app.services.powershell import PowerShellExecutionEngine
from app.services.registry_service import get_registry
from app.services.runtime_recommendation_service import calculate_priority_score, generate_recommendations
from app.services.runtime_scoring_service import apply_scores
from app.services.tenant_secret_service import decrypt_client_secret
from app.utils.logger import logger


RUNTIME_STAGES = {
    "starting": ("starting", 3.0),
    "collecting": ("collecting", 8.0),
    "evaluating": ("evaluating", 82.0),
    "scoring": ("scoring", 90.0),
    "recommendations": ("generating_recommendations", 95.0),
    "completed": ("completed", 100.0),
}

POWERSHELL_REQUIRED_PARAMETERS: set[str] = {
    # Entra controls where the manual finding is based on Microsoft Graph
    # PowerShell report/policy output rather than the app-only Graph fallback.
    "user_consent_for_applications",

    # Exchange controls whose manual source is Exchange Online PowerShell.
    "customer_lockbox",
    "external_storage_providers_in_owa",
    "full_calendar_schedules_able_to_be_shared_externally",

    # Teams governance controls exposed through Teams PowerShell, not app-only
    # Microsoft Graph.
    "guest_access_enabled_disabled",
    "meeting_recording_retention_policies",
    "teams_channel_email_addresses",
    "teams_file_storage_option",
    "teams_lobby_bypass",

    # SharePoint tenant settings where Graph beta omits the exact manual fields.
    "days_to_retain_a_deleted_user_s_onedrive",
    "expiration_policy_for_anyone_links",
    "permission_setting_for_anyone_links",
    "sharepoint_and_onedrive_guest_access_expiry",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _runtime_log(message: str, **context: Any) -> None:
    logger.info("[ASSESSMENT] %s %s", message, context)


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _collector_failure_details(
    *,
    collector_result: dict[str, Any] | None = None,
    error: str | None = None,
    exception: Exception | None = None,
) -> dict[str, Any]:
    telemetry = (collector_result or {}).get("telemetry") or {}
    raw_value = (collector_result or {}).get("raw_value") or {}
    contract = raw_value.get("collector_contract") if isinstance(raw_value, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    errors = (collector_result or {}).get("errors") or contract.get("errors") or []
    collector_error = error or "; ".join(str(item) for item in errors if item) or None
    exception_message = str(exception) if exception is not None else collector_error
    raw_response = raw_value.get("raw_response") if isinstance(raw_value, dict) else None
    graph_error = None
    if isinstance(raw_response, dict):
        graph_error = raw_response.get("graph_error") or raw_response.get("error")

    return {
        "collector_error": collector_error,
        "exception_type": type(exception).__name__ if exception is not None else None,
        "exception_message": exception_message,
        "powershell_output": {
            "stdout": telemetry.get("stdout") or telemetry.get("stdout_preview"),
            "stderr": telemetry.get("stderr"),
            "exit_code": telemetry.get("exit_code"),
            "attempts": telemetry.get("attempts"),
        },
        "graph_error": graph_error,
    }


def _non_empty_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message or type(exc).__name__


def _collector_debug_payload(
    *,
    parameter_key: str,
    collector: dict[str, Any],
    runtime_name: str,
    progress: float,
    manifest_entry: dict[str, Any] | None = None,
    collector_result: dict[str, Any] | None = None,
    exception: Exception | None = None,
) -> dict[str, Any]:
    telemetry = (collector_result or {}).get("telemetry") or {}
    raw_value = (collector_result or {}).get("raw_value") or {}
    contract = raw_value.get("collector_contract") if isinstance(raw_value, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    errors = (collector_result or {}).get("errors") or contract.get("errors") or []
    return {
        "parameter_key": parameter_key,
        "collector": collector.get("collector_name"),
        "runtime": runtime_name,
        "script_path": telemetry.get("source_script") or (manifest_entry or {}).get("script"),
        "command": collector.get("powershell_script"),
        "stdout": telemetry.get("stdout") or telemetry.get("stdout_preview"),
        "stderr": telemetry.get("stderr"),
        "exit_code": telemetry.get("exit_code"),
        "attempts": telemetry.get("attempts"),
        "retries": telemetry.get("retries"),
        "duration_ms": telemetry.get("duration_ms"),
        "generated_files": telemetry.get("generated_files") or contract.get("metrics", {}).get("generated_files"),
        "errors": errors,
        "exception_type": type(exception).__name__ if exception is not None else None,
        "exception_message": _non_empty_error_message(exception) if exception is not None else None,
        "stack_trace": traceback.format_exception(type(exception), exception, exception.__traceback__)[-8:]
        if exception is not None
        else None,
        "progress_pct": progress,
    }


def _short_ref(parameter: dict[str, Any]) -> str | None:
    source_refs = parameter.get("source_refs") or []
    if not source_refs:
        return None
    source = source_refs[0]
    sheet = str(source.get("sheet") or "")[:18]
    row = source.get("row") or ""
    return f"{sheet}:{row}"[:50]


def _pass_threshold(rule: dict[str, Any]) -> str | None:
    expression = rule.get("expression") or {}
    thresholds = expression.get("percentage_thresholds") or expression.get("count_thresholds")
    if thresholds:
        return ",".join(str(item) for item in thresholds)[:255]
    criteria = expression.get("pass_criteria")
    return str(criteria)[:255] if criteria else None


def _runtime_parameters(parameters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run the approved registry list; each parameter chooses Graph or PowerShell at execution time."""

    return parameters


def _select_runtime(
    *,
    parameter_key: str,
    manifest_entry: dict[str, Any] | None,
) -> str:
    """Choose the collector runtime from the canonical collector manifest."""

    manifest_entry = manifest_entry or {}
    supports_powershell = bool(manifest_entry.get("supports_powershell"))
    supports_graph = bool(manifest_entry.get("supports_graph"))
    if parameter_key in POWERSHELL_REQUIRED_PARAMETERS and supports_powershell:
        return "powershell"
    if parameter_key in GRAPH_COLLECTORS:
        return "graph"
    if supports_powershell and not supports_graph:
        return "powershell"
    if supports_powershell:
        return "powershell"
    return "graph"


async def ensure_registry_seeded(
    db: AsyncSession,
) -> tuple[dict[str, AssessmentParameter], dict[str, AssessmentRule]]:
    """Materialize runtime registry rows required by persisted findings."""

    registry = get_registry()
    parameters = registry.get_parameters()
    parameter_keys = [item["parameter_key"] for item in parameters]

    all_existing_parameters = (
        await db.execute(select(AssessmentParameter))
    ).scalars().all()
    for db_parameter in all_existing_parameters:
        should_be_active = db_parameter.parameter_key in parameter_keys
        if db_parameter.is_active != should_be_active:
            db_parameter.is_active = should_be_active

    existing_parameters = (
        await db.execute(
            select(AssessmentParameter).where(
                AssessmentParameter.parameter_key.in_(parameter_keys)
            )
        )
    ).scalars().all()
    parameter_by_key = {item.parameter_key: item for item in existing_parameters}

    for parameter in parameters:
        key = parameter["parameter_key"]
        if key in parameter_by_key:
            db_parameter = parameter_by_key[key]
            collector = registry.get_collector_by_key(key) or {}
            db_parameter.parameter_name = parameter.get("display_name") or key
            db_parameter.category = parameter.get("category") or parameter.get("domain") or "unclassified"
            db_parameter.collection_method = parameter.get("collection_method") or "unknown"
            db_parameter.collector_module = (
                collector.get("collector_name")
                or f"powershell.{parameter.get('collector_type') or 'unknown'}"
            )
            db_parameter.graph_endpoint = parameter.get("graph_endpoint") or None
            db_parameter.copilot_relevance = parameter.get("copilot_relevance") or None
            db_parameter.excel_row_reference = _short_ref(parameter)
            db_parameter.is_active = True
            continue
        collector = registry.get_collector_by_key(key) or {}
        db_parameter = AssessmentParameter(
            parameter_key=key,
            parameter_name=parameter.get("display_name") or key,
            category=parameter.get("category") or parameter.get("domain") or "unclassified",
            collection_method=parameter.get("collection_method") or "unknown",
            collector_module=collector.get("collector_name")
            or f"powershell.{parameter.get('collector_type') or 'unknown'}",
            graph_endpoint=parameter.get("graph_endpoint") or None,
            copilot_relevance=parameter.get("copilot_relevance") or None,
            is_active=True,
            excel_row_reference=_short_ref(parameter),
        )
        db.add(db_parameter)
        parameter_by_key[key] = db_parameter

    await db.flush()

    parameter_ids = [item.id for item in parameter_by_key.values()]
    existing_rules = (
        await db.execute(
            select(AssessmentRule).where(AssessmentRule.parameter_id.in_(parameter_ids))
        )
    ).scalars().all()
    rule_by_parameter_id = {item.parameter_id: item for item in existing_rules}
    rule_by_key: dict[str, AssessmentRule] = {}

    for parameter in parameters:
        key = parameter["parameter_key"]
        db_parameter = parameter_by_key[key]
        existing_rule = rule_by_parameter_id.get(db_parameter.id)
        registry_rule = registry.get_rule_by_key(key) or {}
        expression = registry_rule.get("expression") or {}
        if existing_rule is not None:
            existing_rule.rule_type = registry_rule.get("rule_type") or "configuration_value_check"
            existing_rule.pass_threshold = _pass_threshold(registry_rule)
            existing_rule.warning_threshold = str(expression.get("warning_threshold") or "")[:255] or None
            existing_rule.pass_condition = expression
            existing_rule.severity = registry_rule.get("severity") or parameter.get("severity") or "info"
            existing_rule.scoring_weight = float(registry_rule.get("scoring_weight") or 1.0)
            existing_rule.copilot_blocking = bool(
                registry_rule.get("copilot_blocking")
                if "copilot_blocking" in registry_rule
                else parameter.get("copilot_blocker")
            )
            rule_by_key[key] = existing_rule
            continue

        db_rule = AssessmentRule(
            parameter_id=db_parameter.id,
            rule_type=registry_rule.get("rule_type") or "configuration_value_check",
            pass_threshold=_pass_threshold(registry_rule),
            warning_threshold=str(expression.get("warning_threshold") or "")[:255] or None,
            pass_condition=expression,
            severity=registry_rule.get("severity") or parameter.get("severity") or "info",
            scoring_weight=float(registry_rule.get("scoring_weight") or 1.0),
            copilot_blocking=bool(
                registry_rule.get("copilot_blocking")
                if "copilot_blocking" in registry_rule
                else parameter.get("copilot_blocker")
            ),
        )
        db.add(db_rule)
        rule_by_key[key] = db_rule

    await db.flush()
    return parameter_by_key, rule_by_key


def _reconciled_collector_result(
    *,
    parameter_key: str,
    parameter: dict[str, Any],
    status: str,
    evaluated_value: str,
    collector_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    raw_value = (collector_result or {}).get("raw_value")
    raw_value = raw_value if isinstance(raw_value, dict) else {}
    telemetry = (collector_result or {}).get("telemetry")
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    severity = (
        (collector_result or {}).get("severity")
        or parameter.get("severity")
        or "info"
    )
    expected_value = (
        (collector_result or {}).get("expected_value")
        or raw_value.get("expected_value")
        or parameter.get("pass_criteria")
        or parameter.get("expected_output")
        or "Meets CRA expected configuration"
    )
    actual_value = (
        (collector_result or {}).get("actual_value")
        or raw_value.get("actual_value")
        or raw_value.get("evidence")
        or ("Collector did not return evidence" if status in {"failed_collector", "collection_error"} else "Manual validation required")
    )
    return {
        "parameter_key": parameter_key,
        "status": status,
        "raw_value": {
            **raw_value,
            "parameter_key": parameter_key,
            "status": status,
            "actual_value": actual_value,
            "expected_value": expected_value,
            "evidence": raw_value.get("evidence") or {
                "collection_status": status,
                "reason": error or evaluated_value,
            },
            "reconciled": True,
        },
        "evaluated_value": evaluated_value,
        "severity": severity,
        "score_contribution": 0.0,
        "telemetry": telemetry,
        "errors": (collector_result or {}).get("errors") or ([error] if error else []),
        "warnings": (collector_result or {}).get("warnings") or [],
    }


def _classified_dependency_status(message: str | None) -> str:
    text = str(message or "").lower()
    if any(token in text for token in ["license", "licence", "e5", "premium feature"]):
        return "service_unavailable"
    if any(
        token in text
        for token in [
            "aadsts500014",
            "serviceprincipaldisabled",
            "exchange_unavailable",
            "exchange online is not available",
            "service principal.*disabled",
            "subscriptionnotfound",
        ]
    ):
        return "service_unavailable"
    if any(
        token in text
        for token in [
            "window handle",
            "wam",
            "interactive",
            "device code",
            "persisted context",
            "admin_url is required",
            "required powershell module",
            "timed out",
            "timeout",
        ]
    ):
        return "collection_error"
    if any(token in text for token in ["not supported", "unsupported", "not available through graph"]):
        return "collection_error"
    return "collection_error"


def _canonical_finding_status(status: str | None) -> str:
    normalized = str(status or "fail").lower().replace(" ", "_")
    if normalized == "not_collected":
        return "fail"
    if normalized in {"manual_validation_required", "manual_validation", "evidence_collected"}:
        return "fail"
    if normalized in {"failed", "error", "execution_failed", "collector_failed", "failed_collector"}:
        return "fail"
    if normalized == "collection_error":
        return "fail"
    if normalized in {"licensing_required", "licensing_limitation", "licensing_gap"}:
        return "fail"
    if normalized in {"service_unavailable", "skipped"}:
        return "fail"
    return normalized


async def _load_job(db: AsyncSession, job_id: str | UUID) -> AssessmentJob:
    result = await db.execute(select(AssessmentJob).where(AssessmentJob.id == UUID(str(job_id))))
    job = result.scalars().first()
    if job is None:
        raise RuntimeError(f"Assessment job not found: {job_id}")
    return job


async def _load_assessment(db: AsyncSession, assessment_id: UUID) -> Assessment:
    assessment = await db.get(Assessment, assessment_id)
    if assessment is None:
        raise RuntimeError(f"Assessment not found: {assessment_id}")
    return assessment


async def _set_stage(
    db: AsyncSession,
    *,
    assessment: Assessment,
    job: AssessmentJob,
    status: str,
    stage: str,
    progress: float,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    assessment.status = status
    assessment.progress_pct = progress
    job.status = status
    job.current_stage = stage
    job.progress_pct = progress
    if status == "running" and job.started_at is None:
        job.started_at = _utc_now()
    await emit_event(
        db,
        assessment_id=assessment.id,
        tenant_id=assessment.tenant_id,
        event_type=event_type,
        payload={"stage": stage, "progress_pct": progress, **(payload or {})},
    )
    await db.commit()


async def _persist_finding(
    db: AsyncSession,
    *,
    assessment: Assessment,
    parameter: AssessmentParameter,
    rule: AssessmentRule | None,
    collector_result: dict[str, Any],
) -> AssessmentFinding:
    now = _utc_now()
    finding = AssessmentFinding(
        assessment_id=assessment.id,
        parameter_id=parameter.id,
        rule_id=rule.id if rule else None,
        status=_canonical_finding_status(collector_result["status"]),
        raw_value=collector_result["raw_value"],
        evaluated_value=collector_result["evaluated_value"],
        severity=collector_result["severity"],
        score_contribution=collector_result["score_contribution"],
        collected_at=now,
        evaluated_at=now,
    )
    db.add(finding)
    await db.flush()
    _runtime_log(
        "FINDING_CREATED",
        assessment_id=str(assessment.id),
        parameter_id=str(parameter.id),
        status=finding.status,
        severity=finding.severity,
    )
    return finding


async def _persist_artifact(
    db: AsyncSession,
    *,
    assessment: Assessment,
    job: AssessmentJob,
    parameter_key: str,
    collector: dict[str, Any],
    parameter: dict[str, Any] | None = None,
    collector_result: dict[str, Any] | None = None,
    status: str,
    artifact_type: str = "collector_execution",
    error: str | None = None,
    exception: Exception | None = None,
) -> AssessmentArtifact:
    telemetry = (collector_result or {}).get("telemetry") or {}
    raw_value = (collector_result or {}).get("raw_value") or {}
    contract = raw_value.get("collector_contract") if isinstance(raw_value, dict) else None
    evidence = raw_value.get("evidence") if isinstance(raw_value, dict) else None
    raw_response = raw_value.get("raw_response") if isinstance(raw_value, dict) else None
    collected_at = (
        telemetry.get("collected_at")
        or (raw_value.get("collected_at") if isinstance(raw_value, dict) else None)
    )
    graph_endpoint = (
        telemetry.get("graph_endpoint")
        or (raw_value.get("graph_endpoint") if isinstance(raw_value, dict) else None)
        or collector.get("graph_endpoint")
    )
    actual_value = (
        telemetry.get("actual_value")
        if "actual_value" in telemetry
        else (raw_value.get("actual_value") if isinstance(raw_value, dict) else None)
    )
    expected_value = (
        telemetry.get("expected_value")
        or (raw_value.get("expected_value") if isinstance(raw_value, dict) else None)
    )
    failure_details = _collector_failure_details(
        collector_result=collector_result,
        error=error,
        exception=exception,
    ) if status == "failed" or error or (collector_result or {}).get("errors") else None
    artifact = AssessmentArtifact(
        assessment_id=assessment.id,
        job_id=job.id,
        tenant_id=assessment.tenant_id,
        parameter_key=parameter_key,
        parameter_name=(parameter or {}).get("display_name"),
        service=(parameter or {}).get("technology") or (parameter or {}).get("category") or collector.get("service") or collector.get("collector_type"),
        collector_name=telemetry.get("collector_name") or collector.get("collector_name"),
        graph_endpoint=graph_endpoint,
        artifact_type=artifact_type,
        source_script=telemetry.get("source_script"),
        source_csv=(
            (telemetry.get("generated_files") or [None])[0]
            if isinstance(telemetry.get("generated_files"), list)
            else collector.get("output_file") or None
        ),
        status=status,
        actual_value=actual_value,
        expected_value=expected_value,
        raw_evidence_json={
            "evidence": evidence,
            "raw_response": raw_response,
            **({"failure_details": failure_details} if failure_details else {}),
        } if evidence is not None or raw_response is not None or failure_details else None,
        collection_timestamp=_parse_datetime(collected_at),
        stdout=telemetry.get("stdout") or telemetry.get("stdout_preview"),
        stderr=telemetry.get("stderr") or error,
        payload={
            "collector": collector,
            "result": collector_result,
            "contract": contract,
            "error": error,
            **(failure_details or {}),
        },
    )
    db.add(artifact)
    await db.flush()
    return artifact


def _finding_payload(
    finding: AssessmentFinding,
    parameter: AssessmentParameter,
    collector_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": str(finding.id),
        "assessment_id": str(finding.assessment_id),
        "parameter_id": str(finding.parameter_id),
        "parameter_key": collector_result["parameter_key"],
        "parameter_name": parameter.parameter_name,
        "category": parameter.category,
        "status": finding.status,
        "raw_value": finding.raw_value,
        "evaluated_value": finding.evaluated_value,
        "severity": finding.severity,
        "score_contribution": finding.score_contribution,
        "collected_at": finding.collected_at.isoformat() if finding.collected_at else None,
        "evaluated_at": finding.evaluated_at.isoformat() if finding.evaluated_at else None,
    }


# Parameters that cannot be evaluated app-only until pending admin consent / role
# steps are completed (Teams cert + Teams Administrator role, Exchange Online app
# RBAC, SharePoint/OneDrive PnP cert). Until then their collectors fail or return a
# generic placeholder. The post-collection pass in _collect_findings rewrites those
# generic findings with a specific, actionable message telling the customer exactly
# what to check manually and what to do to enable automation. It is GUARDED (only
# replaces generic "could-not-collect" text — never a real PASS/FAIL from live data).
MANUAL_VERIFICATION_MESSAGES: dict[str, str] = {
    # --- Teams (require Teams PowerShell app-only: cert + Teams Administrator role) ---
    "copilot_integration_enabled": (
        "Copilot integration could not be verified automatically (requires Teams PowerShell "
        "app-only access). Manual check: Teams Admin Center > Teams apps > Manage apps > "
        "search 'Copilot'. To enable automated checking: complete Teams Administrator role "
        "assignment for the CRA app registration."
    ),
    "meeting_policies_configuration": (
        "Meeting policies could not be verified automatically (requires Get-CsTeamsMeetingPolicy "
        "via Teams PowerShell). Expected: AllowCloudRecording and AllowTranscription both enabled. "
        "Manual check: Teams Admin Center > Meetings > Meeting policies > Global policy. To enable "
        "automated checking: complete Teams Administrator role assignment."
    ),
    "meeting_transcription_enabled": (
        "Meeting transcription setting could not be verified automatically (requires "
        "Get-CsTeamsMeetingPolicy via Teams PowerShell). Manual check: Teams Admin Center > "
        "Meetings > Meeting policies > Global policy > AllowTranscription. To enable automated "
        "checking: complete Teams Administrator role assignment."
    ),
    "meeting_recording_retention_policies": (
        "Meeting recording retention could not be verified automatically (requires "
        "Get-CsTeamsMeetingPolicy via Teams PowerShell). Manual check: Teams Admin Center > "
        "Meetings > Meeting policies > Global policy > Recording expiration. To enable automated "
        "checking: complete Teams Administrator role assignment."
    ),
    "teams_meeting_chat": (
        "Meeting chat setting could not be verified automatically (requires Get-CsTeamsMeetingPolicy "
        "via Teams PowerShell). Manual check: Teams Admin Center > Meetings > Meeting policies > "
        "Global policy > MeetingChatEnabledType. To enable automated checking: complete Teams "
        "Administrator role assignment."
    ),
    "third_party_apps_allowed": (
        "Third-party app settings could not be verified automatically (requires "
        "Get-CsTeamsClientConfiguration via Teams PowerShell). Manual check: Teams Admin Center > "
        "Teams apps > Manage apps > Org-wide app settings. To enable automated checking: complete "
        "Teams Administrator role assignment."
    ),
    "guest_access_enabled_disabled": (
        "Guest access setting could not be verified automatically (requires "
        "Get-CsTeamsClientConfiguration via Teams PowerShell). Manual check: Teams Admin Center > "
        "Users > Guest access. To enable automated checking: complete Teams Administrator role "
        "assignment."
    ),
    "teams_channel_email_addresses": (
        "Channel email addresses setting could not be verified automatically (requires "
        "Get-CsTeamsClientConfiguration via Teams PowerShell). Manual check: Teams Admin Center > "
        "Teams > Teams settings > Email integration. To enable automated checking: complete Teams "
        "Administrator role assignment."
    ),
    "teams_file_storage_option": (
        "File storage options could not be verified automatically (requires "
        "Get-CsTeamsClientConfiguration via Teams PowerShell). Manual check: Teams Admin Center > "
        "Teams > Teams settings > Files. To enable automated checking: complete Teams Administrator "
        "role assignment."
    ),
    "teams_lobby_bypass": (
        "Lobby bypass setting could not be verified automatically (requires Get-CsTeamsMeetingPolicy "
        "via Teams PowerShell). Manual check: Teams Admin Center > Meetings > Meeting policies > "
        "Global policy > AutoAdmittedUsers. To enable automated checking: complete Teams "
        "Administrator role assignment."
    ),
    # --- Exchange Online (app authenticates but lacks Exchange RBAC role: UnAuthorized) ---
    "customer_lockbox": (
        "Customer Lockbox could not be verified automatically — Exchange Online PowerShell returned "
        "UnAuthorized. The CRA app has Exchange.ManageAsApp consent but is not yet assigned an "
        "Exchange Online admin role. To enable: in Exchange Admin Center > Roles > Admin roles, "
        "assign the CRA app service principal a role with View-Only Configuration (or run "
        "New-ServicePrincipal + Add-RoleGroupMember). Manual check: Microsoft 365 Admin Center > "
        "Settings > Org settings > Security & privacy > Customer Lockbox "
        "(Get-OrganizationConfig | fl CustomerLockBoxEnabled)."
    ),
    "external_storage_providers_in_owa": (
        "External storage providers in OWA could not be verified automatically — Exchange Online "
        "PowerShell returned UnAuthorized. The CRA app has Exchange.ManageAsApp consent but is not "
        "yet assigned an Exchange Online admin role. To enable: assign the CRA app service principal "
        "an Exchange role with View-Only Configuration. Manual check: Exchange Admin Center > Outlook "
        "Web App policies (Get-OwaMailboxPolicy | fl AdditionalStorageProvidersAvailable)."
    ),
    "full_calendar_schedules_able_to_be_shared_externally": (
        "External calendar sharing could not be verified automatically — Exchange Online PowerShell "
        "returned UnAuthorized. The CRA app has Exchange.ManageAsApp consent but is not yet assigned "
        "an Exchange Online admin role. To enable: assign the CRA app service principal an Exchange "
        "role with View-Only Configuration. Manual check: Exchange Admin Center > Organization > "
        "Sharing (Get-SharingPolicy | fl Domains)."
    ),
    # --- SharePoint / OneDrive (require PnP cert app-only: pending consent) ---
    "days_to_retain_a_deleted_user_s_onedrive": (
        "OneDrive deleted user retention period could not be verified automatically. To enable: "
        "complete the SharePoint app-only consent step in the CRA setup. Manual check: SharePoint "
        "Admin Center > Settings > OneDrive retention."
    ),
    "sharepoint_and_onedrive_guest_access_expiry": (
        "SharePoint and OneDrive guest access expiry settings could not be verified automatically. "
        "To enable: complete the SharePoint app-only consent step in the CRA setup. Manual check: "
        "SharePoint Admin Center > Policies > Sharing > Guest access expiry."
    ),
}


async def _collect_findings(
    db: AsyncSession,
    *,
    assessment: Assessment,
    job: AssessmentJob,
) -> list[AssessmentFinding]:
    registry = get_registry()
    powershell_engine = PowerShellExecutionEngine()
    parameter_by_key, rule_by_key = await ensure_registry_seeded(db)
    tenant = await db.scalar(
        select(ConnectedTenant).where(ConnectedTenant.tenant_id == assessment.tenant_id)
    )
    collector_environment: dict[str, str] = {}
    if tenant and tenant.app_client_id and tenant.encrypted_client_secret:
        client_secret = decrypt_client_secret(tenant)
        collector_environment = {
            "CRA_GRAPH_AUTH_MODE": "app",
            "CRA_GRAPH_CLIENT_ID": tenant.app_client_id,
            "CRA_GRAPH_CLIENT_SECRET": client_secret,
            "CRA_TEAMS_AUTH_MODE": "app",
        }
        # Acquire an Exchange Online access token so Exchange PS collectors can use app-only auth.
        # The token is for https://outlook.office365.com/.default via client_credentials.
        # primary_domain is stored in deployment_diagnostics during tenant deployment.
        primary_domain: str | None = (tenant.deployment_diagnostics or {}).get("primary_domain")
        if primary_domain:
            exchange_token = await get_exchange_access_token(tenant.tenant_id, tenant.app_client_id, client_secret)
            if exchange_token:
                collector_environment["CRA_EXCHANGE_AUTH_MODE"] = "app"
                collector_environment["CRA_EXCHANGE_ACCESS_TOKEN"] = exchange_token
                collector_environment["CRA_EXCHANGE_ORGANIZATION"] = primary_domain
            else:
                logger.warning("[ASSESSMENT] Exchange Online token not available for tenant %s — Exchange PS collectors will be skipped", tenant.tenant_id)
        else:
            logger.warning("[ASSESSMENT] primary_domain not found in deployment_diagnostics for tenant %s — Exchange PS collectors will be skipped", tenant.tenant_id)

        # Certificate app-only auth for PnP/SharePoint + Teams collectors.
        # The MicrosoftTeams and PnP.PowerShell modules cannot use client-secret
        # app auth — they require a certificate. Wire the per-tenant cert env vars
        # so Connect-CraPnP / Connect-CraTeams (cra_common.ps1) can load it.
        # .env values are read via pydantic settings (not os.environ), so they
        # must be injected into collector_environment to reach the PS subprocess
        # (powershell_executor merges env={**os.environ, **collector_environment}).
        cert_pfx_path = settings.cra_cert_pfx_path or str(
            Path(__file__).resolve().parents[2] / "secrets" / "cra_cert.pfx"
        )
        cert_pfx_password = settings.cra_cert_pfx_password
        cert_thumbprint = settings.cra_cert_thumbprint
        if cert_thumbprint or os.path.exists(cert_pfx_path):
            collector_environment["CRA_PNP_AUTH_MODE"] = "certificate"
            collector_environment["CRA_PNP_TENANT"] = tenant.tenant_id
            if os.path.exists(cert_pfx_path):
                collector_environment["CRA_CERT_PFX_PATH"] = cert_pfx_path
                if cert_pfx_password:
                    collector_environment["CRA_CERT_PFX_PASSWORD"] = cert_pfx_password
            if cert_thumbprint:
                collector_environment["CRA_CERT_THUMBPRINT"] = cert_thumbprint
        else:
            logger.warning("[ASSESSMENT] No certificate configured (CRA_CERT_PFX_PATH / CRA_CERT_THUMBPRINT) for tenant %s — PnP/Teams certificate collectors will be skipped", tenant.tenant_id)
    await db.execute(delete(AssessmentFinding).where(AssessmentFinding.assessment_id == assessment.id))
    await db.execute(delete(AssessmentArtifact).where(AssessmentArtifact.assessment_id == assessment.id))
    await db.commit()

    parameters = _runtime_parameters(registry.get_parameters())
    findings: list[AssessmentFinding] = []
    telemetry_summary = {
        "collector_runtime": "hybrid_manifest_routed",
        "collector_failures": 0,
        "collector_timeouts": 0,
        "collector_retries": 0,
        "collector_duration_ms": 0,
        "graph_calls": 0,
        "findings_created": 0,
        "scores_created": 0,
        "failures": [],
    }
    total = max(1, len(parameters))

    for index, parameter_config in enumerate(parameters, start=1):
        key = parameter_config["parameter_key"]
        collector = registry.get_collector_by_key(key) or {}
        manifest_entry = powershell_engine.resolver.get_manifest_entry(key) or {}
        runtime_name = _select_runtime(parameter_key=key, manifest_entry=manifest_entry)
        progress = round(8.0 + (index - 1) / total * 74.0, 2)
        assessment.progress_pct = progress
        job.progress_pct = progress
        job.current_stage = "collecting"

        await emit_event(
            db,
            assessment_id=assessment.id,
            tenant_id=assessment.tenant_id,
            event_type="collector.started",
            payload={
                "parameter_key": key,
                "collector": collector.get("collector_name"),
                "collector_type": collector.get("collector_type"),
                "runtime": runtime_name,
                "manifest_service": manifest_entry.get("service"),
                "script": manifest_entry.get("script"),
                "progress_pct": progress,
            },
        )
        await db.commit()

        try:
            if runtime_name == "graph" and key in GRAPH_COLLECTORS:
                if tenant is None:
                    raise RuntimeError("Connected tenant record was not found")
                if not tenant.app_client_id or not tenant.encrypted_client_secret:
                    raise RuntimeError("Connected tenant is missing Graph app credentials")
                collector_result = await GRAPH_COLLECTORS[key](tenant)
            else:
                collector_result = await powershell_engine.run_collector(
                    tenant_id=assessment.tenant_id,
                    parameter=parameter_config,
                    collector=collector,
                    assessment_id=str(assessment.id),
                    environment=collector_environment,
                )
            telemetry = collector_result.get("telemetry") or {}
            telemetry_summary["graph_calls"] += int(telemetry.get("graph_calls") or 0)
            telemetry_summary["collector_retries"] += int(telemetry.get("retries") or 0)
            telemetry_summary["collector_duration_ms"] += int(telemetry.get("duration_ms") or 0)
            if telemetry.get("timed_out"):
                telemetry_summary["collector_timeouts"] += 1
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="collector.timeout",
                    severity="warning",
                    payload={
                        "parameter_key": key,
                        "collector": collector.get("collector_name"),
                        "timeout_count": telemetry.get("timeout_count", 1),
                        "duration_ms": telemetry.get("duration_ms"),
                        "progress_pct": progress,
                    },
                )
            if telemetry.get("stdout_preview"):
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="collector.stdout",
                    payload={
                        "parameter_key": key,
                        "collector": collector.get("collector_name"),
                        "stdout_preview": telemetry.get("stdout_preview"),
                        "duration_ms": telemetry.get("duration_ms"),
                        "attempts": telemetry.get("attempts"),
                        "progress_pct": progress,
                    },
                )
            for warning in collector_result.get("warnings") or []:
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="collector.warning",
                    severity="warning",
                    payload={
                        "parameter_key": key,
                        "collector": collector.get("collector_name"),
                        "warning": str(warning),
                        "progress_pct": progress,
                    },
                )
            if collector_result.get("errors"):
                telemetry_summary["collector_failures"] += 1
                error_message = "; ".join(str(item) for item in collector_result.get("errors") or [])
                await _persist_artifact(
                    db,
                    assessment=assessment,
                    job=job,
                    parameter_key=key,
                    collector=collector,
                    parameter=parameter_config,
                    collector_result=collector_result,
                    status="failed",
                )
                db_parameter = parameter_by_key[key]
                db_rule = rule_by_key.get(key)
                _dep_status = _classified_dependency_status(error_message)
                reconciled_result = _reconciled_collector_result(
                    parameter_key=key,
                    parameter=parameter_config,
                    status=_dep_status,
                    evaluated_value=(
                        "Service is not available in the tenant — this is a readiness gap."
                        if _dep_status == "service_unavailable"
                        else "Collector failed before producing validated CRA evidence."
                    ),
                    collector_result=collector_result,
                )
                finding = await _persist_finding(
                    db,
                    assessment=assessment,
                    parameter=db_parameter,
                    rule=db_rule,
                    collector_result=reconciled_result,
                )
                findings.append(finding)
                telemetry_summary["findings_created"] += 1
                debug_payload = _collector_debug_payload(
                    parameter_key=key,
                    collector=collector,
                    runtime_name=runtime_name,
                    progress=progress,
                    manifest_entry=manifest_entry,
                    collector_result=collector_result,
                )
                _runtime_log("COLLECTOR_FAILURE_DEBUG", **debug_payload)
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="collector.failure_debug",
                    severity="warning",
                    payload=debug_payload,
                )
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="collector.failed",
                    severity="warning",
                    payload={
                        "parameter_key": key,
                        "collector": collector.get("collector_name"),
                        "errors": collector_result.get("errors"),
                        "stderr": telemetry.get("stderr"),
                        "exit_code": telemetry.get("exit_code"),
                        "attempts": telemetry.get("attempts"),
                        "retries": telemetry.get("retries"),
                        "duration_ms": telemetry.get("duration_ms"),
                        "progress_pct": progress,
                        "finding_generated": True,
                    },
                )
                await db.commit()
                continue
            if collector_result.get("status") == "skipped":
                await _persist_artifact(
                    db,
                    assessment=assessment,
                    job=job,
                    parameter_key=key,
                    collector=collector,
                    parameter=parameter_config,
                    collector_result=collector_result,
                    status="skipped",
                )
                db_parameter = parameter_by_key[key]
                db_rule = rule_by_key.get(key)
                finding = await _persist_finding(
                    db,
                    assessment=assessment,
                    parameter=db_parameter,
                    rule=db_rule,
                    collector_result=collector_result,
                )
                findings.append(finding)
                telemetry_summary["findings_created"] += 1
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="collector.skipped",
                    payload={
                        "parameter_key": key,
                        "collector": collector.get("collector_name"),
                        "reason": (collector_result.get("warnings") or ["Service unavailable"])[0],
                        "progress_pct": progress,
                    },
                )
                await db.commit()
                continue
            if collector_result.get("status") == "not_collected":
                telemetry_summary["collector_failures"] += 1
                await _persist_artifact(
                    db,
                    assessment=assessment,
                    job=job,
                    parameter_key=key,
                    collector=collector,
                    parameter=parameter_config,
                    collector_result=collector_result,
                    status="evidence_collected",
                )
                db_parameter = parameter_by_key[key]
                db_rule = rule_by_key.get(key)
                reconciled_result = _reconciled_collector_result(
                    parameter_key=key,
                    parameter=parameter_config,
                    status="not_collected",
                    evaluated_value="No automated API is available for this control — not included in scoring.",
                    collector_result=collector_result,
                )
                finding = await _persist_finding(
                    db,
                    assessment=assessment,
                    parameter=db_parameter,
                    rule=db_rule,
                    collector_result=reconciled_result,
                )
                findings.append(finding)
                telemetry_summary["findings_created"] += 1
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="csv.detected",
                    payload={
                        "parameter_key": key,
                        "collector": collector.get("collector_name"),
                        "generated_files": (
                            collector_result.get("raw_value", {})
                            .get("collector_contract", {})
                            .get("metrics", {})
                            .get("generated_files", [])
                        ),
                        "finding_generated": True,
                        "progress_pct": progress,
                    },
                )
                await db.commit()
                continue
            await _persist_artifact(
                db,
                assessment=assessment,
                job=job,
                parameter_key=key,
                collector=collector,
                parameter=parameter_config,
                collector_result=collector_result,
                status="collected",
            )
            db_parameter = parameter_by_key[key]
            db_rule = rule_by_key.get(key)
            finding = await _persist_finding(
                db,
                assessment=assessment,
                parameter=db_parameter,
                rule=db_rule,
                collector_result=collector_result,
            )
            findings.append(finding)
            telemetry_summary["findings_created"] += 1

            finding_payload = _finding_payload(finding, db_parameter, collector_result)
            progress = round(8.0 + index / total * 74.0, 2)
            assessment.progress_pct = progress
            job.progress_pct = progress
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="finding.generated",
                severity=finding.severity or "info",
                payload={"finding": finding_payload, "progress_pct": progress},
            )
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="collector.completed",
                payload={
                    "parameter_key": key,
                    "collector": collector.get("collector_name"),
                    "status": collector_result["status"],
                    "runtime": runtime_name,
                    "duration_ms": telemetry.get("duration_ms"),
                    "attempts": telemetry.get("attempts"),
                    "retries": telemetry.get("retries"),
                    "exit_code": telemetry.get("exit_code"),
                    "progress_pct": progress,
                },
            )
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="progress.update",
                payload={"progress_pct": progress, "stage": "collecting"},
            )
            await db.commit()
        except Exception as exc:
            error_message = _non_empty_error_message(exc)
            telemetry_summary["collector_failures"] += 1
            telemetry_summary["failures"].append({"parameter_key": key, "error": error_message})
            await _persist_artifact(
                db,
                assessment=assessment,
                job=job,
                parameter_key=key,
                collector=collector,
                parameter=parameter_config,
                status="failed",
                error=error_message,
                exception=exc,
            )
            db_parameter = parameter_by_key[key]
            db_rule = rule_by_key.get(key)
            _exc_dep_status = _classified_dependency_status(error_message)
            reconciled_result = _reconciled_collector_result(
                parameter_key=key,
                parameter=parameter_config,
                status=_exc_dep_status,
                evaluated_value=(
                    "Service is not available in the tenant — this is a readiness gap."
                    if _exc_dep_status == "service_unavailable"
                    else "Collector execution raised an exception before producing validated CRA evidence."
                ),
                error=error_message,
            )
            finding = await _persist_finding(
                db,
                assessment=assessment,
                parameter=db_parameter,
                rule=db_rule,
                collector_result=reconciled_result,
            )
            findings.append(finding)
            telemetry_summary["findings_created"] += 1
            debug_payload = _collector_debug_payload(
                parameter_key=key,
                collector=collector,
                runtime_name=runtime_name,
                progress=progress,
                manifest_entry=manifest_entry,
                exception=exc,
            )
            _runtime_log("COLLECTOR_FAILURE_DEBUG", **debug_payload)
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="collector.failure_debug",
                severity="warning",
                payload=debug_payload,
            )
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="collector.failed",
                severity="warning",
                payload={
                    "parameter_key": key,
                    "collector": collector.get("collector_name"),
                    "error": error_message,
                    "exception_type": type(exc).__name__,
                    "progress_pct": progress,
                },
            )
            await db.commit()

    # Rewrite generic "could-not-collect" findings with specific, actionable
    # manual-verification guidance (see MANUAL_VERIFICATION_MESSAGES). Guarded: only
    # applied when the collector did NOT produce real data, so a real PASS/FAIL result
    # (e.g. once Teams/Exchange/SharePoint app-only auth is enabled) is never overwritten.
    _id_to_key = {getattr(p, "id", None): k for k, p in parameter_by_key.items()}
    _generic_markers = (
        "collector failed before producing validated cra evidence",
        "not verifiable via graph",
        "cannot be read via graph",
        "not exposed via app-only",
        "powershell is not available",
        "manual verification required",
        "treat as not configured",
        "service is not available in the tenant",
    )
    _rewrote = 0
    for _finding in findings:
        _key = _id_to_key.get(getattr(_finding, "parameter_id", None))
        _msg = MANUAL_VERIFICATION_MESSAGES.get(_key or "")
        if not _msg or getattr(_finding, "status", "") == "pass":
            continue
        _current = (getattr(_finding, "evaluated_value", "") or "").strip().lower()
        if (not _current) or any(marker in _current for marker in _generic_markers):
            _finding.evaluated_value = _msg
            _rewrote += 1
    if _rewrote:
        _runtime_log("MANUAL_VERIFICATION_MESSAGES_APPLIED", count=_rewrote)
        await db.commit()

    job.metadata_payload = {
        **(job.metadata_payload or {}),
        **telemetry_summary,
        "collector_total": len(parameters),
        "collector_collected": len(findings),
        "collector_incomplete": telemetry_summary["collector_failures"]
        + telemetry_summary["collector_timeouts"],
    }
    await db.commit()
    return findings


async def run_assessment_job(job_id: str, *, worker_id: str | None = None) -> dict[str, Any]:
    """Execute a queued assessment job end to end."""

    async with AsyncSessionLocal() as db:
        job = await _load_job(db, job_id)
        assessment = await _load_assessment(db, job.assessment_id)
        job.worker_id = worker_id
        job.error_message = None
        job.metadata_payload = {
            **(job.metadata_payload or {}),
            "runtime": "phase7b_powershell",
            "worker_id": worker_id,
        }

        try:
            await _set_stage(
                db,
                assessment=assessment,
                job=job,
                status="running",
                stage=RUNTIME_STAGES["starting"][0],
                progress=RUNTIME_STAGES["starting"][1],
                event_type="assessment.started",
                payload={"job_id": str(job.id), "worker_id": worker_id},
            )
            await _set_stage(
                db,
                assessment=assessment,
                job=job,
                status="running",
                stage=RUNTIME_STAGES["collecting"][0],
                progress=RUNTIME_STAGES["collecting"][1],
                event_type="progress.update",
            )

            findings = await _collect_findings(db, assessment=assessment, job=job)
            incomplete_count = int((job.metadata_payload or {}).get("collector_incomplete") or 0)
            if incomplete_count:
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="assessment.collectors_incomplete",
                    severity="warning",
                    payload={
                        "job_id": str(job.id),
                        "collector_total": (job.metadata_payload or {}).get("collector_total"),
                        "collector_collected": len(findings),
                        "collector_incomplete": incomplete_count,
                        "progress_pct": assessment.progress_pct,
                        "completion_policy": "continue_to_scoring",
                    },
                )
                await audit_service.log_event(
                    db,
                    tenant_id=assessment.tenant_id,
                    event=AuditEvent.ASSESSMENT_STARTED,
                    action="assessment.collectors_incomplete",
                    user_id=assessment.triggered_by_user_id,
                    resource="assessments",
                    metadata={
                        "assessment_id": str(assessment.id),
                        "job_id": str(job.id),
                        "collector_incomplete": incomplete_count,
                    },
                )
                await db.commit()

            await _set_stage(
                db,
                assessment=assessment,
                job=job,
                status="running",
                stage=RUNTIME_STAGES["evaluating"][0],
                progress=RUNTIME_STAGES["evaluating"][1],
                event_type="progress.update",
            )
            await _set_stage(
                db,
                assessment=assessment,
                job=job,
                status="running",
                stage=RUNTIME_STAGES["scoring"][0],
                progress=RUNTIME_STAGES["scoring"][1],
                event_type="progress.update",
            )
            scores = apply_scores(assessment, findings)
            job.metadata_payload = {
                **(job.metadata_payload or {}),
                "scores_created": 1,
            }
            _runtime_log(
                "SCORE_CREATED",
                assessment_id=str(assessment.id),
                overall_score=scores.get("overall_score"),
                finding_count=len(findings),
            )
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="scoring.completed",
                payload={"scores": scores, "progress_pct": RUNTIME_STAGES["scoring"][1]},
            )
            await db.commit()

            await _set_stage(
                db,
                assessment=assessment,
                job=job,
                status="running",
                stage=RUNTIME_STAGES["recommendations"][0],
                progress=RUNTIME_STAGES["recommendations"][1],
                event_type="progress.update",
            )
            recommendations = await generate_recommendations(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                findings=findings,
            )
            for recommendation in recommendations:
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="recommendation.generated",
                    severity=recommendation.severity,
                    payload={
                        "recommendation": {
                            "id": str(recommendation.id),
                            "assessment_id": str(recommendation.assessment_id),
                            "parameter_key": recommendation.parameter_key,
                            "severity": recommendation.severity,
                            "title": recommendation.title,
                            "recommendation_text": recommendation.recommendation_text,
                            "remediation_steps": recommendation.remediation_steps,
                            "effort": recommendation.effort,
                            "impact": recommendation.impact,
                            "priority_score": calculate_priority_score(
                                severity=recommendation.severity,
                                effort=recommendation.effort,
                                copilot_impact=recommendation.impact,
                            ),
                        },
                        "progress_pct": RUNTIME_STAGES["recommendations"][1],
                    },
                )
            await db.commit()

            report_payload = None
            report_user = await db.get(User, assessment.triggered_by_user_id)
            if report_user is None:
                raise RuntimeError("Assessment report generation failed: triggering user was not found")
            from app.services.reporting import cra_report_service

            report_payload = await cra_report_service.generate_report_bundle(
                assessment_id=assessment.id,
                db=db,
                current_user=report_user,
            )
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="report.generated",
                payload={
                    "assessment_id": str(assessment.id),
                    "artifact_count": len(report_payload.get("artifacts") or []),
                    "progress_pct": 98.0,
                },
            )
            await db.commit()

            assessment.status = "completed"
            assessment.progress_pct = RUNTIME_STAGES["completed"][1]
            job.status = "completed"
            job.current_stage = RUNTIME_STAGES["completed"][0]
            job.progress_pct = RUNTIME_STAGES["completed"][1]
            job.completed_at = _utc_now()
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="assessment.completed",
                payload={
                    "assessment": {
                        "id": str(assessment.id),
                        "tenant_id": assessment.tenant_id,
                        "status": assessment.status,
                        "progress_pct": assessment.progress_pct,
                        "overall_score": assessment.overall_score,
                        "identity_score": assessment.identity_score,
                        "security_score": assessment.security_score,
                        "compliance_score": assessment.compliance_score,
                        "collaboration_score": assessment.collaboration_score,
                        "licensing_score": assessment.licensing_score,
                        "total_findings": assessment.total_findings,
                        "critical_findings": assessment.critical_findings,
                        "high_findings": assessment.high_findings,
                    },
                    "job_id": str(job.id),
                    "progress_pct": RUNTIME_STAGES["completed"][1],
                },
            )
            await audit_service.log_event(
                db,
                tenant_id=assessment.tenant_id,
                event=AuditEvent.ASSESSMENT_COMPLETED,
                action="assessment.completed",
                user_id=assessment.triggered_by_user_id,
                resource="assessments",
                metadata={"assessment_id": str(assessment.id), "job_id": str(job.id)},
            )
            await db.commit()
            return {
                "assessment_id": str(assessment.id),
                "job_id": str(job.id),
                "status": assessment.status,
                "progress_pct": assessment.progress_pct,
                "findings": len(findings),
                "recommendations": len(recommendations),
            }
        except (asyncio.CancelledError, GeneratorExit):
            logger.warning(
                f"Assessment task cancelled/interrupted: job_id={job_id} assessment_id={assessment.id if 'assessment' in locals() else 'unknown'}"
            )
            try:
                await db.rollback()
                job = await _load_job(db, job_id)
                assessment = await _load_assessment(db, job.assessment_id)
                assessment.status = "failed"
                job.status = "failed"
                job.current_stage = "failed"
                job.error_message = "Assessment interrupted — server restarted or task cancelled"
                job.completed_at = _utc_now()
                await emit_event(
                    db,
                    assessment_id=assessment.id,
                    tenant_id=assessment.tenant_id,
                    event_type="assessment.failed",
                    severity="error",
                    payload={"error": "Task cancelled", "job_id": str(job.id)},
                )
                await db.commit()
            except Exception as cleanup_err:
                logger.error(f"Failed to mark assessment as failed after cancellation: {cleanup_err}")
            raise
        except Exception as exc:
            await db.rollback()
            job = await _load_job(db, job_id)
            assessment = await _load_assessment(db, job.assessment_id)
            now = _utc_now()
            assessment.status = "failed"
            job.status = "failed"
            job.current_stage = "failed"
            job.error_message = str(exc)
            job.completed_at = now
            await emit_event(
                db,
                assessment_id=assessment.id,
                tenant_id=assessment.tenant_id,
                event_type="assessment.failed",
                severity="error",
                payload={"error": str(exc), "job_id": str(job.id)},
            )
            await audit_service.log_event(
                db,
                tenant_id=assessment.tenant_id,
                event=AuditEvent.ASSESSMENT_FAILED,
                action="assessment.failed",
                user_id=assessment.triggered_by_user_id,
                resource="assessments",
                metadata={
                    "assessment_id": str(assessment.id),
                    "job_id": str(job.id),
                    "error": str(exc),
                },
            )
            await db.commit()
            return {
                "assessment_id": str(assessment.id),
                "job_id": str(job.id),
                "status": "failed",
                "error": str(exc),
            }
