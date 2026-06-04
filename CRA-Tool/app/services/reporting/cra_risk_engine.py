from __future__ import annotations

from collections import Counter
from typing import Any


SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def normalize_severity(value: str | None) -> str:
    value = (value or "info").lower()
    return value if value in SEVERITY_ORDER else "info"


def readiness_status(score: float | None) -> str:
    score = float(score or 0)
    if score >= 85:
        return "Ready"
    if score >= 70:
        return "Ready with remediation"
    if score >= 55:
        return "At risk"
    return "Not ready"


def aggregate_findings(findings: list[Any]) -> dict[str, Any]:
    severity = Counter(normalize_severity(getattr(item, "severity", None)) for item in findings)
    status = Counter((getattr(item, "status", None) or "observed").lower() for item in findings)
    services = Counter(_service_for_finding(item) for item in findings)
    pillars = Counter(_pillar_for_finding(item) for item in findings)
    return {
        "severity": {key: severity.get(key, 0) for key in SEVERITY_ORDER},
        "status": {
            "pass": status.get("pass", 0),
            "warning": status.get("warning", 0),
            "fail": status.get("fail", 0),
        },
        "services": dict(sorted(services.items())),
        "pillars": dict(sorted(pillars.items())),
    }


def _service_for_finding(finding: Any) -> str:
    category = (getattr(getattr(finding, "parameter", None), "category", None) or "").lower()
    key = (getattr(finding, "raw_value", {}) or {}).get("parameter_key", "")
    text = f"{category} {key}".lower()
    if "entra" in text or "identity" in text or "mfa" in text:
        return "Entra ID"
    if "exchange" in text or "mailbox" in text or "email" in text:
        return "Exchange Online"
    if "purview" in text or "audit" in text or "dlp" in text or "secure_score" in text:
        return "Microsoft Purview"
    if "teams" in text or "meeting" in text:
        return "Teams"
    if "onedrive" in text:
        return "OneDrive"
    if "sharepoint" in text or "site" in text:
        return "SharePoint"
    if "license" in text:
        return "Licensing"
    return "Microsoft 365"


def _pillar_for_finding(finding: Any) -> str:
    category = getattr(getattr(finding, "parameter", None), "category", None)
    if category:
        return str(category).replace("_", " ").title()
    severity = normalize_severity(getattr(finding, "severity", None))
    if severity in {"critical", "high"}:
        return "Security"
    return "Best Practice"
