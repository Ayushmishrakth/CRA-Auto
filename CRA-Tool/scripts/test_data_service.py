#!/usr/bin/env python
"""
Test the AssessmentReportDataService with a real assessment.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    import app.db.base  # noqa
    from app.db.session import AsyncSessionLocal
    from app.services.reporting.assessment_report_data_service import AssessmentReportDataService

    assessment_id = UUID("0e0bac3d-3f17-468d-9aad-6b70b0d283ac")

    async with AsyncSessionLocal() as session:
        try:
            print(f"Testing AssessmentReportDataService with {assessment_id}")
            print("=" * 70)

            # Call the service
            report_data = await AssessmentReportDataService.get_assessment_report_data(
                session, assessment_id
            )

            print("\nOK: Data service succeeded!")
            print("\nReport Data Keys:", list(report_data.keys()))
            print("\nTenant Name:", report_data.get('tenant_name'))
            print("Findings Count:", len(report_data.get('findings', [])))
            print("\nSummary:")
            summary = report_data.get('summary', {})
            print(f"  Total Parameters: {summary.get('total_parameters')}")
            print(f"  Pass/Fail: {summary.get('pass_count')}/{summary.get('fail_count')}")
            print(f"  Severity:")
            print(f"    Critical: {summary.get('critical_count')}")
            print(f"    High: {summary.get('high_count')}")
            print(f"    Medium: {summary.get('medium_count')}")
            print(f"    Low: {summary.get('low_count')}")

            print("\nService Distribution:")
            for service, counts in report_data.get('service_distribution', {}).items():
                print(f"  {service}: {counts['pass']}/{counts['fail']}")

            print("\nFirst 3 Findings:")
            for idx, finding in enumerate(report_data.get('findings', [])[:3], 1):
                print(f"  {idx}. {finding.get('parameter_name')} - {finding.get('status')} ({finding.get('severity')})")

            return True

        except Exception as e:
            print(f"\nERROR: Data service FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
