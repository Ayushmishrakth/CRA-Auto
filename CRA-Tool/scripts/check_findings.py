"""Dump findings for the most recent WealthScape assessment."""
import asyncio, sys, json
sys.path.insert(0, ".")

from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob  # noqa
from app.db.models.assessment_parameter import AssessmentParameter  # noqa
from app.db.models.assessment_recommendation import AssessmentRecommendation  # noqa
from app.db.models.assessment_report import AssessmentReport  # noqa
from app.db.models.assessment_rule import AssessmentRule  # noqa
from app.db.models.assessment_event import AssessmentEvent  # noqa
from app.db.models.assessment_artifact import AssessmentArtifact  # noqa
from app.db.session import AsyncSessionLocal
from sqlalchemy import select, desc


async def check():
    async with AsyncSessionLocal() as db:
        # Get most recent completed assessment
        result = await db.execute(
            select(Assessment)
            .where(
                Assessment.tenant_id == "fe4eff9a-f69c-48c0-921d-8006a6d5beb2",
                Assessment.status == "completed",
            )
            .order_by(desc(Assessment.created_at))
            .limit(1)
        )
        assessment = result.scalar_one_or_none()
        if not assessment:
            print("No completed assessment found")
            return

        print(f"Assessment: {assessment.id}  score: {assessment.overall_score}")
        print(f"  identity: {assessment.identity_score}  security: {assessment.security_score}  compliance: {assessment.compliance_score}  collab: {assessment.collaboration_score}")
        print()

        findings_result = await db.execute(
            select(AssessmentFinding)
            .where(AssessmentFinding.assessment_id == assessment.id)
            .order_by(AssessmentFinding.severity.desc(), AssessmentFinding.status)
        )
        findings = findings_result.scalars().all()
        print(f"Total findings: {len(findings)}")
        print()

        # Group by status
        by_status: dict[str, list] = {}
        for f in findings:
            by_status.setdefault(f.status or "unknown", []).append(f)

        for status, items in sorted(by_status.items()):
            print(f"=== {status.upper()} ({len(items)}) ===")
            for f in items:
                raw = f.raw_value or {}
                param_key = raw.get("parameter_key", f.parameter_key or "unknown")
                ct = raw.get("collector_type", "?")
                print(f"  [{ct:12}] {param_key}")


if __name__ == "__main__":
    asyncio.run(check())
