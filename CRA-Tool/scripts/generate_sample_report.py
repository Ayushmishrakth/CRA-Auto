"""
Generate Sample CRA Report - Demonstrates report generation with realistic data.

This script generates a professional Word and PDF report without requiring database access.
It uses sample assessment data to demonstrate the full report structure.

Usage:
    python scripts/generate_sample_report.py [--output-dir ./reports]
"""

import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.reporting.professional_report_generator import ProfessionalReportGenerator


def create_sample_assessment_data():
    """Create realistic sample assessment data."""

    # Sample findings data
    findings = [
        # Entra ID findings
        {'parameter_name': 'Custom Banned Password List', 'category': 'entra', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Custom-banned password list is currently not enforced.', 'risk': 'Weak or commonly used passwords increase the risk of account compromise.'},
        {'parameter_name': 'Restricted Access to Microsoft Entra Admin Centre', 'category': 'entra', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Best Practices', 'description': 'Access to the Microsoft Entra Admin Center is not restricted.', 'risk': 'Without strict access controls, unauthorised administrators may alter configurations.'},
        {'parameter_name': 'Emergency Access Accounts', 'category': 'entra', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Best Practices', 'description': 'No Break glass accounts are present.', 'risk': 'If emergency access accounts are not properly monitored, they can be exploited.'},
        {'parameter_name': 'Device without Compliance Policies', 'category': 'entra', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Best Practices', 'description': 'Intune is not being utilized.', 'risk': 'Devices that are not governed by compliance policies pose a significant security risk.'},
        {'parameter_name': 'Authentication Methods Enabled', 'category': 'entra', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'All authentication methods are enabled.', 'risk': 'Copilot depends on robust user identity verification.'},
        {'parameter_name': 'Tenant creation by non-admins', 'category': 'entra', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Best Practices', 'description': 'Non-Admin Users are not allowed to create tenants.', 'risk': 'Allowing non-administrators to create tenants can lead to unmanaged environments.'},
        {'parameter_name': 'Global Administrator Accounts', 'category': 'entra', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'There are a total of 3 Global Administrator accounts.', 'risk': 'An excessive number of unmonitored global admin accounts presents risk.'},
        {'parameter_name': 'Self-Service Password Reset Authentication', 'category': 'entra', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Self-Service Password Reset Authentication is enabled.', 'risk': 'Weak SSPR methods increase the risk of account takeovers.'},
        {'parameter_name': 'Tenant Collaboration Invitation', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Security', 'description': 'Set to allow invitation to any domain (most inclusive).', 'risk': 'Uncontrolled collaboration invitations can cause tenant sprawl.'},
        {'parameter_name': 'Administrator Consent Workflows', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Best Practices', 'description': 'User cannot request admin consent.', 'risk': 'Users may inadvertently grant permissions to malicious applications.'},
        {'parameter_name': 'CAP Policies for Risky Sign-Ins', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Governance', 'description': 'CAP policy for risky sign-ins is not enabled.', 'risk': 'Conditional Access Policies are critical for mitigating risky sign-ins.'},
        {'parameter_name': 'Conditional Access Policies (Exclusion)', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Best Practices', 'description': 'Conditional Access Policies have one excluded user.', 'risk': 'Excluding users from Conditional Access policies compromises identity security.'},
        {'parameter_name': 'User Consent for Applications', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Security', 'description': 'User consent for applications is not set.', 'risk': 'Permissive user consent settings can lead to widespread unauthorized access.'},
        {'parameter_name': 'Third-Party App Integrations', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Governance', 'description': 'Users are allowed to register third-party applications.', 'risk': 'Inadequately managed third-party applications can expose sensitive data.'},
        {'parameter_name': 'Users without MFA', 'category': 'entra', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'All MFA-capable users have MFA registered.', 'risk': 'The absence of MFA significantly weakens account security.'},
        {'parameter_name': 'Auto-expiration policy for M365 Groups', 'category': 'entra', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Auto-expiration policy for inactive groups is not configured.', 'risk': 'Inactive M365 Groups may retain sensitive data unnecessarily.'},
        {'parameter_name': 'Customer Lockbox', 'category': 'entra', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Customer Lockbox is not enabled.', 'risk': 'Without Customer Lockbox, Microsoft support engineers may access tenant data without approval.'},
        {'parameter_name': 'Guest Invite Settings', 'category': 'entra', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Anyone in the organisation can invite guest users.', 'risk': 'Permissive invitation settings may permit unintended guests to join.'},
        {'parameter_name': 'Guest Users count', 'category': 'entra', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'There are 0 guest users out of 14 total users.', 'risk': 'Many guest users increase exposure risk.'},
        {'parameter_name': 'User Information', 'category': 'entra', 'status': 'fail', 'severity': 'Low', 'pillar': 'Best Practices', 'description': 'User information details are not complete for all users.', 'risk': 'User profiles lacking accurate details may compromise Copilot relevance.'},
        {'parameter_name': 'Number of accounts enabled', 'category': 'entra', 'status': 'fail', 'severity': 'Low', 'pillar': 'Security', 'description': '9 accounts are enabled out of 14 accounts.', 'risk': 'Inactive accounts that remain enabled pose exposure risk.'},

        # Exchange findings
        {'parameter_name': 'Mailbox Status (Active/Inactive)', 'category': 'exchange', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Governance', 'description': '4 users out of 4 (100%) are active.', 'risk': 'Unused mailboxes can increase risk of exposing outdated data.'},
        {'parameter_name': 'External Storage providers in OWA', 'category': 'exchange', 'status': 'fail', 'severity': 'High', 'pillar': 'Security', 'description': 'Additional storage providers are allowed.', 'risk': 'Third-party storage services may allow Copilot to access uncontrolled content.'},
        {'parameter_name': 'Mailbox Storage usage', 'category': 'exchange', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'All mailboxes are in good condition.', 'risk': 'Excessive mailbox storage may cause Copilot to surface outdated content.'},
        {'parameter_name': 'Full Calendar Schedules', 'category': 'exchange', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Policy for individual sharing is set to least information shared.', 'risk': 'Sharing full calendar access externally may expose sensitive scheduling information.'},
        {'parameter_name': 'Number of Emails read/received', 'category': 'exchange', 'status': 'pass', 'severity': 'Informational', 'pillar': 'Best Practices', 'description': '4 out of 4 (100%) have read 70% of their mail.', 'risk': 'Copilot may analyse read emails for context-aware suggestions.'},
        {'parameter_name': 'Number of emails sent', 'category': 'exchange', 'status': 'pass', 'severity': 'Informational', 'pillar': 'Best Practices', 'description': '4 out of 4 (100%) have sent more than 30 mails.', 'risk': 'Sent emails are included in dataset accessible to Copilot.'},

        # Purview findings
        {'parameter_name': 'Audit Logs Enabled', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Audit logs are not currently enabled.', 'risk': 'Disabling audit logging prevents review and tracking of Copilot activities.'},
        {'parameter_name': 'Secure Score Percentage', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Secure score is only 66.84% (less than 80% standard).', 'risk': 'Low secure score reflects weak security practices.'},
        {'parameter_name': 'Sensitivity Labels configured and applied', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Sensitivity labels are not applied.', 'risk': 'Inconsistent label application prevents Copilot from respecting data boundaries.'},
        {'parameter_name': 'Sensitivity Labels applied to Teams', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'No sensitivity labels have been applied to Teams.', 'risk': 'Without proper labelling, Copilot may access sensitive content without controls.'},
        {'parameter_name': 'Compliance Score Overview', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Governance', 'description': 'Compliance score is only 51% (less than 80% standard).', 'risk': 'Low compliance score signals inadequate policy enforcement.'},
        {'parameter_name': 'Information Protection Labels', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Information Protection labels have not been applied.', 'risk': 'Without consistent label application, Copilot may expose unclassified data.'},
        {'parameter_name': 'DLP Rules configured', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Data Loss Prevention (DLP) rules are not configured.', 'risk': 'In the absence of DLP policies, Copilot may inadvertently expose sensitive information.'},
        {'parameter_name': 'Audit Log Retention Duration', 'category': 'purview', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'No Audit log retention duration.', 'risk': 'Insufficient retention durations may result in loss of critical risk signals.'},

        # Teams findings
        {'parameter_name': 'Copilot Integration Enabled', 'category': 'teams', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Governance', 'description': 'Copilot integration is enabled.', 'risk': 'If Copilot is not fully enabled, it signals incomplete readiness.'},
        {'parameter_name': 'Third Party apps allowed', 'category': 'teams', 'status': 'fail', 'severity': 'High', 'pillar': 'Governance', 'description': 'Third-party apps are allowed.', 'risk': 'Third-party applications may gain access to Copilot-generated content.'},
        {'parameter_name': 'Active/Inactive teams', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'No teams are inactive.', 'risk': 'Many active Teams expands data pool that Copilot interacts with.'},
        {'parameter_name': 'Minimum number of Owners', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'There are no teams that have less than 2 owners.', 'risk': 'Teams lacking minimum owners risk becoming orphaned.'},
        {'parameter_name': 'Teams with External Users', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'There are no teams with external users.', 'risk': 'External users increase risk of sensitive information being exposed.'},
        {'parameter_name': 'Meeting Policies Configuration', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'Recommended settings are configured.', 'risk': 'Inadequate meeting policies may allow Copilot to access unintended content.'},
        {'parameter_name': 'Orphan Teams', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'There are no orphan teams.', 'risk': 'Orphaned Teams without owners may hold sensitive unmanaged content.'},
        {'parameter_name': 'Teams with external guest as owner', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'No teams have external user assigned as owner.', 'risk': 'External owners reduce control over team settings.'},
        {'parameter_name': 'Meeting Transcription enabled', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'Meeting transcription is enabled.', 'risk': 'Enabled transcriptions create content that Copilot can process.'},
        {'parameter_name': 'Guest access Enabled/Disabled', 'category': 'teams', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Guest access on teams is enabled.', 'risk': 'Copilot may unintentionally expose internal content to guest users.'},
        {'parameter_name': 'Teams - Lobby Bypass', 'category': 'teams', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'Team lobby bypass set to Everyone in the Organization.', 'risk': 'Allowing participants to bypass lobby can lead to unauthorised access.'},
        {'parameter_name': 'Teams - File Storage Option', 'category': 'teams', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'File Storage options are enabled (Dropbox, Box, GoogleDrive, etc).', 'risk': 'Improper file storage configuration can route content to non-compliant locations.'},
        {'parameter_name': 'Active/Inactive Teams Users', 'category': 'teams', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': '0 out of 4 team users are active (0%).', 'risk': 'Inactive users who maintain access may have content surfaced by Copilot.'},
        {'parameter_name': 'Teams - Meeting Chat', 'category': 'teams', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'Meeting chats are enabled on global policy.', 'risk': 'Meeting chat messages may include sensitive information.'},
        {'parameter_name': 'Meeting Recording Retention Policies', 'category': 'teams', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'Meeting recordings are set to automatically expire after 120 days.', 'risk': 'Without enforcement, Copilot may continuously process outdated recordings.'},
        {'parameter_name': 'Teams - Channel Email Addresses', 'category': 'teams', 'status': 'fail', 'severity': 'Low', 'pillar': 'Governance', 'description': 'Teams-Channel Email Address is enabled.', 'risk': 'Publicly exposed channel emails can be exploited to inject content.'},

        # OneDrive findings
        {'parameter_name': 'External Sharing Settings', 'category': 'onedrive', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'External sharing is set to only people in your organization.', 'risk': 'Broadly enabled external sharing may expose sensitive content.'},
        {'parameter_name': 'Days to retain deleted users OneDrive', 'category': 'onedrive', 'status': 'pass', 'severity': 'Low', 'pillar': 'Governance', 'description': 'OneDrive retention for deleted users is set to 3650 days.', 'risk': 'Short retention periods may hinder data recovery and audit capabilities.'},
        {'parameter_name': 'Total Active users on OneDrive', 'category': 'onedrive', 'status': 'pass', 'severity': 'Informational', 'pillar': 'Governance', 'description': '4 out of 4 (100%) users have shown activity in the last 2 months.', 'risk': 'High activity increases volume of content Copilot may access.'},

        # SharePoint findings
        {'parameter_name': 'Permission Settings for anyone links', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Permission settings for anyone links is set to edit for both files and folders.', 'risk': 'Edit permissions on public links can lead to unauthorised changes and data manipulation.'},
        {'parameter_name': 'Sensitive SharePoint sites excluded from Copilot', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'No sites have been excluded from Copilot.', 'risk': 'Time-bound access helps mitigate long-term exposure risks.'},
        {'parameter_name': 'Sharing Settings (External/Internal)', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'External sharing is disabled.', 'risk': 'Excessively permissive sharing settings can expose sensitive files.'},
        {'parameter_name': 'SharePoint and OneDrive Guest Access Expiry', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Expiration Policy for guest access links is enabled and set for 90 days.', 'risk': 'Absence of expiry settings permits indefinite guest access.'},
        {'parameter_name': 'Expiration Policy for Anyone links', 'category': 'sharepoint', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'Expiration policy is set for 30 days.', 'risk': 'Time-bound access helps mitigate long-term exposure risks.'},
        {'parameter_name': 'Inactive Site Policies', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'No policy is set for inactive sites.', 'risk': 'Lack of ownership policies can result in unmanaged sites.'},
        {'parameter_name': 'Active Sites count', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Governance', 'description': '2 out of 10 (20%) sites are active.', 'risk': 'If sites are outdated or not properly governed, they may expose insecure information.'},
        {'parameter_name': 'Site Ownership policies', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'No policy is set for site ownership.', 'risk': 'Lack of ownership policies can result in unmanaged sites.'},
        {'parameter_name': 'Active Users on SharePoint', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Governance', 'description': '4 out of 4 (100%) users are active.', 'risk': 'Low user activity may result in Copilot surfacing irrelevant content.'},
        {'parameter_name': 'SharePoint - Modern Authentication', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'Apps using legacy authentication are disabled.', 'risk': 'Legacy protocols may expose data accessed by Copilot.'},
        {'parameter_name': 'Storage Quota Consumption', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Informational', 'pillar': 'Governance', 'description': 'Total storage consumption of the tenant is 545.11 GB out of 1.04 TB.', 'risk': 'Storage constraints increase risk of data being missed during Copilot indexing.'},
    ]

    # Calculate statistics
    total = len(findings)
    passed = sum(1 for f in findings if f['status'] == 'pass')
    failed = sum(1 for f in findings if f['status'] == 'fail')

    return {
        'id': str(uuid4()),
        'tenant_id': str(uuid4()),
        'tenant_name': 'WealthScape',
        'partner_name': 'Hawaii Tech Support',
        'created_at': datetime.now(),
        'overall_score': (passed / total * 100),
        'security_score': 35.0,
        'compliance_score': 42.0,
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


def main():
    """Generate sample report."""
    import os

    output_dir = './reports'

    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--output-dir' and len(sys.argv) > 2:
        output_dir = sys.argv[2]

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("[*] Generating Professional CRA Report...")
    print()

    # Create sample data
    print("[*] Preparing assessment data...")
    assessment_data = create_sample_assessment_data()
    print(f"    - Organization: {assessment_data['tenant_name']}")
    print(f"    - Findings: {assessment_data['summary']['total_parameters']} parameters")
    print(f"    - Failed: {assessment_data['summary']['fail_count']}")
    print(f"    - Overall Score: {assessment_data['overall_score']:.2f}%")
    print()

    # Generate Word report
    print("[*] Building Word document...")
    generator = ProfessionalReportGenerator(assessment_data)
    word_path = os.path.join(output_dir, f"CRA_Report_{assessment_data['tenant_name']}.docx")
    generator.save_word_report(word_path)
    print(f"    [OK] Saved: {word_path}")
    print()

    # Generate PDF
    print("[*] Converting to PDF...")
    try:
        from docx2pdf import convert
        pdf_path = word_path.replace('.docx', '.pdf')
        convert(word_path, pdf_path)
        print(f"    [OK] Saved: {pdf_path}")
    except Exception as e:
        print(f"    [!] PDF conversion skipped: {e}")

    print()
    print("[SUCCESS] Report generation completed!")
    print()
    print(f"[OUTPUT] {os.path.abspath(output_dir)}")


if __name__ == '__main__':
    main()
