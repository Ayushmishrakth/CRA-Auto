#!/usr/bin/env python
"""
Test real report generation with actual database assessment data.
Fetches the latest assessment and generates a complete report.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.services.reporting.assessment_report_data_service import AssessmentReportDataService
from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator


async def test_report_generation():
    """Test real report generation with database data."""

    # Create async engine
    engine = create_async_engine(str(settings.DATABASE_URL))
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_delete=False
    )

    async with AsyncSessionLocal() as session:
        try:
            # Fetch latest assessment
            from sqlalchemy import select, desc
            from app.db.models.assessment import Assessment

            stmt = select(Assessment).order_by(desc(Assessment.created_at)).limit(1)
            result = await session.execute(stmt)
            assessment = result.scalar_one_or_none()

            if not assessment:
                print("ERROR: No assessments found in database")
                return False

            assessment_id = assessment.id
            print(f"Found assessment: {assessment_id}")
            print(f"  Status: {assessment.status}")
            print(f"  Score: {assessment.overall_score}")
            print(f"  Findings: {len(assessment.findings)}")

            # Fetch report data
            print("\nFetching assessment data for report...")
            report_data = await AssessmentReportDataService.get_assessment_report_data(
                session, assessment_id
            )

            print(f"Report data summary:")
            print(f"  Total findings: {report_data['summary']['total_parameters']}")
            print(f"  Pass/Fail: {report_data['summary']['pass_count']}/{report_data['summary']['fail_count']}")
            print(f"  Severity breakdown:")
            for severity in ['Critical', 'High', 'Medium', 'Low']:
                count = report_data['summary'].get(f'{severity.lower()}_count', 0)
                if count > 0:
                    print(f"    {severity}: {count}")

            # Generate report
            print("\nGenerating Word report...")
            gen = EnhancedReportGenerator(report_data)
            report_bytes = gen.generate()

            # Save to file
            output_dir = Path("reports")
            output_dir.mkdir(exist_ok=True)

            filename = f"CRA_Report_{report_data['tenant_name']}.docx"
            filepath = output_dir / filename
            with open(filepath, 'wb') as f:
                f.write(report_bytes.getvalue())

            print(f"Report saved: {filepath}")
            print(f"File size: {filepath.stat().st_size} bytes")

            # Try to convert to PDF
            try:
                from docx2pdf import convert
                pdf_path = output_dir / filename.replace('.docx', '.pdf')
                print(f"\nConverting to PDF...")
                convert(str(filepath), str(pdf_path))
                print(f"PDF saved: {pdf_path}")
            except ImportError:
                print("WARNING: docx2pdf not installed, skipping PDF conversion")
            except Exception as e:
                print(f"WARNING: PDF conversion failed: {e}")

            return True

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(test_report_generation())
    sys.exit(0 if success else 1)
