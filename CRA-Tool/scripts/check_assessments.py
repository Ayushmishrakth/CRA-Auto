"""Check last assessment scores for WealthScape."""
import asyncio, sys
sys.path.insert(0, ".")

# import all models so SQLAlchemy relationships resolve
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
        result = await db.execute(
            select(Assessment)
            .where(Assessment.tenant_id == "fe4eff9a-f69c-48c0-921d-8006a6d5beb2")
            .order_by(desc(Assessment.created_at))
        )
        assessments = result.scalars().all()
        print(f"Total assessments for WealthScape: {len(assessments)}")
        for a in assessments[:5]:
            print(f"\n  ID: {a.id}")
            print(f"  status: {a.status}  overall_score: {a.overall_score}  created: {a.created_at}")
            if a.overall_score is not None:
                print(f"  identity: {a.identity_score}  security: {a.security_score}  compliance: {a.compliance_score}  collab: {a.collaboration_score}")


if __name__ == "__main__":
    asyncio.run(check())
