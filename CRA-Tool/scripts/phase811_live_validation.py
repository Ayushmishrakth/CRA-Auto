from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.models.assessment import Assessment
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.assessment_report import AssessmentReport
from app.db.models.tenant import ConnectedTenant
import app.db.base  # noqa: F401 - register SQLAlchemy models for relationship resolution
from app.db.session import AsyncSessionLocal
from app.services.graph.graph_client import GraphClient
from app.services.graph_cra_collector_service import get_app_graph_token
from app.services.registry_service import get_registry
from app.services.runtime_assessment_service import run_assessment_job


TENANT_ID = "fe4eff9a-f69c-48c0-921d-8006a6d5beb2"
REQUIRED_NEW_PERMISSIONS = [
    "Sites.FullControl.All",
    "SharePointTenantSettings.Read.All",
    "InformationProtectionPolicy.Read.All",
    "SecurityActions.Read.All",
]
REPORT_ROOT = PROJECT_ROOT.parent


def write_report(name: str, content: str) -> None:
    (REPORT_ROOT / name).write_text(content.rstrip() + "\n", encoding="utf-8")


def table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


async def get_tenant() -> ConnectedTenant:
    async with AsyncSessionLocal() as db:
        result = await db.execute(sa.select(ConnectedTenant).where(ConnectedTenant.tenant_id == TENANT_ID))
        tenant = result.scalars().first()
        if tenant is None:
            raise RuntimeError(f"Connected tenant not found: {TENANT_ID}")
        return tenant


async def validate_graph_permissions() -> dict:
    tenant = await get_tenant()
    token = await get_app_graph_token(tenant)
    client = GraphClient(access_token=token)
    graph_sp_response = await client.get(
        "/servicePrincipals",
        params={
            "$filter": "appId eq '00000003-0000-0000-c000-000000000000'",
            "$select": "id,appId,displayName,appRoles",
        },
    )
    graph_sp = (graph_sp_response.get("value") or [None])[0]
    if not graph_sp:
        raise RuntimeError("Microsoft Graph service principal not found")
    role_by_id = {
        role.get("id"): role.get("value")
        for role in graph_sp.get("appRoles") or []
        if role.get("id") and role.get("value")
    }
    assignments = await client.get(
        f"/servicePrincipals/{tenant.service_principal_id}/appRoleAssignments",
        params={"$select": "id,appRoleId,resourceDisplayName,principalDisplayName"},
    )
    granted = {
        role_by_id.get(item.get("appRoleId"))
        for item in assignments.get("value") or []
    }
    rows = [
        {
            "permission": permission,
            "status": "Granted" if permission in granted else "Not Granted",
        }
        for permission in REQUIRED_NEW_PERMISSIONS
    ]
    write_report(
        "GRAPH_PERMISSION_VALIDATION.md",
        f"""# Graph Permission Validation

Generated: 2026-06-02

Tenant: `{tenant.tenant_id}`

App client ID: `{tenant.app_client_id}`

Service principal ID: `{tenant.service_principal_id}`

{table(["Permission", "Status"], [[row["permission"], row["status"]] for row in rows])}
""",
    )
    return {"tenant": tenant, "rows": rows, "granted": granted}


def run_powershell_check(name: str, command: str, timeout: int = 45) -> dict:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "service": name,
        "returncode": completed.returncode,
        "status": "Success" if completed.returncode == 0 else "Failed",
        "stdout": completed.stdout.strip()[-1000:],
        "stderr": completed.stderr.strip()[-1000:],
    }


def validate_powershell() -> list[dict]:
    checks = [
        (
            "Exchange Online",
            "Import-Module ExchangeOnlineManagement -ErrorAction Stop; "
            "Get-ConnectionInformation -ErrorAction Stop | Select-Object -First 1 | ConvertTo-Json -Compress",
        ),
        (
            "Purview",
            "Import-Module ExchangeOnlineManagement -ErrorAction Stop; "
            "Get-Command Get-DlpCompliancePolicy -ErrorAction Stop | Select-Object -First 1 -ExpandProperty Name",
        ),
        (
            "SharePoint Online",
            "Import-Module Microsoft.Online.SharePoint.PowerShell -ErrorAction Stop; "
            "Get-Command Get-SPOTenant -ErrorAction Stop | Select-Object -First 1 -ExpandProperty Name",
        ),
        (
            "PnP PowerShell",
            "Import-Module PnP.PowerShell -ErrorAction Stop; "
            "Get-PnPConnection -ErrorAction Stop | ConvertTo-Json -Compress",
        ),
    ]
    results = []
    for name, command in checks:
        try:
            results.append(run_powershell_check(name, command))
        except subprocess.TimeoutExpired as exc:
            results.append({
                "service": name,
                "returncode": -1,
                "status": "Timeout",
                "stdout": (exc.stdout or "")[-1000:] if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "")[-1000:] if isinstance(exc.stderr, str) else "",
            })
    write_report(
        "POWERSHELL_CONNECTIVITY_REPORT.md",
        f"""# PowerShell Connectivity Report

Generated: 2026-06-02

This validation checks whether non-interactive delegated PowerShell context is already available on the runtime host. It does not start browser or device-code authentication.

{table(["Service", "Connection", "Command execution"], [[item["service"], item["status"], "Succeeded" if item["returncode"] == 0 else "Failed"] for item in results])}

## Details

{table(["Service", "Return Code", "Stdout", "Stderr"], [[item["service"], item["returncode"], item["stdout"].replace("|", "/"), item["stderr"].replace("|", "/")] for item in results])}
""",
    )
    return results


async def run_live_assessment(disable_interactive_powershell: bool) -> dict:
    if disable_interactive_powershell:
        os.environ["CRA_EXCHANGE_AUTH_MODE"] = "disabled"
        os.environ["CRA_PURVIEW_AUTH_MODE"] = "disabled"
        os.environ["CRA_PNP_AUTH_MODE"] = "disabled"
        os.environ["CRA_TEAMS_AUTH_MODE"] = "disabled"
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(sa.select(ConnectedTenant).where(ConnectedTenant.tenant_id == TENANT_ID))).scalars().first()
        user_row = (
            await db.execute(
                sa.text("select id from users where microsoft_tid = :tenant_id order by created_at desc limit 1"),
                {"tenant_id": TENANT_ID},
            )
        ).first()
        if user_row is None:
            raise RuntimeError(f"No user found for tenant {TENANT_ID}")
        assessment = Assessment(
            tenant_id=TENANT_ID,
            triggered_by_user_id=UUID(str(user_row[0])),
            status="queued",
            progress_pct=0.0,
        )
        db.add(assessment)
        await db.flush()
        job = AssessmentJob(
            assessment_id=assessment.id,
            tenant_id=TENANT_ID,
            status="queued",
            progress_pct=0.0,
            current_stage="queued",
            metadata_payload={
                "phase": "8.11_live_validation",
                "tenant_name": tenant.tenant_name if tenant else None,
                "interactive_powershell_disabled": disable_interactive_powershell,
            },
        )
        db.add(job)
        await db.flush()
        assessment.job_id = job.id
        await db.commit()
        assessment_id = str(assessment.id)
        job_id = str(job.id)

    started = time.time()
    await run_assessment_job(job_id, worker_id="phase-8.11-certification")
    duration = round(time.time() - started, 2)

    async with AsyncSessionLocal() as db:
        assessment = await db.get(Assessment, UUID(assessment_id))
        job = await db.get(AssessmentJob, UUID(job_id))
        finding_count = await db.scalar(sa.select(sa.func.count()).select_from(AssessmentFinding).where(AssessmentFinding.assessment_id == assessment.id))
        recommendation_count = await db.scalar(sa.select(sa.func.count()).select_from(AssessmentRecommendation).where(AssessmentRecommendation.assessment_id == assessment.id))
        artifact_count = await db.scalar(sa.select(sa.func.count()).select_from(AssessmentArtifact).where(AssessmentArtifact.assessment_id == assessment.id))
        report_count = await db.scalar(sa.select(sa.func.count()).select_from(AssessmentReport).where(AssessmentReport.assessment_id == assessment.id))
        return {
            "assessment_id": assessment_id,
            "job_id": job_id,
            "status": assessment.status,
            "job_status": job.status,
            "duration_seconds": duration,
            "progress_pct": assessment.progress_pct,
            "metadata": job.metadata_payload or {},
            "finding_count": finding_count or 0,
            "recommendation_count": recommendation_count or 0,
            "artifact_count": artifact_count or 0,
            "report_count": report_count or 0,
        }


async def summarize_existing_assessment(assessment_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        assessment = await db.get(Assessment, UUID(assessment_id))
        if assessment is None:
            raise RuntimeError(f"Assessment not found: {assessment_id}")
        job = (
            await db.execute(
                sa.select(AssessmentJob)
                .where(AssessmentJob.assessment_id == assessment.id)
                .order_by(AssessmentJob.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
        finding_count = await db.scalar(sa.select(sa.func.count()).select_from(AssessmentFinding).where(AssessmentFinding.assessment_id == assessment.id))
        recommendation_count = await db.scalar(sa.select(sa.func.count()).select_from(AssessmentRecommendation).where(AssessmentRecommendation.assessment_id == assessment.id))
        artifact_count = await db.scalar(sa.select(sa.func.count()).select_from(AssessmentArtifact).where(AssessmentArtifact.assessment_id == assessment.id))
        report_count = await db.scalar(sa.select(sa.func.count()).select_from(AssessmentReport).where(AssessmentReport.assessment_id == assessment.id))
        duration = None
        if job and job.started_at and job.completed_at:
            duration = round((job.completed_at - job.started_at).total_seconds(), 2)
        return {
            "assessment_id": str(assessment.id),
            "job_id": str(job.id) if job else "",
            "status": assessment.status,
            "job_status": job.status if job else "",
            "duration_seconds": duration,
            "progress_pct": assessment.progress_pct,
            "metadata": job.metadata_payload if job else {},
            "finding_count": finding_count or 0,
            "recommendation_count": recommendation_count or 0,
            "artifact_count": artifact_count or 0,
            "report_count": report_count or 0,
        }


async def generate_execution_reports(run: dict) -> dict:
    registry = get_registry()
    graph_keys = set()
    source = (Path(__file__).resolve().parents[1] / "app/services/graph_cra_collector_service.py").read_text(encoding="utf-8")
    import ast
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "GRAPH_COLLECTORS" for target in node.targets):
            graph_keys = {key.value for key in node.value.keys if isinstance(key, ast.Constant)}
    async with AsyncSessionLocal() as db:
        assessment_uuid = UUID(run["assessment_id"])
        artifact_rows = (
            await db.execute(
                sa.select(AssessmentArtifact)
                .where(AssessmentArtifact.assessment_id == assessment_uuid)
                .order_by(AssessmentArtifact.parameter_key.asc())
            )
        ).scalars().all()
        finding_rows = (
            await db.execute(
                sa.select(AssessmentFinding)
                .where(AssessmentFinding.assessment_id == assessment_uuid)
            )
        ).scalars().all()
    finding_by_key = {item.parameter_key: item for item in finding_rows if item.parameter_key}
    artifact_by_key = {item.parameter_key: item for item in artifact_rows}
    matrix = []
    real_statuses = {"pass", "fail", "warning"}
    licensing_statuses = {"licensing_required", "licensing_limitation"}
    manual_statuses = {"manual_validation_required"}
    failed_statuses = {"not_collected", "error", "failed", "no_data", "not_supported"}
    counts = Counter()
    for parameter in registry.get_parameters():
        key = parameter["parameter_key"]
        finding = finding_by_key.get(key)
        artifact = artifact_by_key.get(key)
        status = (finding.status if finding else artifact.status if artifact else "no_data").lower()
        if status in real_statuses:
            bucket = "real_collected"
        elif status in licensing_statuses:
            bucket = "licensing_required"
        elif status in manual_statuses:
            bucket = "manual_validation"
        else:
            bucket = "failed_collectors"
        counts[bucket] += 1
        collector_type = "GRAPH" if key in graph_keys else "POWERSHELL"
        if status in manual_statuses:
            collector_type = "MANUAL"
        matrix.append([key, collector_type, status.upper()])

    approved = len(registry.get_parameters())
    real = counts["real_collected"]
    coverage = round(real / approved * 100, 2) if approved else 0.0
    write_report(
        "LIVE_COLLECTOR_EXECUTION_MATRIX.md",
        f"""# Live Collector Execution Matrix

Generated: 2026-06-02

Assessment ID: `{run["assessment_id"]}`

Job ID: `{run["job_id"]}`

Duration: `{run["duration_seconds"]}` seconds

Collector count: `{approved}`

{table(["parameter_key", "collector_type", "status"], matrix)}
""",
    )
    write_report(
        "REAL_COVERAGE_CERTIFICATION.md",
        f"""# Real Coverage Certification

Generated: 2026-06-02

Assessment ID: `{run["assessment_id"]}`

## Certified Counts

{table(["Metric", "Count"], [
    ["Approved Parameters", approved],
    ["Real Collected", counts["real_collected"]],
    ["Licensing Required", counts["licensing_required"]],
    ["Manual Validation", counts["manual_validation"]],
    ["Failed Collectors", counts["failed_collectors"]],
])}

## Certified Coverage

```text
Real Evidence Parameters / 64 Approved Parameters = {real} / {approved} = {coverage}%
```

Certified coverage: **{coverage}%**
""",
    )
    write_report(
        "ASSESSMENT_CERTIFICATION_REPORT.md",
        f"""# Assessment Certification Report

Generated: 2026-06-02

## Assessment Run

{table(["Field", "Value"], [
    ["Assessment ID", run["assessment_id"]],
    ["Job ID", run["job_id"]],
    ["Assessment Status", run["status"]],
    ["Job Status", run["job_status"]],
    ["Progress", run["progress_pct"]],
    ["Duration Seconds", run["duration_seconds"]],
])}

## Generated Outputs

{table(["Output", "Count"], [
    ["Findings", run["finding_count"]],
    ["Recommendations", run["recommendation_count"]],
    ["Evidence Artifacts", run["artifact_count"]],
    ["Reports", run["report_count"]],
])}

## Runtime Metadata

{table(["Metric", "Value"], [[key, value] for key, value in sorted((run["metadata"] or {}).items()) if key in {"collector_total", "collector_collected", "collector_incomplete", "graph_calls", "findings_created", "recommendations_created", "scores_created", "reports_generated"}])}

## Certification Result

The assessment completed with status `{run["status"]}`. Coverage certification is recorded in `REAL_COVERAGE_CERTIFICATION.md`.
""",
    )
    return {"counts": counts, "coverage": coverage, "matrix": matrix}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-assessment", action="store_true")
    parser.add_argument("--certify-assessment-id")
    parser.add_argument("--allow-interactive-powershell", action="store_true")
    args = parser.parse_args()
    graph = await validate_graph_permissions()
    ps = validate_powershell()
    if args.skip_assessment:
        print(json.dumps({"graph": graph["rows"], "powershell": ps}, indent=2))
        return
    if args.certify_assessment_id:
        run = await summarize_existing_assessment(args.certify_assessment_id)
    else:
        run = await run_live_assessment(disable_interactive_powershell=not args.allow_interactive_powershell)
    coverage = await generate_execution_reports(run)
    print(json.dumps({"graph": graph["rows"], "powershell": ps, "run": run, "coverage": {"counts": dict(coverage["counts"]), "coverage": coverage["coverage"]}}, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
