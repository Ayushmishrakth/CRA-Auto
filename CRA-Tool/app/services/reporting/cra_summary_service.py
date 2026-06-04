from __future__ import annotations

from typing import Any

from app.services.reporting.cra_risk_engine import aggregate_findings, readiness_status


def build_summary(*, assessment: Any, findings: list[Any], recommendations: list[Any]) -> dict:
    analytics = aggregate_findings(findings)
    status_counts = analytics["status"]
    score = float(assessment.overall_score or 0)
    return {
        "customer_name": assessment.tenant_id,
        "assessment_id": str(assessment.id),
        "assessment_date": assessment.created_at.isoformat() if assessment.created_at else None,
        "overall_readiness": round(score, 2),
        "readiness_status": readiness_status(score),
        "pass_total": status_counts["pass"],
        "warning_total": status_counts["warning"],
        "fail_total": status_counts["fail"],
        "total_findings": len(findings),
        "critical_findings": analytics["severity"].get("critical", 0),
        "high_findings": analytics["severity"].get("high", 0),
        "recommendation_count": len(recommendations),
        "deployment_recommendation": _deployment_recommendation(score, analytics),
    }


def _deployment_recommendation(score: float, analytics: dict) -> str:
    critical = analytics["severity"].get("critical", 0)
    high = analytics["severity"].get("high", 0)
    if score >= 85 and critical == 0:
        return "Proceed with Copilot rollout while continuing standard governance monitoring."
    if score >= 70 and critical <= 2:
        return "Proceed with a controlled pilot after remediating priority identity, security, and data governance findings."
    if high or critical:
        return "Defer broad Copilot deployment until critical and high-risk controls are remediated."
    return "Proceed only after the documented readiness gaps are validated and accepted by stakeholders."
