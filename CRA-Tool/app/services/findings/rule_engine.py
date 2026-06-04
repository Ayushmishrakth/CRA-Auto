from __future__ import annotations

from typing import Any


class RuleEvaluationError(RuntimeError):
    pass


def evaluate_rule(*, evidence: list[dict[str, Any]], rule: dict[str, Any]) -> str:
    if evidence is None:
        return "not_collected"
    if not evidence:
        return "not_collected"

    expression = rule.get("expression") or rule.get("pass_condition") or {}
    if not expression:
        return "warning"

    if "min_count" in expression and len(evidence) < int(expression["min_count"]):
        return "fail"
    if "max_count" in expression and len(evidence) > int(expression["max_count"]):
        return "fail"

    field = expression.get("field")
    expected = expression.get("equals")
    if field and "equals" in expression:
        values = {str(row.get(field)).lower() for row in evidence}
        return "pass" if str(expected).lower() in values else "fail"

    forbidden = expression.get("forbidden_values") or []
    if field and forbidden:
        forbidden_values = {str(item).lower() for item in forbidden}
        values = {str(row.get(field)).lower() for row in evidence}
        return "fail" if values & forbidden_values else "pass"

    return "warning"
