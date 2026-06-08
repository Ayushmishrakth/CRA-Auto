"""
One-time rescore script — run after the 15a migration to recompute stored scores
for all completed assessments so the dashboard shows correct values.

Usage:
    python rescore_assessments.py
"""
import asyncio
import sys
from sqlalchemy import select

# Import all models to ensure SQLAlchemy mapper is fully configured
import app.db.models.assessment  # noqa: F401
import app.db.models.assessment_finding  # noqa: F401
import app.db.models.assessment_job  # noqa: F401
import app.db.models.assessment_artifact  # noqa: F401
import app.db.models.assessment_parameter  # noqa: F401
import app.db.models.assessment_rule  # noqa: F401
import app.db.models.assessment_recommendation  # noqa: F401
import app.db.models.assessment_report  # noqa: F401
import app.db.models.assessment_event  # noqa: F401
import app.db.models.tenant  # noqa: F401
import app.db.models.user  # noqa: F401
import app.db.models.user_session  # noqa: F401
import app.db.models.refresh_token  # noqa: F401
import app.db.models.audit_log  # noqa: F401
import app.db.models.cra_parameter  # noqa: F401

from app.db.session import AsyncSessionLocal
from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.services.runtime_scoring_service import apply_scores


async def rescore_all() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Assessment).where(Assessment.status == "completed")
        )
        assessments = result.scalars().all()

        if not assessments:
            print("No completed assessments found.")
            return

        print(f"Rescoring {len(assessments)} completed assessment(s)...")
        updated = 0
        for assessment in assessments:
            findings_result = await db.execute(
                select(AssessmentFinding).where(AssessmentFinding.assessment_id == assessment.id)
            )
            findings = findings_result.scalars().all()
            if not findings:
                continue
            old_score = assessment.overall_score
            apply_scores(assessment, findings)
            new_score = assessment.overall_score
            print(f"  {assessment.id} ({assessment.tenant_id}): {old_score} -> {new_score}")
            updated += 1

        await db.commit()
        print(f"Done. {updated} assessment(s) rescored.")


if __name__ == "__main__":
    asyncio.run(rescore_all())
