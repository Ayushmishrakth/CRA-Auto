from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.csv_ingestion import parse_csv_evidence
from app.services.powershell.powershell_executor import PowerShellExecution, PowerShellExecutor


class DomainRuntimeError(RuntimeError):
    pass


class DomainRuntime:
    service: str = "m365"
    master_script: str | None = None

    def __init__(self, *, executor: PowerShellExecutor | None = None) -> None:
        self.executor = executor or PowerShellExecutor()

    async def execute_master_script(
        self,
        *,
        tenant_id: str,
        output_csv: str,
        timeout_seconds: float = 900,
    ) -> list[dict[str, Any]]:
        if not self.master_script:
            raise DomainRuntimeError(f"{self.__class__.__name__} has no canonical master script configured")
        script_path = Path(self.master_script)
        if not script_path.exists():
            raise DomainRuntimeError(f"Canonical master script not found: {script_path}")

        result = await self.executor.execute(
            PowerShellExecution(
                script_path=script_path,
                tenant_id=tenant_id,
                collector_name=f"{self.service}.master",
                parameter_key=f"{self.service}_master",
                parameter={"parameter_key": f"{self.service}_master"},
                collector={"collector_name": f"{self.service}.master"},
                timeout_seconds=timeout_seconds,
                max_retries=0,
            )
        )
        if result.status != "success":
            raise DomainRuntimeError(result.stderr or "; ".join(result.errors) or "Master script failed")
        return parse_csv_evidence(
            csv_path=output_csv,
            parameter_key=f"{self.service}_master",
            service=self.service,
            severity="info",
            source_script=str(script_path),
        )
