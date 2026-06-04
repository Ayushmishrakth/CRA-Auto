from __future__ import annotations


def build_narrative(*, summary: dict, analytics: dict) -> dict:
    top_services = sorted(analytics["services"].items(), key=lambda item: item[1], reverse=True)[:3]
    top_service_text = ", ".join(name for name, _ in top_services) or "Microsoft 365 services"
    critical = summary["critical_findings"]
    high = summary["high_findings"]

    observations = [
        f"The assessment evaluated {summary['total_findings']} Copilot readiness controls across {top_service_text}.",
        f"The current readiness score is {summary['overall_readiness']}%, resulting in a status of {summary['readiness_status']}.",
        f"The environment contains {critical} critical and {high} high-risk findings that should guide remediation priority.",
    ]
    if summary["pass_total"]:
        observations.append(f"{summary['pass_total']} controls are currently passing and provide a foundation for rollout planning.")

    return {
        "executive_summary": (
            f"The Copilot Readiness Assessment indicates an overall readiness of "
            f"{summary['overall_readiness']}%. Based on the observed control posture, "
            f"the environment is classified as {summary['readiness_status']}."
        ),
        "risk_overview": (
            f"Risk is concentrated across {top_service_text}. "
            f"Critical and high findings should be resolved before broad production enablement."
        ),
        "key_observations": observations,
        "recommendations": [
            summary["deployment_recommendation"],
            "Prioritize remediation of failed critical and high-severity controls.",
            "Re-run the assessment after remediation to validate readiness movement.",
        ],
        "conclusion": (
            f"The organization should use this report as the remediation baseline for Microsoft 365 Copilot readiness. "
            f"{summary['deployment_recommendation']}"
        ),
    }
