"""
Runtime registry loader for Phase 7A.

The runtime reads JSON registries only. Excel parsing stays in scripts/build_registry.py.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REGISTRY_DIR = Path(__file__).resolve().parents[1] / "config" / "assessment_registry"


class RegistryValidationError(RuntimeError):
    pass


class AssessmentRegistry:
    def __init__(self, registry_dir: Path = REGISTRY_DIR) -> None:
        self.registry_dir = registry_dir
        self.parameters = self._load_list("parameters")
        self.rules = self._load_list("rules")
        self.collectors = self._load_list("collectors")
        self.recommendations = self._load_list("recommendations")
        self.scoring = self._load_dict("scoring")
        self._parameter_by_key = {item["parameter_key"]: item for item in self.parameters}
        self._rule_by_key = {item["parameter_key"]: item for item in self.rules}
        self._collector_by_key = {item["parameter_key"]: item for item in self.collectors}
        self._recommendation_by_key = {
            item["parameter_key"]: item for item in self.recommendations
        }
        self.validate()

    def _load_json(self, name: str) -> Any:
        path = self.registry_dir / f"{name}.json"
        if not path.exists():
            raise RegistryValidationError(f"Missing registry file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_list(self, name: str) -> list[dict[str, Any]]:
        data = self._load_json(name)
        if not isinstance(data, list):
            raise RegistryValidationError(f"{name}.json must contain a list")
        return data

    def _load_dict(self, name: str) -> dict[str, Any]:
        data = self._load_json(name)
        if not isinstance(data, dict):
            raise RegistryValidationError(f"{name}.json must contain an object")
        return data

    @staticmethod
    def _ensure_unique(items: list[dict[str, Any]], label: str) -> set[str]:
        keys = [item.get("parameter_key") for item in items]
        duplicates = sorted({key for key in keys if key and keys.count(key) > 1})
        if duplicates:
            raise RegistryValidationError(f"Duplicate {label} parameter keys: {duplicates}")
        return {str(key) for key in keys if key}

    def validate(self) -> None:
        parameter_keys = self._ensure_unique(self.parameters, "parameter")
        rule_keys = self._ensure_unique(self.rules, "rule")
        collector_keys = self._ensure_unique(self.collectors, "collector")
        recommendation_keys = self._ensure_unique(self.recommendations, "recommendation")

        required_parameter_fields = {
            "parameter_key",
            "display_name",
            "domain",
            "severity",
            "collector_type",
            "scoring_weight",
            "copilot_blocker",
        }
        missing = []
        for item in self.parameters:
            missing_fields = required_parameter_fields - set(item)
            if missing_fields:
                missing.append(f"{item.get('parameter_key')}: {sorted(missing_fields)}")
        if missing:
            raise RegistryValidationError(f"Invalid parameters registry: {missing[:10]}")

        for label, keys in {
            "rules": rule_keys,
            "collectors": collector_keys,
            "recommendations": recommendation_keys,
        }.items():
            unknown = sorted(keys - parameter_keys)
            absent = sorted(parameter_keys - keys)
            if unknown:
                raise RegistryValidationError(f"{label} references unknown parameters: {unknown[:10]}")
            if absent:
                raise RegistryValidationError(f"{label} missing parameters: {absent[:10]}")

        if "domain_weights" not in self.scoring or "severity_deductions" not in self.scoring:
            raise RegistryValidationError("Scoring registry missing required scoring maps")

    def get_parameters(self) -> list[dict[str, Any]]:
        return self.parameters

    def get_rules(self) -> list[dict[str, Any]]:
        return self.rules

    def get_collectors(self) -> list[dict[str, Any]]:
        return self.collectors

    def get_recommendations(self) -> list[dict[str, Any]]:
        return self.recommendations

    def get_scoring_config(self) -> dict[str, Any]:
        return self.scoring

    def get_parameter_by_key(self, parameter_key: str) -> dict[str, Any] | None:
        return self._parameter_by_key.get(parameter_key)

    def get_rule_by_key(self, parameter_key: str) -> dict[str, Any] | None:
        return self._rule_by_key.get(parameter_key)

    def get_collector_by_key(self, parameter_key: str) -> dict[str, Any] | None:
        return self._collector_by_key.get(parameter_key)

    def get_recommendation_by_key(self, parameter_key: str) -> dict[str, Any] | None:
        return self._recommendation_by_key.get(parameter_key)


@lru_cache(maxsize=1)
def get_registry() -> AssessmentRegistry:
    return AssessmentRegistry()
