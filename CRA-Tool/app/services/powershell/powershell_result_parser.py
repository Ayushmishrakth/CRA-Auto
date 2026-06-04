"""
Parse the Phase 7B PowerShell collector JSON contract.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


SEVERITY_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}


class PowerShellResultParseError(ValueError):
    pass


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_collector_contract(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        raise PowerShellResultParseError("PowerShell collector returned empty stdout")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PowerShellResultParseError("PowerShell collector stdout is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise PowerShellResultParseError("PowerShell collector JSON must be an object")

    for key in ("status", "collector", "tenant_id", "timestamp", "findings", "metrics", "warnings", "errors"):
        if key not in payload:
            raise PowerShellResultParseError(f"PowerShell collector JSON missing '{key}'")

    if not isinstance(payload["findings"], list):
        raise PowerShellResultParseError("PowerShell collector 'findings' must be a list")
    if not isinstance(payload["metrics"], dict):
        raise PowerShellResultParseError("PowerShell collector 'metrics' must be an object")
    if not isinstance(payload["warnings"], list) or not isinstance(payload["errors"], list):
        raise PowerShellResultParseError("PowerShell collector warnings/errors must be lists")

    return payload


def failure_contract(
    *,
    collector: str,
    tenant_id: str,
    parameter_key: str,
    message: str,
    severity: str,
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "failed",
        "collector": collector,
        "tenant_id": tenant_id,
        "timestamp": _utc_iso(),
        "findings": [
            {
                "parameter_key": parameter_key,
                "status": "fail",
                "severity": severity or "info",
                "value": {"error": message},
                "message": message,
                "score_contribution": float(SEVERITY_RANK.get((severity or "info").lower(), 1)),
            }
        ],
        "metrics": {"execution": telemetry},
        "warnings": [],
        "errors": [message],
    }


def contract_to_collector_result(
    *,
    parameter: dict[str, Any],
    collector: dict[str, Any],
    contract: dict[str, Any],
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    parameter_key = parameter["parameter_key"]
    severity = (parameter.get("severity") or "info").lower()
    finding = next(
        (
            item
            for item in contract.get("findings", [])
            if isinstance(item, dict) and item.get("parameter_key", parameter_key) == parameter_key
        ),
        {},
    )

    status = (finding.get("status") or contract.get("status") or "fail").lower()
    if status == "success":
        status = "pass"
    if status not in {"pass", "warning", "fail", "not_collected"}:
        status = "fail" if contract.get("errors") else "warning"

    finding_severity = (finding.get("severity") or severity).lower()
    score_contribution = finding.get("score_contribution")
    if score_contribution is None:
        score_contribution = float(SEVERITY_RANK.get(finding_severity, 1))
        if status in {"pass", "not_collected"}:
            score_contribution = 0.0
        elif status == "warning":
            score_contribution = round(score_contribution * 0.45, 2)

    raw_value = {
        "parameter_key": parameter_key,
        "collector_type": collector.get("collector_type", "powershell"),
        "powershell": True,
        "collector_contract": contract,
        "execution": telemetry,
    }

    return {
        "parameter_key": parameter_key,
        "status": status,
        "severity": finding_severity,
        "raw_value": raw_value,
        "evaluated_value": finding.get("message")
        or contract.get("metrics", {}).get("summary")
        or f"PowerShell {status} result for {parameter.get('display_name', parameter_key)}",
        "score_contribution": float(score_contribution),
        "warnings": contract.get("warnings") or [],
        "errors": contract.get("errors") or [],
        "telemetry": telemetry,
    }
