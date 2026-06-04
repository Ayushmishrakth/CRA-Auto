import json
from pathlib import Path

from app.services.powershell.powershell_collector_base import (
    CollectorScriptNotFoundError,
    PowerShellCollectorResolver,
)
from app.services.powershell.powershell_executor import PowerShellExecutor
from app.services.powershell.powershell_runtime import PowerShellExecutionEngine


def test_missing_collector_script_fails_closed():
    resolver = PowerShellCollectorResolver()
    try:
        resolver.resolve_script(
            collector={"collector_name": "powershell.not_real"},
            parameter={"parameter_key": "not_real"},
        )
    except CollectorScriptNotFoundError as exc:
        assert "No collector manifest entry" in str(exc)
    else:
        raise AssertionError("missing collector resolved instead of failing closed")


async def test_engine_does_not_use_generic_collector_for_missing_mapping(tmp_path: Path):
    (tmp_path / "generic_collector.ps1").write_text("ignored")
    engine = PowerShellExecutionEngine(
        executor=PowerShellExecutor(executable=str(tmp_path / "missing-pwsh")),
        resolver=PowerShellCollectorResolver(root=tmp_path),
    )
    result = await engine.run_collector(
        tenant_id="tenant-a",
        parameter={"parameter_key": "not_real", "severity": "critical", "display_name": "Not Real"},
        collector={"collector_name": "powershell.not_real", "collector_type": "powershell"},
    )
    assert result["status"] == "fail"
    assert result["errors"]
    assert "No collector manifest entry" in result["errors"][0]


def test_collector_manifest_explicitly_lists_all_registry_parameters():
    manifest = json.loads(Path("app/config/collector_manifest.json").read_text())
    parameters = json.loads(Path("app/config/assessment_registry/parameters.json").read_text())
    manifest_keys = {item["parameter_key"] for item in manifest}
    parameter_keys = {item["parameter_key"] for item in parameters}
    assert manifest_keys == parameter_keys
    assert all("script" in item and "parser" in item for item in manifest)
