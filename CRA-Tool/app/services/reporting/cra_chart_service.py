from __future__ import annotations


def build_chart_data(*, summary: dict, analytics: dict) -> dict:
    return {
        "severity_distribution": [
            {"name": name.title(), "value": value}
            for name, value in analytics["severity"].items()
        ],
        "pillar_distribution": [
            {"name": name, "value": value}
            for name, value in analytics["pillars"].items()
        ],
        "service_distribution": [
            {"name": name, "value": value}
            for name, value in analytics["services"].items()
        ],
        "pass_fail": [
            {"name": "Pass", "value": summary["pass_total"]},
            {"name": "Warning", "value": summary["warning_total"]},
            {"name": "Fail", "value": summary["fail_total"]},
        ],
        "readiness_gauge": {
            "score": summary["overall_readiness"],
            "status": summary["readiness_status"],
        },
    }
