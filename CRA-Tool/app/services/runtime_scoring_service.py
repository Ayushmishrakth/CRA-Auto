"""
Runtime scoring service for assessment execution.
"""

from __future__ import annotations

from typing import Any

from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.services.registry_service import get_registry


ASSESSMENT_FIELD_BY_DOMAIN = {
    "identity_access": "identity_score",
    "security": "security_score",
    "best_practice": "security_score",
    "governance": "security_score",
    "compliance": "compliance_score",
    "collaboration": "collaboration_score",
    "licensing": "licensing_score",
}


def _domain_for_parameter(parameter_key: str) -> str:
    registry = get_registry()
    parameter = registry.get_parameter_by_key(parameter_key) or {}
    if "license" in parameter_key or "licensing" in parameter_key:
        return "licensing"
    return parameter.get("domain") or "security"


def calculate_scores(findings: list[AssessmentFinding]) -> dict[str, Any]:
    registry = get_registry()
    scoring = registry.get_scoring_config()
    severity_deductions = scoring.get("severity_deductions", {})
    domain_weights = scoring.get("domain_weights", {})

    domain_totals: dict[str, float] = {
        str(domain): 100.0 for domain in domain_weights
    } or {"security": 100.0}
    critical_count = 0
    high_count = 0
    blocker_count = 0
    total_findings = len(findings)

    for finding in findings:
        parameter_key = (finding.raw_value or {}).get("parameter_key", "")
        domain = _domain_for_parameter(parameter_key)
        domain_totals.setdefault(domain, 100.0)
        severity = (finding.severity or "info").lower()
        if severity == "critical" and finding.status in {"fail", "warning"}:
            critical_count += 1
        if severity == "high" and finding.status in {"fail", "warning"}:
            high_count += 1
        parameter = registry.get_parameter_by_key(parameter_key) or {}
        if finding.status in {"fail", "warning"} and parameter.get("copilot_blocker"):
            blocker_count += 1
        if finding.status in {"pass", "collection_error", "licensing_required", "manual_validation"}:
            continue
        multiplier = 1.0 if finding.status == "fail" else 0.45
        weight = float(parameter.get("scoring_weight") or 1.0)
        domain_totals[domain] -= float(severity_deductions.get(severity, 1)) * multiplier * weight

    domain_scores = {
        "identity_score": 100.0,
        "security_score": 100.0,
        "compliance_score": 100.0,
        "collaboration_score": 100.0,
        "licensing_score": 100.0,
    }
    field_values: dict[str, list[float]] = {key: [] for key in domain_scores}
    for domain, score in domain_totals.items():
        field = ASSESSMENT_FIELD_BY_DOMAIN.get(domain, "security_score")
        field_values[field].append(max(0.0, min(100.0, score)))

    for field, values in field_values.items():
        if values:
            domain_scores[field] = round(sum(values) / len(values), 2)

    weighted_total = 0.0
    total_weight = 0.0
    for domain, weight in domain_weights.items():
        field = ASSESSMENT_FIELD_BY_DOMAIN.get(domain, "security_score")
        weighted_total += domain_scores[field] * float(weight)
        total_weight += float(weight)
    overall = round(weighted_total / total_weight, 2) if total_weight else round(
        sum(domain_scores.values()) / len(domain_scores),
        2,
    )
    if blocker_count:
        cap = scoring.get("blocker_logic", {}).get("critical_copilot_blockers_cap_score_at", 59)
        overall = min(overall, float(cap))

    return {
        **domain_scores,
        "overall_score": overall,
        "total_findings": total_findings,
        "critical_findings": critical_count,
        "high_findings": high_count,
    }


def apply_scores(assessment: Assessment, findings: list[AssessmentFinding]) -> dict[str, Any]:
    scores = calculate_scores(findings)
    for key, value in scores.items():
        setattr(assessment, key, value)
    return scores
