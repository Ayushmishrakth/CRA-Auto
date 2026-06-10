from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.assessment_report import AssessmentReport
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User
from app.services.assessment_service import get_assessment
from app.services.reporting.cra_chart_service import build_chart_data
from app.services.reporting.cra_narrative_service import build_narrative
from app.services.reporting.cra_risk_engine import aggregate_findings
from app.services.reporting.cra_summary_service import build_summary
from app.services.reporting.word_report_generator import render_word_report
from app.services.reporting.report_customization import get_customization_for_pdf, clear_customization
from app.services.registry_service import get_registry


REPORT_ROOT = Path("storage/reports")
SERVICE_ORDER = [
    "Entra ID",
    "Exchange Online",
    "Microsoft Purview",
    "Teams",
    "OneDrive",
    "SharePoint",
    "Licensing",
    "Microsoft 365",
]


async def generate_report_bundle(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
    report_type: str | None = None,
) -> dict[str, Any]:
    report_data = await build_report_data(db, current_user=current_user, assessment_id=assessment_id)
    customization = get_customization_for_pdf(assessment_id)
    requested_report_type = _normalize_report_type(report_type or customization.get("output_format") or "docx")

    assessment = report_data["assessment"]
    target_dir = REPORT_ROOT / str(assessment.id)
    tenant_name = _safe_report_filename(report_data["summary"].get("tenant_name") or report_data["summary"].get("customer_name") or assessment.tenant_id)
    generated_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_stem = f"Copilot_Readiness_Assessment_{tenant_name}_{generated_stamp}"
    docx_path = await asyncio.to_thread(
        render_word_report,
        target_dir / f"{report_stem}.docx",
        report_data,
    )

    await db.execute(delete(AssessmentReport).where(AssessmentReport.assessment_id == assessment.id))
    artifacts: list[AssessmentReport] = []
    docx_artifact = AssessmentReport(
        assessment_id=assessment.id,
        report_type="docx",
        report_status="generated",
        storage_path=str(docx_path),
        generated_by=current_user.id,
        metadata_json={**report_data["metadata"], "source": "docx_template"},
    )
    db.add(docx_artifact)
    artifacts.append(docx_artifact)
    assessment.report_path = str(docx_path)

    pdf_error = None
    if requested_report_type in {"pdf", "both"}:
        try:
            pdf_path = await _convert_docx_to_pdf_async(
                docx_path,
                target_dir / f"{report_stem}.pdf",
            )
            pdf_artifact = AssessmentReport(
                assessment_id=assessment.id,
                report_type="pdf",
                report_status="generated",
                storage_path=str(pdf_path),
                generated_by=current_user.id,
                metadata_json={**report_data["metadata"], "source": "docx_to_pdf"},
            )
            db.add(pdf_artifact)
            artifacts.append(pdf_artifact)
            assessment.report_path = str(pdf_path)
        except Exception as exc:
            # If PDF conversion fails but DOCX succeeded, capture the error
            # but still return DOCX successfully
            pdf_error = str(exc)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"PDF conversion failed for assessment {assessment_id}: {pdf_error}. "
                "DOCX report is available."
            )

    await db.commit()
    for artifact in artifacts:
        await db.refresh(artifact)

    # Clear customization after report generation
    clear_customization(assessment_id)

    return {
        "assessment_id": assessment.id,
        "status": "generated" if not pdf_error else "partial",
        "artifacts": [_artifact_payload(artifact) for artifact in artifacts],
        "summary": report_data["summary"],
        "analytics": report_data["analytics"],
        "pdf_conversion_error": pdf_error,
    }


async def generate_legacy_pdf_report_bundle(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict[str, Any]:
    """Compatibility wrapper for callers that still expect the old PDF-first behavior."""
    return await generate_report_bundle(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
        report_type="pdf",
    )


def _normalize_report_type(report_type: str) -> str:
    value = (report_type or "docx").strip().lower()
    if value not in {"docx", "pdf", "both"}:
        raise ValueError("Report type must be one of: docx, pdf, both")
    return value


async def get_report_bundle(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict[str, Any]:
    report_data = await build_report_data(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentReport)
        .where(AssessmentReport.assessment_id == assessment_id)
        .order_by(AssessmentReport.generated_at.desc())
    )
    artifacts = list(result.scalars().all())
    return {
        "assessment_id": assessment_id,
        "status": "generated" if artifacts else "not_generated",
        "download_ready": bool(artifacts),
        "artifacts": [_artifact_payload(item) for item in artifacts],
        "summary": report_data["summary"],
        "analytics": report_data["analytics"],
    }


async def get_report_artifact(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
    report_type: str = "pdf",
) -> AssessmentReport:
    await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    result = await db.execute(
        select(AssessmentReport)
        .where(
            AssessmentReport.assessment_id == assessment_id,
            AssessmentReport.report_type == report_type,
        )
        .order_by(AssessmentReport.generated_at.desc())
        .limit(1)
    )
    artifact = result.scalars().first()
    if artifact is None:
        raise FileNotFoundError("Report artifact has not been generated")
    return artifact


async def get_report_debug(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict[str, Any]:
    report_data = await build_report_data(db, current_user=current_user, assessment_id=assessment_id)
    assessment = report_data["assessment"]
    findings = await _load_findings(db, assessment.id)
    recommendations = await _load_recommendations(db, assessment.id, assessment.tenant_id)
    artifacts = await _load_artifacts(db, assessment.id, assessment.tenant_id)
    report_result = await db.execute(
        select(AssessmentReport).where(AssessmentReport.assessment_id == assessment_id)
    )
    reports = list(report_result.scalars().all())
    scores = [
        assessment.overall_score,
        assessment.identity_score,
        assessment.security_score,
        assessment.compliance_score,
        assessment.collaboration_score,
        assessment.licensing_score,
    ]
    return {
        "assessment_status": assessment.status,
        "tenant_id": assessment.tenant_id,
        "artifact_count": len(artifacts),
        "finding_count": len(findings),
        "recommendation_count": len(recommendations),
        "report_count": len(reports),
        "findings_count": report_data["metadata"]["finding_count"],
        "scores_count": len([score for score in scores if score is not None]),
        "recommendations_count": report_data["metadata"]["recommendation_count"],
        "sections_generated": report_data["metadata"]["sections_generated"],
        "missing_sections": report_data["metadata"]["missing_sections"],
    }


async def build_report_data(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
) -> dict[str, Any]:
    assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    tenant_result = await db.execute(
        select(ConnectedTenant).where(ConnectedTenant.tenant_id == assessment.tenant_id)
    )
    tenant = tenant_result.scalars().first()
    findings = await _load_findings(db, assessment.id)
    recommendations = await _load_recommendations(db, assessment.id, assessment.tenant_id)
    artifacts = await _load_artifacts(db, assessment.id, assessment.tenant_id)
    analytics_raw = aggregate_findings(findings)
    summary = build_summary(assessment=assessment, findings=findings, recommendations=recommendations)
    narrative = build_narrative(summary=summary, analytics=analytics_raw)
    parameter_rows = _build_parameter_rows(findings, recommendations, artifacts)
    summary = {
        **summary,
        "tenant_id": assessment.tenant_id,
        "tenant_name": tenant.tenant_name if tenant and tenant.tenant_name else assessment.tenant_id,
        "customer_name": tenant.tenant_name if tenant and tenant.tenant_name else summary.get("customer_name"),
        "parameter_total": len(parameter_rows),
        "collected_total": len([row for row in parameter_rows if row["status"] in {"pass", "warning", "fail"}]),
        "failed_total": len([row for row in parameter_rows if row["status"] == "failed"]),
        "licensing_required_total": len([row for row in parameter_rows if row["status"] in {"licensing_required", "licensing_limitation"}]),
        "manual_validation_total": len([row for row in parameter_rows if row["status"] == "manual_validation_required"]),
        "not_collected_total": len([row for row in parameter_rows if row["status"] == "not_collected"]),
    }
    analytics = _build_report_analytics(summary=summary, parameter_rows=parameter_rows, assessment=assessment)
    sections = _build_sections_from_rows(parameter_rows)
    report_model = _build_report_model(
        assessment=assessment,
        summary=summary,
        analytics=analytics,
        parameter_rows=parameter_rows,
        recommendations=recommendations,
    )
    sections_generated = [section["title"] for section in report_model["sections"] if section["items"] or section.get("metrics")]
    return {
        "assessment": assessment,
        "summary": summary,
        "analytics": analytics,
        "narrative": narrative,
        "sections": sections,
        "report_model": report_model,
        "parameter_rows": parameter_rows,
        "metadata": {
            "finding_count": len(findings),
            "recommendation_count": len(recommendations),
            "failed_collector_count": len([item for item in artifacts if item.status != "collected"]),
            "parameter_count": len(parameter_rows),
            "sections_generated": sections_generated,
            "missing_sections": [
                section["title"] for section in report_model["sections"]
                if not section["items"] and not section.get("metrics")
            ],
            "evidence_policy": "missing collectors are NOT_COLLECTED; failed collectors are FAILED",
        },
    }


async def _load_findings(db: AsyncSession, assessment_id: UUID) -> list[AssessmentFinding]:
    result = await db.execute(
        select(AssessmentFinding)
        .options(selectinload(AssessmentFinding.parameter))
        .where(AssessmentFinding.assessment_id == assessment_id)
    )
    return list(result.scalars().all())


async def _load_recommendations(
    db: AsyncSession,
    assessment_id: UUID,
    tenant_id: str,
) -> list[AssessmentRecommendation]:
    result = await db.execute(
        select(AssessmentRecommendation).where(
            AssessmentRecommendation.assessment_id == assessment_id,
            AssessmentRecommendation.tenant_id == tenant_id,
        )
    )
    return list(result.scalars().all())


async def _load_artifacts(
    db: AsyncSession,
    assessment_id: UUID,
    tenant_id: str,
) -> list[AssessmentArtifact]:
    result = await db.execute(
        select(AssessmentArtifact).where(
            AssessmentArtifact.assessment_id == assessment_id,
            AssessmentArtifact.tenant_id == tenant_id,
        )
    )
    return list(result.scalars().all())


def _build_sections(
    findings: list[AssessmentFinding],
    recommendations: list[AssessmentRecommendation],
    artifacts: list[AssessmentArtifact],
) -> dict[str, list[dict[str, Any]]]:
    rec_by_key = {item.parameter_key: item for item in recommendations}
    sections = {service: [] for service in SERVICE_ORDER}
    for finding in findings:
        parameter = finding.parameter
        raw = finding.raw_value or {}
        parameter_key = raw.get("parameter_key") or getattr(parameter, "parameter_key", None) or ""
        service = _service_for_key(parameter_key, getattr(parameter, "category", None))
        recommendation = rec_by_key.get(parameter_key)
        item = {
            "title": getattr(parameter, "parameter_name", None) or parameter_key,
            "service": service,
            "pillar": getattr(parameter, "category", None) or "Best Practice",
            "severity": (finding.severity or "info").lower(),
            "finding": finding.evaluated_value or finding.status,
            "description": getattr(parameter, "copilot_relevance", None) or "Assessment control evaluated for Copilot readiness.",
            "risk": _risk_text(finding),
            "recommendation": recommendation.recommendation_text if recommendation else "Review and remediate this control.",
            "evidence": raw,
            "documentation_link": "",
        }
        sections.setdefault(service, []).append(item)
    collected_keys = {
        (finding.raw_value or {}).get("parameter_key") or getattr(finding.parameter, "parameter_key", None)
        for finding in findings
    }
    for artifact in artifacts:
        if artifact.status == "collected" or artifact.parameter_key in collected_keys:
            continue
        service = _service_for_key(artifact.parameter_key, artifact.service)
        sections.setdefault(service, []).append(
            {
                "title": artifact.parameter_key,
                "service": service,
                "pillar": artifact.service or "Unknown",
                "severity": "info",
                "finding": "NOT COLLECTED",
                "description": "Collector did not produce trusted evidence.",
                "risk": "No readiness conclusion was generated for this control because evidence was unavailable.",
                "recommendation": "Resolve collector configuration and re-run the assessment.",
                "evidence": {
                    "status": artifact.status,
                    "error": artifact.stderr,
                    "source_script": artifact.source_script,
                    "source_csv": artifact.source_csv,
                },
                "documentation_link": "",
            }
        )
    return {service: sections.get(service, []) for service in SERVICE_ORDER if sections.get(service)}


def _build_parameter_rows(
    findings: list[AssessmentFinding],
    recommendations: list[AssessmentRecommendation],
    artifacts: list[AssessmentArtifact],
) -> list[dict[str, Any]]:
    registry = get_registry()
    rec_by_key = {item.parameter_key: item for item in recommendations}
    registry_rec_by_key = {
        item["parameter_key"]: item
        for item in registry.get_recommendations()
    }
    finding_by_key = {
        ((finding.raw_value or {}).get("parameter_key") or getattr(finding.parameter, "parameter_key", None)): finding
        for finding in findings
    }
    artifact_by_key: dict[str, list[AssessmentArtifact]] = {}
    for artifact in artifacts:
        artifact_by_key.setdefault(artifact.parameter_key, []).append(artifact)

    rows: list[dict[str, Any]] = []
    for parameter in registry.get_parameters():
        key = parameter["parameter_key"]
        finding = finding_by_key.get(key)
        recommendation = rec_by_key.get(key)
        registry_recommendation = registry_rec_by_key.get(key, {})
        parameter_artifacts = artifact_by_key.get(key, [])
        latest_artifact = parameter_artifacts[-1] if parameter_artifacts else None
        status = _row_status(finding, latest_artifact)
        evidence = (finding.raw_value if finding else None) or _artifact_evidence(latest_artifact)
        service = _service_for_key(key, parameter.get("category") or parameter.get("domain"))
        row = {
            "parameter_key": key,
            "title": parameter.get("display_name") or key,
            "service": service,
            "pillar": str(parameter.get("domain") or parameter.get("category") or "unclassified").replace("_", " ").title(),
            "category": parameter.get("category"),
            "technology": parameter.get("technology"),
            "severity": (finding.severity if finding else parameter.get("severity") or "info").lower(),
            "status": status,
            "score_contribution": finding.score_contribution if finding else None,
            "finding": finding.evaluated_value if finding else "NOT COLLECTED",
            "actual_result": _actual_result_text(finding, latest_artifact),
            "expected_result": parameter.get("pass_criteria") or parameter.get("expected_output") or "",
            "description": parameter.get("copilot_relevance") or "",
            "pass_criteria": parameter.get("pass_criteria") or "",
            "fail_criteria": parameter.get("fail_criteria") or "",
            "expected_output": parameter.get("expected_output") or "",
            "recommendation": (
                recommendation.recommendation_text
                if recommendation
                else _registry_recommendation_text(registry_recommendation)
            ),
            "remediation_steps": (
                recommendation.remediation_steps
                if recommendation
                else registry_recommendation.get("remediation_steps", [])
            ),
            "evidence": evidence,
            "artifact_status": latest_artifact.status if latest_artifact else None,
            "artifact_error": latest_artifact.stderr if latest_artifact else None,
            "source_script": latest_artifact.source_script if latest_artifact else None,
            "source_csv": latest_artifact.source_csv if latest_artifact else None,
        }
        rows.append(row)
    return rows


def _actual_result_text(finding: AssessmentFinding | None, artifact: AssessmentArtifact | None) -> str:
    if finding is not None:
        raw = finding.raw_value if isinstance(finding.raw_value, dict) else {}
        actual = raw.get("actual_value")
        if actual is not None:
            return _display_value(actual)
        if finding.evaluated_value:
            return finding.evaluated_value
        return str(finding.status or "Assessed")
    if artifact is not None:
        if artifact.status == "failed":
            return artifact.stderr or "Collector execution failed"
        return str(artifact.status or "Evidence unavailable")
    return "Evidence was not collected for this assessment."


def _display_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, dict):
        parts = []
        for key, item in list(value.items())[:4]:
            label = str(key).replace("_", " ").title()
            if isinstance(item, bool):
                rendered = "Yes" if item else "No"
            elif isinstance(item, list):
                rendered = f"{len(item)} item(s)"
            elif isinstance(item, dict):
                rendered = f"{len(item)} field(s)"
            else:
                rendered = str(item)
            parts.append(f"{label}: {rendered}")
        return "; ".join(parts)
    return str(value)


def _row_status(finding: AssessmentFinding | None, artifact: AssessmentArtifact | None) -> str:
    if finding is not None:
        return str(finding.status or "warning").lower()
    if artifact is None:
        return "not_collected"
    artifact_status = str(artifact.status or "").lower()
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    result_status = str(result.get("status") or "").lower()
    if artifact_status == "failed":
        return "collection_error"
    if result_status in {"collection_error", "failed_collector", "collector_failed"}:
        return "collection_error"
    if result_status in {"licensing_required", "licensing_limitation"}:
        return "licensing_required"
    if result_status in {"manual_validation_required", "not_supported", "powershell_required", "graph_limitation"}:
        return "manual_validation_required"
    if artifact_status in {"evidence_collected"}:
        return "manual_validation_required"
    return result_status or artifact_status or "not_collected"


def _registry_recommendation_text(registry_recommendation: dict[str, Any]) -> str:
    if not registry_recommendation:
        return "No recommendation record exists for this parameter."
    steps = registry_recommendation.get("remediation_steps") or []
    if steps:
        return str(steps[0])
    impact = registry_recommendation.get("impact") or registry_recommendation.get("copilot_impact")
    if impact:
        return str(impact)
    return registry_recommendation.get("title") or "Recommendation source did not include remediation text."


def _artifact_evidence(artifact: AssessmentArtifact | None) -> dict[str, Any]:
    if artifact is None:
        return {"status": "missing", "message": "No finding or collector artifact exists for this parameter."}
    return {
        "status": artifact.status,
        "error": artifact.stderr,
        "source_script": artifact.source_script,
        "source_csv": artifact.source_csv,
        "payload": artifact.payload,
    }


def _build_sections_from_rows(parameter_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    sections = {service: [] for service in SERVICE_ORDER}
    for row in parameter_rows:
        sections.setdefault(row["service"], []).append({
            "title": row["title"],
            "service": row["service"],
            "pillar": row["pillar"],
            "severity": row["severity"],
            "finding": row["finding"],
            "description": row["description"],
            "risk": _risk_text_from_row(row),
            "recommendation": row["recommendation"],
            "evidence": row["evidence"],
            "documentation_link": "",
            "status": row["status"],
        })
    return {service: items for service, items in sections.items() if items}


def _build_report_analytics(*, summary: dict, parameter_rows: list[dict[str, Any]], assessment: Any) -> dict:
    from collections import Counter

    severity = Counter(row["severity"] for row in parameter_rows)
    status = Counter(row["status"] for row in parameter_rows)
    services = Counter(row["service"] for row in parameter_rows)
    pillars = Counter(row["pillar"] for row in parameter_rows)
    licensing_rows = [row for row in parameter_rows if row["service"] == "Licensing" or "license" in row["parameter_key"]]
    licensing_status = Counter(row["status"] for row in licensing_rows)
    analytics = build_chart_data(
        summary={
            **summary,
            "pass_total": status.get("pass", 0),
            "warning_total": status.get("warning", 0),
            "fail_total": status.get("fail", 0),
        },
        analytics={
            "severity": {name: severity.get(name, 0) for name in ["critical", "high", "medium", "low", "info"]},
            "status": {
                "pass": status.get("pass", 0),
                "warning": status.get("warning", 0),
                "fail": status.get("fail", 0),
            },
            "services": dict(sorted(services.items())),
            "pillars": dict(sorted(pillars.items())),
        },
    )
    analytics["not_collected"] = status.get("not_collected", 0)
    analytics["security_governance_best_practice"] = [
        {"name": name, "value": pillars.get(name, 0)}
        for name in ["Security", "Governance", "Best Practice"]
    ]
    analytics["m365_service_scores"] = _service_scores(parameter_rows)
    analytics["pillar_scores"] = _pillar_scores(parameter_rows)
    analytics["licensing_readiness"] = [
        {"name": "Pass", "value": licensing_status.get("pass", 0)},
        {"name": "Warning", "value": licensing_status.get("warning", 0)},
        {"name": "Fail", "value": licensing_status.get("fail", 0)},
        {"name": "Not Collected", "value": licensing_status.get("not_collected", 0)},
    ]
    analytics["assessment_scores"] = {
        "overall": assessment.overall_score,
        "identity": assessment.identity_score,
        "security": assessment.security_score,
        "compliance": assessment.compliance_score,
        "collaboration": assessment.collaboration_score,
        "licensing": assessment.licensing_score,
    }
    return analytics


def _score_for_rows(rows: list[dict[str, Any]]) -> float | None:
    collected = [row for row in rows if row["status"] in {"pass", "warning", "fail"}]
    if not collected:
        return None
    points = sum(1.0 if row["status"] == "pass" else 0.5 if row["status"] == "warning" else 0.0 for row in collected)
    return round(points / len(collected) * 100, 2)


def _service_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"name": service, "score": _score_for_rows([row for row in rows if row["service"] == service])}
        for service in SERVICE_ORDER
        if any(row["service"] == service for row in rows)
    ]


def _pillar_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pillars = sorted({row["pillar"] for row in rows})
    return [
        {"name": pillar, "score": _score_for_rows([row for row in rows if row["pillar"] == pillar])}
        for pillar in pillars
    ]


def _build_report_model(
    *,
    assessment: Any,
    summary: dict,
    analytics: dict,
    parameter_rows: list[dict[str, Any]],
    recommendations: list[AssessmentRecommendation],
) -> dict[str, Any]:
    return {
        "title": "Copilot Readiness Assessment",
        "assessment_id": str(assessment.id),
        "tenant_id": assessment.tenant_id,
        "sections": [
            {"title": "Executive Summary", "metrics": summary, "items": []},
            {"title": "Readiness Score", "metrics": analytics["assessment_scores"], "items": []},
            {"title": "Pillar Scores", "metrics": {}, "items": analytics["pillar_scores"]},
            {"title": "M365 Service Scores", "metrics": {}, "items": analytics["m365_service_scores"]},
            {"title": "Severity Distribution", "metrics": {}, "items": analytics["severity_distribution"]},
            {"title": "Findings Summary", "metrics": {}, "items": analytics["pass_fail"] + [{"name": "Not Collected", "value": analytics["not_collected"]}]},
            {"title": "Detailed Findings", "metrics": {}, "items": parameter_rows},
            {"title": "Recommendations", "metrics": {}, "items": [
                _recommendation_payload_from_row(row)
                for row in parameter_rows
                if row.get("recommendation")
            ]},
            {"title": "Licensing Analysis", "metrics": {}, "items": analytics["licensing_readiness"]},
            {"title": "User Activity Analysis", "metrics": {}, "items": [
                row for row in parameter_rows
                if any(token in row["parameter_key"] for token in ["active", "inactive", "user", "mailbox", "onedrive"])
            ]},
            {"title": "Conclusion", "metrics": {"readiness_status": summary["readiness_status"], "deployment_recommendation": summary["deployment_recommendation"]}, "items": []},
        ],
    }


def _recommendation_payload(item: AssessmentRecommendation) -> dict[str, Any]:
    return {
        "parameter_key": item.parameter_key,
        "severity": item.severity,
        "title": item.title,
        "recommendation": item.recommendation_text,
        "remediation_steps": item.remediation_steps,
        "impact": item.impact,
    }


def _recommendation_payload_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "parameter_key": row["parameter_key"],
        "severity": row["severity"],
        "title": f"Recommendation for {row['title']}",
        "recommendation": row["recommendation"],
        "remediation_steps": row.get("remediation_steps") or [],
        "impact": row.get("description") or "",
        "status": row["status"],
    }


def _risk_text_from_row(row: dict[str, Any]) -> str:
    if row["status"] == "pass":
        return "No immediate risk was identified for this control."
    if row["status"] == "not_collected":
        return "No readiness conclusion was generated because evidence was not collected."
    if row["severity"] in {"critical", "high"}:
        return "This finding can materially increase Copilot deployment, data exposure, or governance risk."
    return "This finding should be reviewed as part of readiness improvement planning."


def _service_for_key(parameter_key: str, category: str | None) -> str:
    text = f"{parameter_key} {category or ''}".lower()
    if any(token in text for token in ["entra", "mfa", "identity", "admin", "guest_users"]):
        return "Entra ID"
    if any(token in text for token in ["exchange", "mailbox", "email", "calendar"]):
        return "Exchange Online"
    if any(token in text for token in ["purview", "audit", "dlp", "secure_score", "sensitivity"]):
        return "Microsoft Purview"
    if "teams" in text or "meeting" in text:
        return "Teams"
    if "onedrive" in text:
        return "OneDrive"
    if any(token in text for token in ["sharepoint", "site", "sharing", "permission", "anyone_links", "anyone links"]):
        return "SharePoint"
    if "license" in text:
        return "Licensing"
    return "Microsoft 365"


def _risk_text(finding: AssessmentFinding) -> str:
    severity = (finding.severity or "info").lower()
    if finding.status == "pass":
        return "No immediate risk was identified for this control."
    if severity in {"critical", "high"}:
        return "This finding can materially increase Copilot deployment, data exposure, or governance risk."
    return "This finding should be reviewed as part of readiness improvement planning."


def _artifact_payload(item: AssessmentReport) -> dict[str, Any]:
    return {
        "id": item.id,
        "assessment_id": item.assessment_id,
        "report_type": item.report_type,
        "report_status": item.report_status,
        "storage_path": item.storage_path,
        "generated_at": item.generated_at.isoformat(),
        "generated_by": item.generated_by,
        "metadata": item.metadata_json,
    }


def _safe_report_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip())
    return cleaned.strip("._") or "tenant"


async def _convert_docx_to_pdf_async(
    docx_path: Path,
    pdf_path: Path,
) -> Path:
    """Convert DOCX to PDF with a real document converter; never fall back to synthetic PDF."""
    try:
        from docx2pdf import convert
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(convert, str(docx_path), str(pdf_path))
        if _is_valid_pdf(pdf_path):
            return pdf_path
    except Exception as exc:
        last_error = exc
    else:
        last_error = RuntimeError("docx2pdf did not produce a valid PDF")

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        try:
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(
                subprocess.run,
                [
                    soffice,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(pdf_path.parent),
                    str(docx_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            converted = pdf_path.parent / f"{docx_path.stem}.pdf"
            if converted != pdf_path and converted.exists():
                converted.replace(pdf_path)
            if _is_valid_pdf(pdf_path):
                return pdf_path
        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        "PDF generation requires a reliable DOCX-to-PDF converter. "
        "Generate DOCX, or install/configure Microsoft Word docx2pdf or LibreOffice headless."
    ) from last_error


def _is_valid_pdf(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size <= 1000:
            return False
        with path.open("rb") as handle:
            return handle.read(4) == b"%PDF"
    except OSError:
        return False
