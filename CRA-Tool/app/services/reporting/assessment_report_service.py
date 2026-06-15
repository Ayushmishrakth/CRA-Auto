"""
Assessment Report Service - fetches real assessment data from database and generates reports.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from collections import defaultdict

from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_parameter import AssessmentParameter
from app.services.reporting.professional_report_generator import ProfessionalReportGenerator


class AssessmentReportService:
    """Service to generate reports from assessment data in the database."""

    def __init__(self, db_session=None):
        """Initialize with optional database session (for testing/sync operations)."""
        self.db = db_session

    def get_assessment_by_id(self, assessment_id: UUID) -> Optional[Assessment]:
        """Fetch assessment from database."""
        return self.db.query(Assessment).filter(Assessment.id == assessment_id).first()

    def get_assessment_findings(self, assessment_id: UUID) -> list:
        """Fetch all findings for an assessment."""
        findings = self.db.query(AssessmentFinding).filter(
            AssessmentFinding.assessment_id == assessment_id
        ).all()
        return findings

    def enrich_finding_data(self, finding: AssessmentFinding) -> dict:
        """Convert ORM finding to dict with enriched data."""
        param = finding.parameter

        return {
            'id': str(finding.id),
            'assessment_id': str(finding.assessment_id),
            'parameter_key': param.parameter_key if param else None,
            'parameter_name': param.parameter_name if param else None,
            'category': param.category if param else None,
            'status': finding.status,
            'severity': finding.severity,
            'pillar': self._map_category_to_pillar(param.category if param else None),
            'description': self._get_parameter_description(param.parameter_key if param else None),
            'risk': self._get_parameter_risk(param.parameter_key if param else None),
            'evaluated_value': finding.evaluated_value,
            'raw_value': finding.raw_value,
            'collected_at': finding.collected_at,
            'evaluated_at': finding.evaluated_at,
        }

    def _map_category_to_pillar(self, category: str) -> str:
        """Map category to CRA Pillar (Security, Governance, Best Practices)."""
        pillar_mapping = {
            'entra': 'Security',
            'exchange': 'Security',
            'purview': 'Governance',
            'teams': 'Governance',
            'onedrive': 'Best Practices',
            'sharepoint': 'Security',
        }
        return pillar_mapping.get(category.lower() if category else None, 'Best Practices')

    def _get_parameter_description(self, param_key: str) -> str:
        """Get parameter description from parameter registry."""
        # This would load from parameters.json or database
        # For now, return a placeholder
        return f"Assessment of {param_key if param_key else 'parameter'}."

    def _get_parameter_risk(self, param_key: str) -> str:
        """Get parameter risk statement from parameter registry."""
        # This would load from parameters.json or database
        # For now, return a placeholder
        return f"Misconfiguration of {param_key if param_key else 'this parameter'} can impact security and compliance."

    def calculate_summary_stats(self, findings: list) -> dict:
        """Calculate summary statistics from findings."""
        total = len(findings)
        passed = sum(1 for f in findings if f.status == 'pass')
        failed = sum(1 for f in findings if f.status == 'fail')

        severity_counts = defaultdict(int)
        for f in findings:
            if f.severity:
                severity_counts[f.severity] += 1

        return {
            'total_parameters': total,
            'pass_count': passed,
            'fail_count': failed,
            'critical_count': severity_counts.get('Critical', 0),
            'high_count': severity_counts.get('High', 0),
            'medium_count': severity_counts.get('Medium', 0),
            'low_count': severity_counts.get('Low', 0),
        }

    def prepare_assessment_data(self, assessment_id: UUID, tenant_info: Optional[dict] = None) -> dict:
        """Prepare complete assessment data for report generation."""
        assessment = self.get_assessment_by_id(assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        # Get findings
        findings = self.get_assessment_findings(assessment_id)
        enriched_findings = [self.enrich_finding_data(f) for f in findings]

        # Calculate summary
        summary = self.calculate_summary_stats(findings)

        # Prepare data structure for report generator
        data = {
            'id': str(assessment.id),
            'tenant_id': str(assessment.tenant_id),
            'tenant_name': tenant_info.get('tenant_name', 'Organization') if tenant_info else 'Organization',
            'partner_name': tenant_info.get('partner_name', 'Assessment Team') if tenant_info else 'Assessment Team',
            'created_at': assessment.created_at,
            'overall_score': assessment.overall_score or 0.0,
            'security_score': assessment.security_score or 0.0,
            'compliance_score': assessment.compliance_score or 0.0,
            'findings': enriched_findings,
            'summary': summary,
        }

        return data

    def generate_word_report(
        self,
        assessment_id: UUID,
        tenant_info: Optional[dict] = None,
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        Generate Word report for assessment.

        Args:
            assessment_id: UUID of assessment
            tenant_info: Dict with tenant_name and partner_name
            output_path: Optional file path to save report

        Returns:
            Bytes of Word document
        """
        # Prepare data
        assessment_data = self.prepare_assessment_data(assessment_id, tenant_info)

        # Generate report
        generator = ProfessionalReportGenerator(assessment_data)
        report_bytes = generator.generate_word_report()

        # Save if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(report_bytes)

        return report_bytes

    def generate_pdf_report(
        self,
        assessment_id: UUID,
        tenant_info: Optional[dict] = None,
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        Generate PDF report for assessment.

        Uses word-to-pdf conversion.

        Args:
            assessment_id: UUID of assessment
            tenant_info: Dict with tenant_name and partner_name
            output_path: Optional file path to save report

        Returns:
            Bytes of PDF document
        """
        try:
            from docx2pdf import convert
            import tempfile

            # Generate Word report
            word_bytes = self.generate_word_report(assessment_id, tenant_info)

            # Save Word to temp file
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
                tmp.write(word_bytes)
                tmp_path = tmp.name

            # Convert to PDF
            pdf_path = tmp_path.replace('.docx', '.pdf')
            convert(tmp_path, pdf_path)

            # Read PDF
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            # Save if path provided
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)

            return pdf_bytes

        except ImportError:
            raise ImportError("docx2pdf not installed. Install with: pip install docx2pdf")

    def generate_both_reports(
        self,
        assessment_id: UUID,
        tenant_info: Optional[dict] = None,
        output_dir: Optional[str] = None,
    ) -> dict:
        """
        Generate both Word and PDF reports.

        Args:
            assessment_id: UUID of assessment
            tenant_info: Dict with tenant_name and partner_name
            output_dir: Optional directory to save reports

        Returns:
            Dict with 'word' and 'pdf' bytes
        """
        word_path = None
        pdf_path = None

        if output_dir:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            word_path = f"{output_dir}/CRA_Report_{timestamp}.docx"
            pdf_path = f"{output_dir}/CRA_Report_{timestamp}.pdf"

        word_bytes = self.generate_word_report(assessment_id, tenant_info, word_path)
        pdf_bytes = self.generate_pdf_report(assessment_id, tenant_info, pdf_path)

        return {
            'word': word_bytes,
            'pdf': pdf_bytes,
            'word_path': word_path,
            'pdf_path': pdf_path,
        }

    def close(self):
        """Close database session."""
        self.db.close()
