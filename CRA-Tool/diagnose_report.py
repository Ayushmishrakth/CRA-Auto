#!/usr/bin/env python3
"""
Diagnostic script to test report generation with detailed logging.
Run this to see exactly where the logo is getting lost.
"""

import asyncio
import sys
import logging
from pathlib import Path
from uuid import UUID

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('report_diagnosis.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_report_generation():
    """Test report generation with a real assessment."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.db.session import get_db
    from app.services.reporting.assessment_report_data_service import AssessmentReportDataService
    from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator

    # Use the first assessment in the database for testing
    logger.info("=" * 80)
    logger.info("REPORT GENERATION DIAGNOSTIC TEST")
    logger.info("=" * 80)

    try:
        # Create database session
        from app.core.config import settings
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            # Get first assessment
            from app.db.models.assessment import Assessment
            from sqlalchemy import select

            result = await db.execute(select(Assessment).limit(1))
            assessment = result.scalars().first()

            if not assessment:
                logger.error("❌ No assessments found in database")
                return

            assessment_id = assessment.id
            logger.info(f"\n✅ Found assessment: {assessment_id}")
            logger.info(f"   Tenant: {assessment.tenant_name}")

            # Step 1: Fetch assessment data
            logger.info("\n[STEP 1] Fetching assessment data...")
            assessment_data = await AssessmentReportDataService.get_assessment_report_data(db, assessment_id)
            logger.info(f"✅ Fetched {len(assessment_data.get('findings', []))} findings")

            # Step 2: Create fake logo for testing
            logger.info("\n[STEP 2] Creating test logo...")
            logo_dir = Path("storage/logos")
            logo_dir.mkdir(parents=True, exist_ok=True)

            # Create a minimal PNG (1x1 transparent)
            test_logo_path = logo_dir / f"test_logo_{assessment_id}.png"
            test_png_data = (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
                b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            with open(test_logo_path, 'wb') as f:
                f.write(test_png_data)
            logger.info(f"✅ Created test logo: {test_logo_path}")
            logger.info(f"   File size: {test_logo_path.stat().st_size} bytes")
            logger.info(f"   Exists: {test_logo_path.exists()}")

            # Step 3: Apply customization
            logger.info("\n[STEP 3] Applying customization...")
            assessment_data['tenant_name'] = 'TEST_COMPANY_NAME'
            assessment_data['company_address'] = '123 TEST Street, Test City'
            assessment_data['logo_path'] = str(test_logo_path)
            logger.info(f"✅ Set company_name: {assessment_data.get('tenant_name')}")
            logger.info(f"✅ Set company_address: {assessment_data.get('company_address')}")
            logger.info(f"✅ Set logo_path: {assessment_data.get('logo_path')}")

            # Step 4: Generate report
            logger.info("\n[STEP 4] Generating report...")
            logger.info(f"   Passing logo_path to generator: {str(test_logo_path)}")

            gen = EnhancedReportGenerator(assessment_data, logo_path=str(test_logo_path))
            report_bytes = gen.generate()

            logger.info(f"✅ Report generated: {len(report_bytes.getvalue())} bytes")

            # Step 5: Save report for inspection
            logger.info("\n[STEP 5] Saving report to disk...")
            output_dir = Path("storage/reports")
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / f"diagnostic_report_{assessment_id}.docx"
            with open(output_path, 'wb') as f:
                f.write(report_bytes.getvalue())

            logger.info(f"✅ Report saved: {output_path}")
            logger.info(f"   File size: {output_path.stat().st_size} bytes")

            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("DIAGNOSTIC TEST COMPLETE")
            logger.info("=" * 80)
            logger.info(f"\n✅ Generated report: {output_path}")
            logger.info(f"✅ Open this file and check:")
            logger.info(f"   - Logo appears at top of cover page?")
            logger.info(f"   - Company name 'TEST_COMPANY_NAME' appears?")
            logger.info(f"   - Address '123 TEST Street, Test City' appears?")
            logger.info(f"\n✅ Check the console output above for [LOGO] messages")
            logger.info(f"✅ If logo is missing, check for [LOGO] ❌ messages")
            logger.info(f"\n📊 Log file: report_diagnosis.log")

    except Exception as e:
        logger.exception(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    logger.info("Starting diagnostic test...")
    asyncio.run(test_report_generation())
