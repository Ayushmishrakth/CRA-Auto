"""Generate Enhanced Sample Report with Professional Charts and Structure"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator


def create_assessment_data():
    """Create assessment data matching your WealthScape assessment: 12 failed, 21 passed"""

    # Real-world assessment findings
    findings = [
        # ENTRA ID (21 total)
        {'parameter_name': 'Custom Banned Password List', 'category': 'entra', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Custom-banned password list is currently not enforced.', 'risk': 'Weak passwords increase account compromise risk.'},
        {'parameter_name': 'Restricted Access to Entra Admin Centre', 'category': 'entra', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Best Practices', 'description': 'Access to Microsoft Entra Admin Center is not restricted.', 'risk': 'Unauthorized configuration changes possible.'},
        {'parameter_name': 'Emergency Access Accounts', 'category': 'entra', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Best Practices', 'description': 'No break glass accounts present.', 'risk': 'No emergency access mechanism in place.'},
        {'parameter_name': 'Device Compliance Policies', 'category': 'entra', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Best Practices', 'description': 'Intune is not being utilized.', 'risk': 'Unmanaged devices pose security risk.'},
        {'parameter_name': 'Authentication Methods', 'category': 'entra', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'All authentication methods enabled.', 'risk': 'Robust identity verification in place.'},
        {'parameter_name': 'Tenant Creation Controls', 'category': 'entra', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Best Practices', 'description': 'Non-admin users cannot create tenants.', 'risk': 'Shadow IT prevented.'},
        {'parameter_name': 'Global Administrator Accounts', 'category': 'entra', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Only 3 global admin accounts.', 'risk': 'Admin access properly controlled.'},
        {'parameter_name': 'Self-Service Password Reset', 'category': 'entra', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'SSPR authentication is enabled.', 'risk': 'Users can securely reset passwords.'},
        {'parameter_name': 'Tenant Collaboration Invitation', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Security', 'description': 'Invitations allowed to any domain.', 'risk': 'Uncontrolled external collaboration.'},
        {'parameter_name': 'Administrator Consent Workflow', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Best Practices', 'description': 'User cannot request admin consent.', 'risk': 'Risky apps may be granted permissions.'},
        {'parameter_name': 'CAP for Risky Sign-Ins', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Governance', 'description': 'CAP policy not enabled for risky sign-ins.', 'risk': 'Compromised sessions not blocked.'},
        {'parameter_name': 'CAP Exclusions', 'category': 'entra', 'status': 'pass', 'severity': 'High', 'pillar': 'Best Practices', 'description': 'No users excluded from CAP.', 'risk': 'All users protected by policies.'},
        {'parameter_name': 'User Consent Settings', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Security', 'description': 'User consent for apps not restricted.', 'risk': 'Malicious apps can gain permissions.'},
        {'parameter_name': 'Third-Party App Registration', 'category': 'entra', 'status': 'fail', 'severity': 'High', 'pillar': 'Governance', 'description': 'Users allowed to register third-party apps.', 'risk': 'Unvetted apps can be integrated.'},
        {'parameter_name': 'MFA Enrollment', 'category': 'entra', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'All MFA-capable users have MFA.', 'risk': 'Strong authentication enforced.'},
        {'parameter_name': 'M365 Group Expiration', 'category': 'entra', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Auto-expiration policy not configured.', 'risk': 'Inactive groups retain sensitive data.'},
        {'parameter_name': 'Customer Lockbox', 'category': 'entra', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Customer Lockbox not enabled.', 'risk': 'Microsoft support can access tenant data.'},
        {'parameter_name': 'Guest Invite Settings', 'category': 'entra', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Anyone can invite guest users.', 'risk': 'Uncontrolled guest access.'},
        {'parameter_name': 'Guest Users Count', 'category': 'entra', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'No guest users present.', 'risk': 'Guest exposure minimized.'},
        {'parameter_name': 'User Information Completeness', 'category': 'entra', 'status': 'fail', 'severity': 'Low', 'pillar': 'Best Practices', 'description': 'User profiles lack complete information.', 'risk': 'Inaccurate organizational hierarchy.'},
        {'parameter_name': 'Enabled User Accounts', 'category': 'entra', 'status': 'pass', 'severity': 'Low', 'pillar': 'Security', 'description': '14 user accounts enabled appropriately.', 'risk': 'User access properly managed.'},

        # EXCHANGE ONLINE (6 total)
        {'parameter_name': 'Mailbox Status', 'category': 'exchange', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Governance', 'description': 'All mailboxes are active.', 'risk': 'Active monitoring in place.'},
        {'parameter_name': 'External Storage Providers', 'category': 'exchange', 'status': 'fail', 'severity': 'High', 'pillar': 'Security', 'description': 'Third-party storage allowed in OWA.', 'risk': 'Data governance reduced.'},
        {'parameter_name': 'Mailbox Storage Usage', 'category': 'exchange', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'All mailboxes in good condition.', 'risk': 'Storage properly managed.'},
        {'parameter_name': 'Calendar Sharing', 'category': 'exchange', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Calendar sharing properly restricted.', 'risk': 'Calendar data protected.'},
        {'parameter_name': 'Email Read Activity', 'category': 'exchange', 'status': 'pass', 'severity': 'Informational', 'pillar': 'Best Practices', 'description': 'High email read rate observed.', 'risk': 'Users engaged with email system.'},
        {'parameter_name': 'Email Send Activity', 'category': 'exchange', 'status': 'pass', 'severity': 'Informational', 'pillar': 'Best Practices', 'description': 'Healthy email send activity.', 'risk': 'Email communication active.'},

        # MICROSOFT PURVIEW (8 total)
        {'parameter_name': 'Audit Logs Enabled', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Audit logging is disabled.', 'risk': 'No activity tracking possible.'},
        {'parameter_name': 'Secure Score', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Score is 66.84% (below 80% standard).', 'risk': 'Security posture below baseline.'},
        {'parameter_name': 'Sensitivity Labels', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Labels not applied to content.', 'risk': 'Data classification missing.'},
        {'parameter_name': 'Teams Sensitivity Labels', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'No labels applied to Teams.', 'risk': 'Teams content unclassified.'},
        {'parameter_name': 'Compliance Score', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Governance', 'description': 'Score is 51% (below 80% standard).', 'risk': 'Compliance gaps exist.'},
        {'parameter_name': 'Information Protection Labels', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'IP labels not applied.', 'risk': 'Content protection incomplete.'},
        {'parameter_name': 'DLP Rules', 'category': 'purview', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'No DLP rules configured.', 'risk': 'Data loss not prevented.'},
        {'parameter_name': 'Audit Log Retention', 'category': 'purview', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'No retention duration set.', 'risk': 'Audit logs may be deleted.'},

        # MICROSOFT TEAMS (16 total)
        {'parameter_name': 'Copilot Integration', 'category': 'teams', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Governance', 'description': 'Copilot integration enabled.', 'risk': 'AI features available.'},
        {'parameter_name': 'Third-Party Apps', 'category': 'teams', 'status': 'fail', 'severity': 'High', 'pillar': 'Governance', 'description': 'Third-party apps allowed.', 'risk': 'Security surface expanded.'},
        {'parameter_name': 'Team Activity Status', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'All teams are active.', 'risk': 'Team collaboration ongoing.'},
        {'parameter_name': 'Team Owners', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'All teams have minimum owners.', 'risk': 'Teams properly governed.'},
        {'parameter_name': 'External Users in Teams', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'No external users in teams.', 'risk': 'External access limited.'},
        {'parameter_name': 'Meeting Policies', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'Recommended policies configured.', 'risk': 'Meetings properly secured.'},
        {'parameter_name': 'Orphan Teams', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'No orphan teams detected.', 'risk': 'Teams properly managed.'},
        {'parameter_name': 'External Owners', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'No external team owners.', 'risk': 'Owner control maintained.'},
        {'parameter_name': 'Meeting Transcription', 'category': 'teams', 'status': 'pass', 'severity': 'High', 'pillar': 'Governance', 'description': 'Meeting transcription enabled.', 'risk': 'Meetings documented.'},
        {'parameter_name': 'Guest Access', 'category': 'teams', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'Guest access enabled.', 'risk': 'Guest exposure possible.'},
        {'parameter_name': 'Lobby Bypass', 'category': 'teams', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'Lobby bypass set to organization.', 'risk': 'Meeting access not restricted.'},
        {'parameter_name': 'File Storage Options', 'category': 'teams', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Security', 'description': 'External storage options enabled.', 'risk': 'Files stored outside M365.'},
        {'parameter_name': 'Team User Activity', 'category': 'teams', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'Some team users inactive.', 'risk': 'Inactive accounts retain access.'},
        {'parameter_name': 'Meeting Chat', 'category': 'teams', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'Meeting chat enabled globally.', 'risk': 'Meeting communication available.'},
        {'parameter_name': 'Recording Retention', 'category': 'teams', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'Auto-expiry set to 120 days.', 'risk': 'Recording retention managed.'},
        {'parameter_name': 'Channel Email Address', 'category': 'teams', 'status': 'fail', 'severity': 'Low', 'pillar': 'Governance', 'description': 'Channel email addresses enabled.', 'risk': 'Email-based injection possible.'},

        # ONEDRIVE (3 total)
        {'parameter_name': 'External Sharing', 'category': 'onedrive', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'Sharing limited to organization.', 'risk': 'External sharing controlled.'},
        {'parameter_name': 'Deleted User Retention', 'category': 'onedrive', 'status': 'pass', 'severity': 'Low', 'pillar': 'Governance', 'description': 'Retention set to 3650 days.', 'risk': 'Data recovery possible.'},
        {'parameter_name': 'Active Users', 'category': 'onedrive', 'status': 'pass', 'severity': 'Informational', 'pillar': 'Governance', 'description': 'All users show recent activity.', 'risk': 'OneDrive actively used.'},

        # SHAREPOINT (11 total)
        {'parameter_name': 'Anyone Link Permissions', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Edit permissions on public links.', 'risk': 'Unauthorized modifications possible.'},
        {'parameter_name': 'Copilot Site Exclusions', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Critical', 'pillar': 'Security', 'description': 'No sites excluded from Copilot.', 'risk': 'Sensitive sites accessible to Copilot.'},
        {'parameter_name': 'External Sharing', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'External sharing disabled.', 'risk': 'External access prevented.'},
        {'parameter_name': 'Guest Link Expiry', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Critical', 'pillar': 'Security', 'description': 'Guest links expire in 90 days.', 'risk': 'Time-bound access enforced.'},
        {'parameter_name': 'Anyone Link Expiry', 'category': 'sharepoint', 'status': 'pass', 'severity': 'High', 'pillar': 'Security', 'description': 'Links expire in 30 days.', 'risk': 'Link access time-limited.'},
        {'parameter_name': 'Inactive Site Policies', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'No policy for inactive sites.', 'risk': 'Inactive sites may accumulate data.'},
        {'parameter_name': 'Active Sites Count', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Governance', 'description': '2 of 10 sites are active (20%).', 'risk': 'Most sites inactive.'},
        {'parameter_name': 'Site Ownership Policies', 'category': 'sharepoint', 'status': 'fail', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'No site ownership policy.', 'risk': 'Sites may be unmanaged.'},
        {'parameter_name': 'Active Users on SharePoint', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Governance', 'description': 'All users show activity.', 'risk': 'SharePoint actively used.'},
        {'parameter_name': 'Modern Authentication', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Medium', 'pillar': 'Best Practices', 'description': 'Legacy auth disabled.', 'risk': 'Modern security in place.'},
        {'parameter_name': 'Storage Quota', 'category': 'sharepoint', 'status': 'pass', 'severity': 'Informational', 'pillar': 'Governance', 'description': '545.11 GB of 1.04 TB used.', 'risk': 'Storage adequate.'},
    ]

    return {
        'id': 'assessment-demo',
        'tenant_id': '9c1e68c7-b730-4ace-8a59-9c10db3d7f3e',
        'tenant_name': 'WealthScape',
        'partner_name': 'Hawaii Tech Support',
        'created_at': datetime.now(),
        'overall_score': 46.15,
        'findings': findings,
        'summary': {
            'total_parameters': len(findings),
            'pass_count': sum(1 for f in findings if f['status'] == 'pass'),
            'fail_count': sum(1 for f in findings if f['status'] == 'fail'),
            'critical_count': sum(1 for f in findings if f['severity'] == 'Critical'),
            'high_count': sum(1 for f in findings if f['severity'] == 'High'),
            'medium_count': sum(1 for f in findings if f['severity'] == 'Medium'),
            'low_count': sum(1 for f in findings if f['severity'] == 'Low'),
        }
    }


if __name__ == '__main__':
    import os

    output_dir = './reports'
    if len(sys.argv) > 1 and sys.argv[1] == '--output-dir' and len(sys.argv) > 2:
        output_dir = sys.argv[2]

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("[*] Creating enhanced report with charts and colors...")
    data = create_assessment_data()

    print(f"    - Organization: {data['tenant_name']}")
    print(f"    - Total Parameters: {data['summary']['total_parameters']}")
    print(f"    - Failed: {data['summary']['fail_count']} (Not Ready)")
    print(f"    - Passed: {data['summary']['pass_count']}")

    print("[*] Generating Word document with severity charts...")
    generator = EnhancedReportGenerator(data)

    word_file = os.path.join(output_dir, 'CRA_Report_WealthScape_Professional.docx')
    generator.save(word_file)
    print(f"    [OK] {word_file}")

    print("[*] Converting to PDF...")
    try:
        from docx2pdf import convert
        pdf_file = word_file.replace('.docx', '.pdf')
        convert(word_file, pdf_file)
        print(f"    [OK] {pdf_file}")
    except Exception as e:
        print(f"    [!] PDF: {e}")

    print("\n[SUCCESS] Professional report generated!")
    print(f"[OUTPUT] {os.path.abspath(output_dir)}")
