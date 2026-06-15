"""
Assessment Report Data Service
Fetches and aggregates real assessment data from the database for report generation.
"""

import uuid
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.cra_parameter import CraAssessmentResult, CraParameter
from app.db.models.tenant import ConnectedTenant

logger = logging.getLogger(__name__)

# Pillar mapping based on category
PILLAR_MAPPING = {
    'entra': {
        'governance': 'Governance',
        'security': 'Security',
        'best_practice': 'Best Practices',
    },
    'exchange': {
        'governance': 'Governance',
        'security': 'Security',
        'best_practice': 'Best Practices',
    },
    'purview': {
        'governance': 'Governance',
        'security': 'Security',
        'best_practice': 'Best Practices',
    },
    'teams': {
        'governance': 'Governance',
        'security': 'Security',
        'best_practice': 'Best Practices',
    },
    'onedrive': {
        'governance': 'Governance',
        'security': 'Security',
        'best_practice': 'Best Practices',
    },
    'sharepoint': {
        'governance': 'Governance',
        'security': 'Security',
        'best_practice': 'Best Practices',
    },
}

SERVICE_DISPLAY_NAMES = {
    'entra': 'ENTRA ID',
    'exchange': 'EXCHANGE ONLINE',
    'purview': 'MICROSOFT PURVIEW',
    'teams': 'MICROSOFT TEAMS',
    'onedrive': 'ONEDRIVE FOR BUSINESS',
    'sharepoint': 'SHAREPOINT ONLINE',
}

SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low', 'Informational', 'Info']


class AssessmentReportDataService:
    """Fetch and aggregate assessment data for report generation."""

    @staticmethod
    async def get_assessment_report_data(
        db: AsyncSession,
        assessment_id: uuid.UUID,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch complete assessment data and aggregate for report.

        Returns:
            Dict with all data needed for report generation:
            - assessment: Assessment record
            - tenant: Tenant record
            - findings: List of finding dicts with aggregated data
            - summary: Summary statistics
            - by_service: Findings grouped by service
            - by_severity: Findings grouped by severity
            - by_pillar: Findings grouped by pillar
        """
        try:
            logger.info(f"Fetching assessment data for {assessment_id}")

            # Fetch assessment with relationships (they have lazy="selectin" already)
            stmt = select(Assessment).where(Assessment.id == assessment_id)

            result = await db.execute(stmt)
            assessment = result.scalar_one_or_none()

            if not assessment:
                raise ValueError(f"Assessment {assessment_id} not found")

            logger.info(f"Found assessment with {len(assessment.findings)} findings")

            # Fetch tenant (ConnectedTenant with matching tenant_id)
            tenant_stmt = select(ConnectedTenant).where(ConnectedTenant.tenant_id == str(assessment.tenant_id))
            tenant_result = await db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()

            # Transform findings
            findings_list = []
            severity_counts = defaultdict(int)
            service_counts = defaultdict(lambda: {'pass': 0, 'fail': 0})
            pillar_counts = defaultdict(int)
            pass_count = 0
            fail_count = 0

            for finding in assessment.findings:
                finding_dict = AssessmentReportDataService._transform_finding(finding, tenant)
                findings_list.append(finding_dict)

                # Aggregate counts
                severity = finding_dict.get('severity', 'Informational')
                severity_counts[severity] += 1

                service = finding_dict.get('category', 'unknown').lower()
                if finding_dict.get('status') == 'pass':
                    service_counts[service]['pass'] += 1
                    pass_count += 1
                else:
                    service_counts[service]['fail'] += 1
                    fail_count += 1

                pillar = finding_dict.get('pillar', 'Best Practices')
                pillar_counts[pillar] += 1

            # Build summary
            total_parameters = len(findings_list)
            summary = {
                'tenant_id': str(assessment.tenant_id),
                'tenant_name': tenant.tenant_name if tenant else 'Unknown Tenant',
                'organization_name': tenant.tenant_name if tenant else 'Unknown Organization',
                'overall_score': assessment.overall_score or 0.0,
                'identity_score': assessment.identity_score,
                'security_score': assessment.security_score,
                'compliance_score': assessment.compliance_score,
                'collaboration_score': assessment.collaboration_score,
                'licensing_score': assessment.licensing_score,
                'total_parameters': total_parameters,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'total_checks': total_parameters,
                'critical_count': severity_counts.get('Critical', 0),
                'high_count': severity_counts.get('High', 0),
                'medium_count': severity_counts.get('Medium', 0),
                'low_count': severity_counts.get('Low', 0),
                'info_count': severity_counts.get('Informational', 0) + severity_counts.get('Info', 0),
                'copilot_eligible_users': assessment.copilot_eligible_user_count or 0,
                'assessment_date': assessment.created_at.isoformat() if assessment.created_at else datetime.now().isoformat(),
            }

            # Group by service
            findings_by_service = defaultdict(list)
            for finding in findings_list:
                service = finding.get('category', 'unknown').lower()
                findings_by_service[service].append(finding)

            # Group by pillar
            findings_by_pillar = defaultdict(list)
            for finding in findings_list:
                pillar = finding.get('pillar', 'Best Practices')
                findings_by_pillar[pillar].append(finding)

            # Build final data structure with only serializable data
            # (avoid passing ORM objects that may lose session context)
            report_data = {
                'assessment_id': str(assessment_id),
                'assessment': {
                    'id': str(assessment.id),
                    'tenant_id': str(assessment.tenant_id),
                    'status': assessment.status,
                    'overall_score': assessment.overall_score,
                    'created_at': assessment.created_at.isoformat() if assessment.created_at else None,
                },
                'tenant': {
                    'id': str(tenant.id) if tenant else None,
                    'name': tenant.tenant_name if tenant else 'Unknown Tenant',
                } if tenant else {'id': None, 'name': 'Unknown Tenant'},
                'tenant_name': tenant.tenant_name if tenant else 'Unknown Tenant',
                'partner_name': 'CRA Assessment Team',
                'created_at': assessment.created_at.isoformat() if assessment.created_at else None,
                'findings': findings_list,
                'summary': summary,
                'by_service': dict(findings_by_service),
                'by_severity': dict(severity_counts),
                'by_pillar': dict(pillar_counts),
                'service_distribution': dict(service_counts),
                'severity_distribution': {
                    'critical': severity_counts.get('Critical', 0),
                    'high': severity_counts.get('High', 0),
                    'medium': severity_counts.get('Medium', 0),
                    'low': severity_counts.get('Low', 0),
                    'info': severity_counts.get('Informational', 0) + severity_counts.get('Info', 0),
                },
                'analytics': {
                    'severity_distribution': {
                        'critical': severity_counts.get('Critical', 0),
                        'high': severity_counts.get('High', 0),
                        'medium': severity_counts.get('Medium', 0),
                        'low': severity_counts.get('Low', 0),
                        'info': severity_counts.get('Informational', 0) + severity_counts.get('Info', 0),
                    },
                    'service_distribution': dict(service_counts),
                    'pillar_distribution': dict(pillar_counts),
                },
            }

            logger.info(f"Aggregated {total_parameters} findings for report")
            return report_data

        except Exception as e:
            logger.error(f"Error fetching assessment report data: {e}", exc_info=True)
            raise

    @staticmethod
    def _transform_finding(finding: AssessmentFinding, tenant: Optional[ConnectedTenant]) -> Dict[str, Any]:
        """Transform a database AssessmentFinding into report format."""
        param = finding.parameter

        # Determine pillar from category and rule/parameter details
        category = param.category.lower() if param and param.category else 'unknown'

        # Map category to service for display
        service_key = category.split('_')[0] if '_' in category else category
        pillar = 'Best Practices'

        # Simple pillar assignment based on category or other heuristics
        if 'security' in category.lower():
            pillar = 'Security'
        elif 'governance' in category.lower() or 'compliance' in category.lower():
            pillar = 'Governance'
        else:
            pillar = 'Best Practices'

        # Normalize severity
        severity = finding.severity or 'Informational'
        if severity.lower() == 'info':
            severity = 'Informational'

        # Normalize status
        status = 'pass' if finding.status.lower() == 'pass' else 'fail'

        finding_dict = {
            'id': str(finding.id),
            'parameter_id': str(finding.parameter_id) if finding.parameter_id else None,
            'parameter_key': param.parameter_key if param else None,
            'parameter_name': param.parameter_name if param else 'Unknown Parameter',
            'category': category,
            'service': SERVICE_DISPLAY_NAMES.get(service_key, service_key.upper()),
            'severity': severity,
            'status': status,
            'pillar': pillar,
            'evaluated_value': finding.evaluated_value,
            'raw_value': finding.raw_value,
            'description': param.parameter_key if param else 'Parameter',
            'risk': f'This finding requires immediate attention based on {severity.lower()} severity rating.',
            'recommendation': f'Review and remediate this {severity.lower()} severity finding.',
        }

        return finding_dict

    @staticmethod
    def get_readiness_level(pass_count: int, total: int) -> str:
        """Determine readiness level based on pass rate."""
        if total == 0:
            return 'Incomplete'

        pass_rate = (pass_count / total) * 100

        if pass_rate >= 80:
            return 'Ready'
        elif pass_rate >= 50:
            return 'Partially Ready'
        else:
            return 'Not Ready'

    @staticmethod
    def get_readiness_description(readiness_level: str) -> str:
        """Get description for readiness level."""
        descriptions = {
            'Ready': 'The environment is ready for Copilot deployment with minimal additional work required.',
            'Partially Ready': 'The environment requires significant remediation before Copilot deployment.',
            'Not Ready': 'Substantial remediation is required prior to enabling Copilot in the production environment.',
            'Incomplete': 'Assessment incomplete - unable to determine readiness.',
        }
        return descriptions.get(readiness_level, 'Unable to determine readiness level.')
