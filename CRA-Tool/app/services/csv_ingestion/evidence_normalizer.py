from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_evidence_row(
    *,
    parameter_key: str,
    service: str,
    severity: str,
    row: dict[str, Any],
    source_script: str | None = None,
    source_csv: str | None = None,
) -> dict[str, Any]:
    status = str(row.get("status") or row.get("pass_fail") or row.get("result") or "").lower()
    if status in {"pass", "success", "passed", "true", "compliant"}:
        status = "pass"
    elif status in {"warn", "warning"}:
        status = "warning"
    elif status in {"fail", "failed", "false", "noncompliant", "non-compliant"}:
        status = "fail"
    else:
        status = "not_collected"

    return {
        "parameter_key": parameter_key,
        "service": service,
        "category": row.get("category"),
        "severity": severity,
        "pass_fail": status,
        "raw_value": row,
        "normalized_value": row.get("value") or row.get("message") or row,
        "evidence": row,
        "recommendation": row.get("recommendation"),
        "remediation": row.get("remediation") or row.get("remediation_steps"),
        "source_script": source_script,
        "source_csv": source_csv,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
