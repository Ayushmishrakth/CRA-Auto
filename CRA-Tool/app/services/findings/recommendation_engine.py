from __future__ import annotations

from typing import Any

from app.services.registry_service import get_registry


def build_recommendation(parameter_key: str, *, status: str) -> dict[str, Any]:
    template = get_registry().get_recommendation_by_key(parameter_key) or {}
    if status == "not_collected":
        return {
            "title": f"Collect evidence for {parameter_key}",
            "recommendation": "Resolve collector authentication, module, script, or CSV output failure and re-run the assessment.",
            "remediation": ["Verify Microsoft 365 permissions", "Verify PowerShell modules", "Re-run collector"],
        }
    return {
        "title": template.get("title") or f"Review {parameter_key}",
        "recommendation": template.get("recommendation_text") or template.get("title") or "Review this control.",
        "remediation": template.get("remediation_steps") or ["Review and remediate this CRA control."],
    }
