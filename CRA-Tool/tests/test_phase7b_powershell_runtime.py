import json
import os
import stat
import textwrap
from pathlib import Path

import pytest

from app.services.powershell.powershell_collector_base import PowerShellCollectorResolver
from app.services.powershell.powershell_executor import PowerShellExecution, PowerShellExecutor
from app.services.powershell.powershell_result_parser import (
    PowerShellResultParseError,
    contract_to_collector_result,
    parse_collector_contract,
)
from app.services.powershell.powershell_runtime import PowerShellExecutionEngine


def _fake_pwsh(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body.lstrip())
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _script(path: Path) -> Path:
    path.write_text("ignored")
    return path


def _contract(status: str = "pass") -> dict:
    return {
        "status": "success",
        "collector": "powershell.test",
        "tenant_id": "tenant-a",
        "timestamp": "2026-01-01T00:00:00Z",
        "findings": [
            {
                "parameter_key": "test_parameter",
                "status": status,
                "severity": "high",
                "value": {"enabled": True},
                "message": "collector produced JSON",
                "score_contribution": 0 if status == "pass" else 4,
            }
        ],
        "metrics": {"summary": "ok"},
        "warnings": [],
        "errors": [],
    }


def test_parse_collector_contract_requires_json_object():
    payload = parse_collector_contract(json.dumps(_contract()))
    assert payload["collector"] == "powershell.test"

    with pytest.raises(PowerShellResultParseError):
        parse_collector_contract("plain text")


def test_contract_maps_to_existing_collector_result_shape():
    result = contract_to_collector_result(
        parameter={"parameter_key": "test_parameter", "severity": "high", "display_name": "Test"},
        collector={"collector_type": "powershell"},
        contract=_contract("warning"),
        telemetry={"duration_ms": 12, "attempts": 1, "retries": 0},
    )
    assert result["parameter_key"] == "test_parameter"
    assert result["status"] == "warning"
    assert result["raw_value"]["powershell"] is True
    assert result["raw_value"]["execution"]["duration_ms"] == 12


async def test_executor_runs_subprocess_and_captures_json(tmp_path):
    fake = _fake_pwsh(
        tmp_path / "pwsh",
        textwrap.dedent(
            f"""
            import json
            print(json.dumps({_contract()!r}))
            """
        ),
    )
    execution = PowerShellExecution(
        script_path=_script(tmp_path / "collector.ps1"),
        tenant_id="tenant-a",
        collector_name="powershell.test",
        parameter_key="test_parameter",
        parameter={"parameter_key": "test_parameter"},
        collector={"collector_name": "powershell.test"},
        timeout_seconds=2,
        max_retries=0,
    )
    result = await PowerShellExecutor(executable=str(fake)).execute(execution)
    assert result.status == "success"
    assert result.exit_code == 0
    assert parse_collector_contract(result.stdout)["status"] == "success"


async def test_executor_times_out_and_cleans_process(tmp_path):
    fake = _fake_pwsh(
        tmp_path / "pwsh",
        "import time\ntime.sleep(5)\n",
    )
    execution = PowerShellExecution(
        script_path=_script(tmp_path / "collector.ps1"),
        tenant_id="tenant-a",
        collector_name="powershell.test",
        parameter_key="test_parameter",
        parameter={"parameter_key": "test_parameter"},
        collector={"collector_name": "powershell.test"},
        timeout_seconds=0.1,
        max_retries=0,
    )
    result = await PowerShellExecutor(executable=str(fake)).execute(execution)
    assert result.status == "timeout"
    assert result.timed_out is True
    assert result.exit_code is None


async def test_executor_retries_failed_subprocess(tmp_path):
    marker = tmp_path / "attempts.txt"
    fake = _fake_pwsh(
        tmp_path / "pwsh",
        textwrap.dedent(
            f"""
            import json, pathlib, sys
            marker = pathlib.Path({str(marker)!r})
            attempts = int(marker.read_text()) if marker.exists() else 0
            marker.write_text(str(attempts + 1))
            if attempts == 0:
                print('first failure', file=sys.stderr)
                raise SystemExit(7)
            print(json.dumps({_contract()!r}))
            """
        ),
    )
    execution = PowerShellExecution(
        script_path=_script(tmp_path / "collector.ps1"),
        tenant_id="tenant-a",
        collector_name="powershell.test",
        parameter_key="test_parameter",
        parameter={"parameter_key": "test_parameter"},
        collector={"collector_name": "powershell.test"},
        timeout_seconds=2,
        max_retries=1,
    )
    result = await PowerShellExecutor(executable=str(fake)).execute(execution)
    assert result.status == "success"
    assert result.attempts == 2


async def test_engine_returns_failure_finding_when_pwsh_missing(tmp_path):
    engine = PowerShellExecutionEngine(
        executor=PowerShellExecutor(executable=str(tmp_path / "missing-pwsh")),
        resolver=PowerShellCollectorResolver(root=tmp_path),
        timeout_seconds=1,
    )
    (tmp_path / "generic_collector.ps1").write_text("ignored")
    result = await engine.run_collector(
        tenant_id="tenant-a",
        parameter={"parameter_key": "test_parameter", "severity": "critical", "display_name": "Test"},
        collector={"collector_name": "powershell.test", "collector_type": "powershell"},
    )
    assert result["status"] == "fail"
    assert result["errors"]
    assert result["raw_value"]["powershell"] is True
