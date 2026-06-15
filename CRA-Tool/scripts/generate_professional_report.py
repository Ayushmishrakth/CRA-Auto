"""
Professional Report Generation Script

Generates Word and PDF reports from real assessment data in the database.
This script uses the ProfessionalReportGenerator with actual assessment findings.

Usage:
    python scripts/generate_professional_report.py <assessment_id> [--output-dir ./reports]
"""

import sys
import os
from pathlib import Path
from uuid import UUID
import logging

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.services.reporting.assessment_report_service import AssessmentReportService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_report(assessment_id: str, output_dir: str = './reports', include_pdf: bool = True):
    """
    Generate Word and PDF reports for an assessment.

    Args:
        assessment_id: UUID of assessment
        output_dir: Directory to save reports
        include_pdf: Whether to generate PDF (requires docx2pdf)
    """
    try:
        assessment_uuid = UUID(assessment_id)
    except ValueError:
        logger.error(f"Invalid assessment ID: {assessment_id}")
        sys.exit(1)

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Initialize service
    service = AssessmentReportService()

    try:
        # Fetch assessment
        assessment = service.get_assessment_by_id(assessment_uuid)
        if not assessment:
            logger.error(f"Assessment {assessment_id} not found")
            sys.exit(1)

        logger.info(f"Found assessment: {assessment.id}")

        # Get findings
        findings = service.get_assessment_findings(assessment_uuid)
        logger.info(f"Found {len(findings)} findings")

        # Prepare tenant info
        tenant_info = {
            'tenant_name': 'Organization' if not hasattr(assessment, 'tenant_name') else assessment.tenant_name,
            'partner_name': 'Assessment Team',
        }

        # Generate Word report
        logger.info("Generating Word report...")
        word_path = os.path.join(output_dir, f'CRA_Report_{assessment.id}.docx')
        word_bytes = service.generate_word_report(assessment_uuid, tenant_info, word_path)
        logger.info(f"✓ Word report saved: {word_path}")

        # Generate PDF if requested
        if include_pdf:
            try:
                logger.info("Generating PDF report...")
                pdf_path = os.path.join(output_dir, f'CRA_Report_{assessment.id}.pdf')
                pdf_bytes = service.generate_pdf_report(assessment_uuid, tenant_info, pdf_path)
                logger.info(f"✓ PDF report saved: {pdf_path}")
            except ImportError as e:
                logger.warning(f"PDF generation skipped: {e}")

        logger.info("✓ Report generation completed successfully!")

    finally:
        service.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample:")
        print(f"  python scripts/generate_professional_report.py 550e8400-e29b-41d4-a716-446655440000")
        sys.exit(1)

    assessment_id = sys.argv[1]
    output_dir = './reports'

    # Parse optional arguments
    for i, arg in enumerate(sys.argv[2:]):
        if arg == '--output-dir' and i + 3 < len(sys.argv):
            output_dir = sys.argv[i + 3]

    generate_report(assessment_id, output_dir)
