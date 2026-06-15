#!/usr/bin/env python
"""
Simple check to see if assessments exist and what their status is.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    import app.db.base  # noqa - register all models
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.db.models.assessment import Assessment
    from app.db.models.assessment_finding import AssessmentFinding

    async with AsyncSessionLocal() as session:
        try:
            # Count total assessments
            stmt = select(func.count(Assessment.id))
            result = await session.execute(stmt)
            total = result.scalar()
            print(f"Total assessments: {total}")

            if total == 0:
                print("ERROR: No assessments in database!")
                return False

            # Get latest assessment
            stmt = select(Assessment).limit(1)
            result = await session.execute(stmt)
            assessment = result.scalar()

            if assessment:
                print(f"\nLatest assessment:")
                print(f"  ID: {assessment.id}")
                print(f"  Status: {assessment.status}")
                print(f"  Created: {assessment.created_at}")
                print(f"  Overall Score: {assessment.overall_score}")

                # Check findings
                stmt = select(func.count(AssessmentFinding.id)).where(
                    AssessmentFinding.assessment_id == assessment.id
                )
                result = await session.execute(stmt)
                finding_count = result.scalar()
                print(f"  Findings: {finding_count}")

                if finding_count == 0:
                    print("ERROR: Assessment has no findings!")
                    return False

                if assessment.status not in ['complete', 'success']:
                    print(f"WARNING: Assessment status is '{assessment.status}', not 'complete'")
                    print("       Consider waiting for assessment to complete")

                return True
            else:
                print("ERROR: Could not fetch assessment!")
                return False

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
