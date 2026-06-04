# Root Cause: Single Parameter Display

## Observed Latest Assessment

Latest assessment `5eaa7bfbf6ab4a489408a2d9470b1f16` is `completed` at `100.0%`, with job stage `completed`.

The database does not contain only one parameter result. It contains:

- Findings: 65
- Artifacts: 65
- Recommendations: 65
- Reports: 2

However, the status distribution is:

- PASS: 1
- COLLECTION_ERROR: 64

## Exact Root Cause

Only one collector completed successfully: `graph.global_administrator_accounts` for parameter `global_administrator_accounts`.

The other 64 collectors started through the PowerShell runtime and failed before data retrieval. Their artifacts show:

- `exception_type`: `NotImplementedError`
- `exception_message`: empty
- `stdout`: null
- `stderr`: null
- `exit_code`: null

This proves the failure happened inside the platform runtime before PowerShell produced output. It is not a Microsoft API result, not tenant data absence, and not frontend filtering.

## Fault Classification

| Layer | Finding |
| --- | --- |
| Backend execution | Failing for 64 PowerShell collectors before subprocess output. |
| Database persistence | Working. It persisted 65 artifacts, 65 findings, and 65 recommendations. |
| API response | Evidence service is designed to return all 65 registry parameters. |
| Frontend filtering | Default views are `ALL`/`All`; they do not hide collection errors by default. |
| Frontend rendering | Expected to render 65 evidence rows if the evidence API response is loaded. |

## Why Only One Shows PASS

Only one parameter has a PASS result because only one collector used the Graph runtime and completed successfully. The remaining 64 parameters were evaluated as `COLLECTION_ERROR` due to PowerShell runtime execution failure.

## Most Likely Technical Cause From Evidence

The empty `NotImplementedError` is consistent with Python async subprocess creation failing before `pwsh` starts. The runtime path is:

`runtime_assessment_service._collect_findings()` -> `PowerShellExecutionEngine.run_collector()` -> `PowerShellExecutor.execute()` -> `asyncio.create_subprocess_exec(...)`

Because failed artifacts have no stdout, stderr, exit code, attempts, or duration telemetry, the PowerShell command itself did not execute.

## Required Next Fix Area

Fix the backend PowerShell execution runtime for Windows/background execution. The immediate code area is:

- `CRA-Tool/app/services/powershell/powershell_executor.py`
- `CRA-Tool/app/services/powershell/powershell_runtime.py`
- `CRA-Tool/app/services/runtime_assessment_service.py`

The frontend is not the primary cause of the one-PASS result.
