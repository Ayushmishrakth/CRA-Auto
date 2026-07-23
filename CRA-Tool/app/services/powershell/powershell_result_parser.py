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


_REQUIRED_CONTRACT_KEYS = ("status", "collector", "tenant_id", "timestamp", "findings", "metrics", "warnings", "errors")


def _iter_json_object_candidates(text: str):
    """
    Yield every top-level JSON object substring found in ``text``, in document order.

    PowerShell modules (ExchangeOnlineManagement, Connect-ExchangeOnline, Install-Module,
    Import-Module) can emit banner/verbose/warning text to the success stream before or
    after the compressed JSON contract. This scanner walks the string with brace-depth
    tracking (string- and escape-aware) so a valid contract object is recovered regardless
    of surrounding noise, instead of naively slicing at the last "{" (which lands on a
    nested brace and corrupts the payload).
    """
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    yield text[start:i + 1]
                    break
        start = text.find("{", start + 1)


def _extract_contract_object(text: str) -> dict[str, Any]:
    # 1) The common case: stdout is exactly the JSON contract.
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    # 2) Compressed contracts are a single line; scan lines (last-first) for one that is a
    #    complete JSON object carrying the contract keys.
    fallback: dict[str, Any] | None = None
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            continue
        try:
            candidate = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            if all(key in candidate for key in _REQUIRED_CONTRACT_KEYS):
                return candidate
            fallback = fallback or candidate

    # 3) Brace-depth scan for an embedded object (handles noise on the same line as JSON).
    for candidate_text in _iter_json_object_candidates(text):
        try:
            candidate = json.loads(candidate_text)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            if all(key in candidate for key in _REQUIRED_CONTRACT_KEYS):
                return candidate
            fallback = fallback or candidate

    if fallback is not None:
        return fallback
    raise PowerShellResultParseError("PowerShell collector stdout did not contain a JSON contract object")


def parse_collector_contract(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        raise PowerShellResultParseError("PowerShell collector returned empty stdout")

    payload = _extract_contract_object(text)

    if not isinstance(payload, dict):
        raise PowerShellResultParseError("PowerShell collector JSON must be an object")

    for key in _REQUIRED_CONTRACT_KEYS:
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
    if status == "service_unavailable":
        status = "skipped"  # Exchange/module unavailable — excluded from scoring
    elif status not in {"pass", "warning", "fail", "not_collected", "skipped"}:
        status = "fail" if contract.get("errors") else "warning"

    finding_severity = (finding.get("severity") or severity).lower()
    score_contribution = finding.get("score_contribution")
    if score_contribution is None:
        score_contribution = float(SEVERITY_RANK.get(finding_severity, 1))
        if status in {"pass", "not_collected", "skipped"}:
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
