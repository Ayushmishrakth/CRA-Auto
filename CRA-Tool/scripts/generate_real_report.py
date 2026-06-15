"""
Generate Real CRA Report with Actual Data and Charts

Generates professional Word and PDF reports using real assessment data from your database.
Includes severity-colored charts and complete structure.

Usage:
    python scripts/generate_real_report.py <assessment-id> [--output-dir ./reports]

Example:
    python scripts/generate_real_report.py 9c1e68c7-b730-4ace-8a59-9c10db3d7f3e
"""

import sys
import os
import logging
from pathlib import Path
from uuid import UUID
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    # Import all models to register them
    from app.db.models import (
        assessment,
        assessment_finding,
        assessment_job,
        assessment_parameter,
        assessment_recommendation,
        assessment_rule,
        assessment_event,
        assessment_artifact,
        assessment_report,
        user,
        tenant,
    )
    from app.db.models.assessment import Assessment
    from app.db.models.assessment_finding import AssessmentFinding
    from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator
except ImportError as e:
    logger.error(f"Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def get_sync_session():
    """Create synchronous database session."""
    try:
        # Convert async URL to sync
        db_url = settings.database_url
        if "aiosqlite" in db_url:
            db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
        elif "asyncpg" in db_url:
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None


def fetch_assessment_data(assessment_id: UUID, db_session) -> dict:
    """Fetch complete assessment data from database."""
    try:
        # Get assessment
        assessment = db_session.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            logger.error(f"Assessment {assessment_id} not found")
            return None

        logger.info(f"Found assessment: {assessment.id}")

        # Get findings
        findings_orm = db_session.query(AssessmentFinding).filter(
            AssessmentFinding.assessment_id == assessment_id
        ).all()

        logger.info(f"Found {len(findings_orm)} findings")

        # Convert ORM to dict
        findings = []
        for f in findings_orm:
            param = f.parameter
            finding_dict = {
                'parameter_name': param.parameter_name if param else 'Unknown',
                'category': param.category if param else 'unknown',
                'status': f.status,
                'severity': f.severity or 'Informational',
                'pillar': _map_to_pillar(param.category if param else None),
                'description': f.evaluated_value or 'Assessment data collected.',
                'risk': f'Risk assessment for {param.parameter_name if param else "this parameter"}.',
            }
            findings.append(finding_dict)

        # Calculate summary
        total = len(findings)
        passed = sum(1 for f in findings if f['status'] == 'pass')
        failed = sum(1 for f in findings if f['status'] == 'fail')

        return {
            'id': str(assessment.id),
            'tenant_id': str(assessment.tenant_id),
            'tenant_name': 'Organization',
            'partner_name': 'Assessment Team',
            'created_at': assessment.created_at,
            'overall_score': assessment.overall_score or 0.0,
            'findings': findings,
            'summary': {
                'total_parameters': total,
                'pass_count': passed,
                'fail_count': failed,
                'critical_count': sum(1 for f in findings if f['severity'] == 'Critical'),
                'high_count': sum(1 for f in findings if f['severity'] == 'High'),
                'medium_count': sum(1 for f in findings if f['severity'] == 'Medium'),
                'low_count': sum(1 for f in findings if f['severity'] == 'Low'),
            }
        }

    except Exception as e:
        logger.error(f"Error fetching assessment data: {e}")
        import traceback
        traceback.print_exc()
        return None


def _map_to_pillar(category: str) -> str:
    """Map category to CRA pillar."""
    pillar_map = {
        'entra': 'Security',
        'exchange': 'Governance',
        'purview': 'Governance',
        'teams': 'Governance',
        'onedrive': 'Best Practices',
        'sharepoint': 'Security',
    }
    return pillar_map.get(category.lower() if category else None, 'Best Practices')


def main():
    """Generate report from real assessment data."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Parse arguments
    assessment_id_str = sys.argv[1]
    output_dir = './reports'

    if '--output-dir' in sys.argv:
        idx = sys.argv.index('--output-dir')
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]

    # Validate UUID
    try:
        assessment_uuid = UUID(assessment_id_str)
    except ValueError:
        logger.error(f"Invalid assessment ID: {assessment_id_str}")
        sys.exit(1)

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info("[*] Connecting to database...")
    db_session = get_sync_session()
    if not db_session:
        logger.error("[!] Failed to connect to database")
        sys.exit(1)

    try:
        logger.info(f"[*] Fetching assessment data for {assessment_id_str}...")
        assessment_data = fetch_assessment_data(assessment_uuid, db_session)

        if not assessment_data:
            logger.error("[!] Failed to fetch assessment data")
            sys.exit(1)

        logger.info(f"    - Organization: {assessment_data.get('tenant_name')}")
        logger.info(f"    - Total Parameters: {assessment_data['summary']['total_parameters']}")
        logger.info(f"    - Failed: {assessment_data['summary']['fail_count']}")
        logger.info(f"    - Overall Score: {assessment_data['overall_score']:.2f}%")

        logger.info("[*] Generating Word report with charts...")
        generator = EnhancedReportGenerator(assessment_data)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        org_name = assessment_data.get('tenant_name', 'Assessment').replace(' ', '_')
        word_path = os.path.join(output_dir, f"CRA_Report_{org_name}_{timestamp}.docx")

        generator.save(word_path)
        logger.info(f"    [OK] Saved: {word_path}")

        # Generate PDF
        logger.info("[*] Converting to PDF...")
        try:
            from docx2pdf import convert
            pdf_path = word_path.replace('.docx', '.pdf')
            convert(word_path, pdf_path)
            logger.info(f"    [OK] Saved: {pdf_path}")
        except Exception as e:
            logger.warning(f"    [!] PDF conversion failed: {e}")

        logger.info("[SUCCESS] Report generation completed!")
        logger.info(f"[OUTPUT] {os.path.abspath(output_dir)}")

    finally:
        if db_session:
            db_session.close()


if __name__ == '__main__':
    main()
