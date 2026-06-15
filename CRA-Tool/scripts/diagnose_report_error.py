#!/usr/bin/env python
"""
Diagnose report generation errors by testing each step.
"""

import asyncio
import sys
import traceback
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, inspect

from app.config.settings import settings


async def diagnose():
    """Step-by-step diagnosis of report generation."""

    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)

    try:
        async with AsyncSessionLocal() as session:
            print("=" * 70)
            print("STEP 1: Check Database Connection")
            print("=" * 70)
            try:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                print("✓ Database connection OK")
            except Exception as e:
                print(f"✗ Database connection FAILED: {e}")
                return False

            print("\n" + "=" * 70)
            print("STEP 2: List All Tables")
            print("=" * 70)
            try:
                from sqlalchemy import inspect as sqla_inspect
                inspector = sqla_inspect(engine.sync_engine)
                tables = inspector.get_table_names()
                print(f"✓ Found {len(tables)} tables: {', '.join(tables[:10])}...")
            except Exception as e:
                print(f"✗ Failed to list tables: {e}")

            print("\n" + "=" * 70)
            print("STEP 3: Check Assessments Table")
            print("=" * 70)
            try:
                from app.db.models.assessment import Assessment
                stmt = select(Assessment).limit(1)
                result = await session.execute(stmt)
                assessment = result.scalar_one_or_none()

                if assessment:
                    print(f"✓ Found assessment: {assessment.id}")
                    print(f"  Status: {assessment.status}")
                    print(f"  Created: {assessment.created_at}")
                    print(f"  Findings count: {len(assessment.findings) if assessment.findings else 0}")
                    latest_assessment_id = assessment.id
                else:
                    print("✗ No assessments found in database")
                    return False
            except Exception as e:
                print(f"✗ Failed to query assessments: {e}")
                traceback.print_exc()
                return False

            print("\n" + "=" * 70)
            print("STEP 4: Check Assessment Findings")
            print("=" * 70)
            try:
                from app.db.models.assessment_finding import AssessmentFinding
                stmt = select(AssessmentFinding).where(
                    AssessmentFinding.assessment_id == latest_assessment_id
                ).limit(5)
                result = await session.execute(stmt)
                findings = result.scalars().all()

                print(f"✓ Found {len(findings)} findings (showing first 5)")
                for i, finding in enumerate(findings, 1):
                    print(f"  {i}. Status: {finding.status}, Severity: {finding.severity}")
                    if finding.parameter:
                        print(f"     Parameter: {finding.parameter.parameter_name}")
            except Exception as e:
                print(f"✗ Failed to query findings: {e}")
                traceback.print_exc()
                return False

            print("\n" + "=" * 70)
            print("STEP 5: Check Tenant")
            print("=" * 70)
            try:
                from app.db.models.tenant import Tenant
                stmt = select(Tenant).where(Tenant.id == assessment.tenant_id)
                result = await session.execute(stmt)
                tenant = result.scalar_one_or_none()

                if tenant:
                    print(f"✓ Found tenant: {tenant.name}")
                else:
                    print(f"✗ Tenant not found for ID: {assessment.tenant_id}")
            except Exception as e:
                print(f"✗ Failed to query tenant: {e}")
                traceback.print_exc()

            print("\n" + "=" * 70)
            print("STEP 6: Test Data Service Import")
            print("=" * 70)
            try:
                from app.services.reporting.assessment_report_data_service import AssessmentReportDataService
                print("✓ AssessmentReportDataService imported successfully")
            except Exception as e:
                print(f"✗ Failed to import data service: {e}")
                traceback.print_exc()
                return False

            print("\n" + "=" * 70)
            print("STEP 7: Test Data Service - Get Report Data")
            print("=" * 70)
            try:
                from app.services.reporting.assessment_report_data_service import AssessmentReportDataService

                print(f"Calling get_assessment_report_data() for assessment: {latest_assessment_id}")
                report_data = await AssessmentReportDataService.get_assessment_report_data(
                    session, latest_assessment_id
                )

                print(f"✓ Got report data successfully")
                print(f"  Tenant: {report_data.get('tenant_name')}")
                print(f"  Findings: {len(report_data.get('findings', []))}")
                print(f"  Summary stats:")
                summary = report_data.get('summary', {})
                print(f"    Total: {summary.get('total_parameters')}")
                print(f"    Pass/Fail: {summary.get('pass_count')}/{summary.get('fail_count')}")
                print(f"    Critical: {summary.get('critical_count')}")
                print(f"    High: {summary.get('high_count')}")

            except Exception as e:
                print(f"✗ Failed in data service: {e}")
                print("\nFull traceback:")
                traceback.print_exc()
                return False

            print("\n" + "=" * 70)
            print("STEP 8: Test Report Generator Import")
            print("=" * 70)
            try:
                from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator
                print("✓ EnhancedReportGenerator imported successfully")
            except Exception as e:
                print(f"✗ Failed to import generator: {e}")
                traceback.print_exc()
                return False

            print("\n" + "=" * 70)
            print("STEP 9: Test Report Generation")
            print("=" * 70)
            try:
                from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator

                print("Generating report from data...")
                gen = EnhancedReportGenerator(report_data)
                report_bytes = gen.generate()

                size = len(report_bytes.getvalue())
                print(f"✓ Report generated successfully")
                print(f"  Size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")

            except Exception as e:
                print(f"✗ Failed to generate report: {e}")
                print("\nFull traceback:")
                traceback.print_exc()
                return False

            print("\n" + "=" * 70)
            print("✓ ALL TESTS PASSED")
            print("=" * 70)
            print("\nReport generation should work via API.")
            print("If you still get 500 errors, check:")
            print("  1. Application logs for detailed error message")
            print("  2. Database connectivity from application context")
            print("  3. Assessment has status='complete' (not 'queued' or 'failed')")

            return True

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        traceback.print_exc()
        return False

    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(diagnose())
    sys.exit(0 if success else 1)
