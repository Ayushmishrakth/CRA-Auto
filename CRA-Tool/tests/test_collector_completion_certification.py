import json
from pathlib import Path

from app.services.graph_cra_collector_service import GRAPH_COLLECTORS
from app.services.runtime_assessment_service import _select_runtime


ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_all_approved_parameters_have_manifest_and_script_output_contracts():
    parameters = _load_json("app/config/assessment_registry/parameters.json")
    manifest = {
        item["parameter_key"]: item
        for item in _load_json("app/config/collector_manifest.json")
    }

    missing_manifest = []
    missing_script = []
    missing_output_contract = []

    for parameter in parameters:
        key = parameter["parameter_key"]
        entry = manifest.get(key)
        if entry is None:
            missing_manifest.append(key)
            continue

        script = ROOT / entry["script"]
        if not script.exists():
            missing_script.append((key, entry["script"]))
            continue

        script_text = script.read_text(encoding="utf-8")
        if entry["output_file"] not in script_text:
            missing_output_contract.append((key, entry["script"], entry["output_file"]))

    assert len(parameters) == 65
    assert missing_manifest == []
    assert missing_script == []
    assert missing_output_contract == []


def test_manifest_power_shell_only_collectors_route_to_powershell():
    manifest = _load_json("app/config/collector_manifest.json")
    for entry in manifest:
        if (
            entry.get("supports_powershell")
            and not entry.get("supports_graph")
            and entry["parameter_key"] not in GRAPH_COLLECTORS
        ):
            assert _select_runtime(
                parameter_key=entry["parameter_key"],
                manifest_entry=entry,
            ) == "powershell"


def test_python_graph_collectors_route_to_graph_first():
    manifest = {
        item["parameter_key"]: item
        for item in _load_json("app/config/collector_manifest.json")
    }
    parameters = _load_json("app/config/assessment_registry/parameters.json")
    official_keys = {item["parameter_key"] for item in parameters}

    for key in sorted(official_keys & set(GRAPH_COLLECTORS)):
        assert _select_runtime(
            parameter_key=key,
            manifest_entry=manifest.get(key),
        ) == "graph"


def test_no_collector_notimplemented_errors_in_backend_app():
    offenders = []
    for path in (ROOT / "app").rglob("*.py"):
        if "NotImplementedError" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
