"""
Async PowerShell subprocess executor with timeout, retries, and telemetry.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PowerShellExecution:
    script_path: Path
    tenant_id: str
    collector_name: str
    parameter_key: str
    parameter: dict[str, Any]
    collector: dict[str, Any]
    assessment_id: str | None = None
    output_root: str = "artifacts"
    timeout_seconds: float = 30.0
    max_retries: int = 0
    environment: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PowerShellExecutionResult:
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    attempts: int
    timed_out: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def telemetry(self) -> dict[str, Any]:
        return {
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "retries": max(0, self.attempts - 1),
            "timeout_count": 1 if self.timed_out else 0,
            "timed_out": self.timed_out,
            "exit_code": self.exit_code,
            "stderr": self.stderr[-4000:] if self.stderr else "",
            "stdout": self.stdout[-20000:] if self.stdout else "",
            "stdout_preview": self.stdout[:1200] if self.stdout else "",
        }


class PowerShellExecutor:
    def __init__(self, *, executable: str = "pwsh") -> None:
        self.executable = executable

    def _resolve_executable(self) -> list[str] | None:
        if Path(self.executable).exists():
            path = Path(self.executable)
            if os.name == "nt" and path.suffix.lower() not in {".exe", ".bat", ".cmd", ".ps1"}:
                return [sys.executable, str(path)]
            return [self.executable]
        resolved = shutil.which(self.executable)
        return [resolved] if resolved else None

    @staticmethod
    def _safe_script_path(path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"PowerShell collector script not found: {resolved}")
        return resolved

    def _build_args(self, executable: list[str], execution: PowerShellExecution) -> list[str]:
        script = self._safe_script_path(execution.script_path)
        parameter_json = json.dumps(execution.parameter, separators=(",", ":"))
        collector_json = json.dumps(execution.collector, separators=(",", ":"))
        return [
            *executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-TenantId",
            execution.tenant_id,
            "-CollectorName",
            execution.collector_name,
            "-ParameterKey",
            execution.parameter_key,
            "-ParameterJson",
            parameter_json,
            "-CollectorJson",
            collector_json,
            "-AssessmentId",
            execution.assessment_id or "adhoc",
            "-OutputRoot",
            execution.output_root,
        ]

    async def _run_once(
        self,
        execution: PowerShellExecution,
        *,
        executable: list[str],
        attempt: int,
        started_at: float,
    ) -> PowerShellExecutionResult:
        proc = await asyncio.create_subprocess_exec(
            *self._build_args(executable, execution),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **execution.environment},
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=execution.timeout_seconds,
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            status = "success" if proc.returncode == 0 else "failed"
            return PowerShellExecutionResult(
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode,
                duration_ms=round((time.perf_counter() - started_at) * 1000),
                attempts=attempt,
                errors=[] if proc.returncode == 0 else [stderr.strip() or f"PowerShell exited {proc.returncode}"],
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return PowerShellExecutionResult(
                status="timeout",
                stdout="",
                stderr="",
                exit_code=None,
                duration_ms=round((time.perf_counter() - started_at) * 1000),
                attempts=attempt,
                timed_out=True,
                errors=[f"PowerShell collector timed out after {execution.timeout_seconds}s"],
            )

    async def execute(self, execution: PowerShellExecution) -> PowerShellExecutionResult:
        executable = self._resolve_executable()
        started_at = time.perf_counter()
        if executable is None:
            return PowerShellExecutionResult(
                status="failed",
                stdout="",
                stderr="pwsh executable was not found",
                exit_code=None,
                duration_ms=0,
                attempts=1,
                errors=["pwsh executable was not found"],
            )

        attempts = max(1, execution.max_retries + 1)
        last_result: PowerShellExecutionResult | None = None
        for attempt in range(1, attempts + 1):
            result = await self._run_once(
                execution,
                executable=executable,
                attempt=attempt,
                started_at=started_at,
            )
            last_result = result
            if result.status == "success":
                return result
            if attempt < attempts:
                await asyncio.sleep(min(0.2 * attempt, 1.0))

        return last_result or PowerShellExecutionResult(
            status="failed",
            stdout="",
            stderr="PowerShell collector did not run",
            exit_code=None,
            duration_ms=round((time.perf_counter() - started_at) * 1000),
            attempts=attempts,
            errors=["PowerShell collector did not run"],
        )
