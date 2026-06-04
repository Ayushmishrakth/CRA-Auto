"""
PowerShell collector script resolution.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any


POWERSHELL_ROOT = Path(__file__).resolve().parents[2] / "powershell"
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "config" / "collector_manifest.json"


class CollectorScriptNotFoundError(FileNotFoundError):
    """Raised when a registry collector has no explicit script mapping."""


def collector_slug(collector: dict[str, Any], parameter: dict[str, Any]) -> str:
    raw = collector.get("collector_name") or collector.get("powershell_script") or parameter["parameter_key"]
    raw = str(raw).split(".")[-1]
    return re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower()).strip("_")


class PowerShellCollectorResolver:
    def __init__(self, *, root: Path = POWERSHELL_ROOT) -> None:
        self.root = root
        self._manifest = self._load_manifest()

    @staticmethod
    def _load_manifest() -> dict[str, dict[str, Any]]:
        if not MANIFEST_PATH.exists():
            return {}
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return {item["parameter_key"]: item for item in data}

    def resolve_script(self, *, collector: dict[str, Any], parameter: dict[str, Any]) -> Path:
        parameter_key = parameter["parameter_key"]
        manifest_entry = self._manifest.get(parameter_key)
        if manifest_entry is None:
            raise CollectorScriptNotFoundError(
                f"No collector manifest entry mapped for parameter '{parameter_key}'"
            )

        script = str(manifest_entry.get("script") or "").strip()
        if script:
            script_path = Path(script)
            if not script_path.is_absolute():
                script_path = Path.cwd() / script_path
            if script_path.exists() and script_path.is_file():
                return script_path
            raise CollectorScriptNotFoundError(
                f"Collector manifest script does not exist for parameter '{parameter_key}': {script}"
            )

        slug = collector_slug(collector, parameter)
        raise CollectorScriptNotFoundError(
            f"No explicit PowerShell collector script mapped for parameter "
            f"'{parameter_key}' (expected slug '{slug}')"
        )

    def get_manifest_entry(self, parameter_key: str) -> dict[str, Any] | None:
        return self._manifest.get(parameter_key)
