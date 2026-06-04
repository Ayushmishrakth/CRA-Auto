from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.findings.recommendation_engine import build_recommendation
from app.services.findings.rule_engine import evaluate_rule


def build_finding(
    *,
    parameter: dict[str, Any],
    manifest_entry: dict[str, Any],
    evidence: list[dict[str, Any]] | None,
    rule: dict[str, Any] | None,
) -> dict[str, Any]:
    parameter_key = parameter["parameter_key"]
    status = evaluate_rule(evidence=evidence or [], rule=rule or {})
    recommendation = build_recommendation(parameter_key, status=status)
    source_csv = manifest_entry.get("output_file")
    return {
        "parameter_key": parameter_key,
        "service": manifest_entry.get("service"),
        "category": parameter.get("category") or parameter.get("domain"),
        "severity": parameter.get("severity") or "info",
        "pass_fail": status,
        "raw_value": evidence,
        "normalized_value": {
            "row_count": len(evidence or []),
            "source_csv": source_csv,
        },
        "evidence": evidence or [],
        "recommendation": recommendation["recommendation"],
        "remediation": recommendation["remediation"],
        "source_script": manifest_entry.get("script"),
        "source_csv": source_csv,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
