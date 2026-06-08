"""
Async PowerShell subprocess executor with timeout, retries, and telemetry.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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
    timeout_seconds: float = 300.0
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

    @staticmethod
    def _event_loop_snapshot() -> dict[str, str | bool]:
        policy = asyncio.get_event_loop_policy()
        snapshot: dict[str, str | bool] = {
            "event_loop_policy": f"{type(policy).__module__}.{type(policy).__name__}",
            "loop_type": "none",
            "subprocess_supported": True,  # always True with to_thread(subprocess.run())
        }
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            close_loop = True
        else:
            close_loop = False
        try:
            snapshot["loop_type"] = f"{type(loop).__module__}.{type(loop).__name__}"
        finally:
            if close_loop:
                loop.close()
        return snapshot

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

    @staticmethod
    def _run_powershell_sync(
        args: list[str],
        environment: dict[str, str],
        timeout: int,
    ) -> tuple[str, str, int | None, bool]:
        """
        Run PowerShell synchronously via subprocess.run().
        Returns (stdout, stderr, returncode, timed_out).
        Using subprocess.run() inside asyncio.to_thread() bypasses the event loop's
        subprocess transport entirely, which fixes NotImplementedError on Windows
        where SelectorEventLoop does not support asyncio.create_subprocess_exec().
        """
        try:
            result = subprocess.run(
                args,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env={**os.environ, **environment},
            )
            return result.stdout, result.stderr, result.returncode, False
        except subprocess.TimeoutExpired:
            return "", "", None, True

    async def _run_once(
        self,
        execution: PowerShellExecution,
        *,
        executable: list[str],
        attempt: int,
        started_at: float,
    ) -> PowerShellExecutionResult:
        args = self._build_args(executable, execution)
        logger.info(
            "PowerShell collector subprocess starting",
            extra={
                "assessment_id": execution.assessment_id,
                "parameter_key": execution.parameter_key,
                "collector": execution.collector_name,
                "source_script": str(execution.script_path),
                "attempt": attempt,
                **self._event_loop_snapshot(),
            },
        )
        try:
            stdout, stderr, returncode, timed_out = await asyncio.to_thread(
                self._run_powershell_sync,
                args,
                execution.environment,
                int(execution.timeout_seconds),
            )
        except Exception:
            logger.exception(
                "PowerShell collector subprocess creation failed",
                extra={
                    "assessment_id": execution.assessment_id,
                    "parameter_key": execution.parameter_key,
                    "collector": execution.collector_name,
                    "source_script": str(execution.script_path),
                    "attempt": attempt,
                    **self._event_loop_snapshot(),
                },
            )
            raise

        if timed_out:
            logger.warning(
                "PowerShell collector subprocess timed out",
                extra={
                    "assessment_id": execution.assessment_id,
                    "parameter_key": execution.parameter_key,
                    "collector": execution.collector_name,
                    "source_script": str(execution.script_path),
                    "attempts": attempt,
                    "exit_code": None,
                    **self._event_loop_snapshot(),
                },
            )
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

        status = "success" if returncode == 0 else "failed"
        logger.info(
            "PowerShell collector subprocess completed",
            extra={
                "assessment_id": execution.assessment_id,
                "parameter_key": execution.parameter_key,
                "collector": execution.collector_name,
                "source_script": str(execution.script_path),
                "attempts": attempt,
                "exit_code": returncode,
                "stdout": stdout[-20000:] if stdout else "",
                "stderr": stderr[-4000:] if stderr else "",
                **self._event_loop_snapshot(),
            },
        )
        return PowerShellExecutionResult(
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=returncode,
            duration_ms=round((time.perf_counter() - started_at) * 1000),
            attempts=attempt,
            errors=[] if returncode == 0 else [stderr.strip() or f"PowerShell exited {returncode}"],
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
