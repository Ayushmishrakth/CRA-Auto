#!/usr/bin/env python
"""
Find a completed assessment with findings.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    import app.db.base  # noqa
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.db.models.assessment import Assessment
    from app.db.models.assessment_finding import AssessmentFinding

    async with AsyncSessionLocal() as session:
        try:
            # Find assessments with findings
            stmt = (
                select(Assessment)
                .join(AssessmentFinding, Assessment.id == AssessmentFinding.assessment_id, isouter=True)
                .group_by(Assessment.id)
                .having(func.count(AssessmentFinding.id) > 0)
                .limit(10)
            )
            result = await session.execute(stmt)
            assessments = result.scalars().all()

            if not assessments:
                print("No assessments with findings found!")
                print("\nTrying different approach - check all assessments:")

                stmt = select(Assessment).limit(10)
                result = await session.execute(stmt)
                assessments = result.scalars().all()

                for idx, a in enumerate(assessments, 1):
                    print(f"{idx}. ID: {a.id}")
                    print(f"   Status: {a.status}")
                    print(f"   Findings: {len(a.findings) if a.findings else 0}")
                    print()

                return False

            print(f"Found {len(assessments)} assessments with findings:\n")

            for idx, assessment in enumerate(assessments, 1):
                # Count findings for this assessment
                stmt = select(func.count(AssessmentFinding.id)).where(
                    AssessmentFinding.assessment_id == assessment.id
                )
                result = await session.execute(stmt)
                finding_count = result.scalar()

                print(f"{idx}. Assessment ID: {assessment.id}")
                print(f"   Status: {assessment.status}")
                print(f"   Created: {assessment.created_at}")
                print(f"   Findings: {finding_count}")
                print(f"   Score: {assessment.overall_score}")
                print()

            return True

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
