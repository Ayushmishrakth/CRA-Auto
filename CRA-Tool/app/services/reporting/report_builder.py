"""
CRA Report Builder - Complete 50-page professional DOCX report with charts and detailed findings.
Uses exact database field names from AssessmentFinding and AssessmentParameter models.
"""

from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
import tempfile
import os
import logging

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

logger = logging.getLogger(__name__)

SERVICE_ORDER = [
    "Entra ID",
    "Exchange Online",
    "Microsoft Purview",
    "Teams",
    "OneDrive",
    "SharePoint",
]


# ============================================================================
# CHART FUNCTIONS - Using matplotlib
# ============================================================================

def _create_pie_chart(labels, values, colors, title, width=5, height=4):
    """Create pie chart PNG and return path."""
    # Filter out zero values
    filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if not filtered:
        return None

    fl, fv, fc = zip(*filtered)
    fig, ax = plt.subplots(figsize=(width, height))
    ax.pie(fv, labels=fl, colors=fc, autopct='%1.0f%%',
           startangle=90, textprops={'fontsize': 10})
    ax.set_title(title, fontsize=12, fontweight='bold')
    plt.tight_layout()

    path = tempfile.mktemp(suffix='.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path


def _create_bar_chart(labels, values, colors, title):
    """Create horizontal bar chart PNG and return path."""
    if not any(values):
        return None

    fig, ax = plt.subplots(figsize=(7, 3))
    bars = ax.barh(labels, values, color=colors)
    ax.bar_label(bars, padding=3, fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlim(0, max(values) * 1.15 if max(values) > 0 else 10)
    plt.tight_layout()

    path = tempfile.mktemp(suffix='.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path


def _create_doughnut_chart(percentage, label):
    """Create small doughnut chart PNG and return path."""
    fig, ax = plt.subplots(figsize=(2.2, 2.2))
    values = [percentage, 100 - percentage]
    colors = ['#00B050', '#D3D3D3']
    ax.pie(values, colors=colors, startangle=90,
           wedgeprops=dict(width=0.5, edgecolor='white'))
    ax.text(0, 0, f'{percentage}%', ha='center', va='center',
            fontsize=12, fontweight='bold')
    ax.set_title(label, fontsize=9, pad=5)
    plt.tight_layout()

    path = tempfile.mktemp(suffix='.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _set_cell_bg(cell, hex_color):
    """Set table cell background color."""
    if not hex_color:
        return
    hex_color = hex_color.lstrip('#')
    fill = OxmlElement('w:shd')
    fill.set(qn('w:fill'), hex_color)
    cell._element.get_or_add_tcPr().append(fill)


def _add_image(doc, image_path, width_inches=4):
    """Add image to document centered."""
    if not image_path or not os.path.exists(image_path):
        return
    try:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(image_path, width=Inches(width_inches))
    except Exception as e:
        logger.warning(f"Failed to add image: {e}")
    finally:
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass


def _format_date(date_value):
    """Format date as DD-MM-YYYY."""
    if not date_value:
        return datetime.now().strftime('%d-%m-%Y')
    if isinstance(date_value, datetime):
        return date_value.strftime('%d-%m-%Y')
    try:
        dt = datetime.fromisoformat(str(date_value)[:19])
        return dt.strftime('%d-%m-%Y')
    except:
        return str(date_value)[:10]


def _add_heading1(doc, text):
    """Add Heading 1."""
    h = doc.add_heading(text, level=1)
    for run in h.runs:
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102)
    return h


def _add_heading2(doc, text):
    """Add Heading 2."""
    h = doc.add_heading(text, level=2)
    for run in h.runs:
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102)
    return h


def _add_heading3(doc, text):
    """Add Heading 3."""
    h = doc.add_heading(text, level=3)
    for run in h.runs:
        run.font.size = Pt(11)
        run.font.bold = True
    return h


# ============================================================================
# PAGE BUILDERS
# ============================================================================

def _add_cover_page(doc, company_name, logo_path, assessment_date):
    """PAGE 1: Cover page with dark navy background."""
    # Create navy background table
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    cell.width = Inches(6.5)

    # Set background color
    _set_cell_bg(cell, '003366')

    # Set row height to full page
    tr = table.rows[0]._tr
    trPr = tr.get_or_add_trPr()
    trHeight = OxmlElement('w:trHeight')
    trHeight.set(qn('w:val'), '10000')
    trHeight.set(qn('w:hRule'), 'exact')
    trPr.append(trHeight)

    # Clear default paragraph
    cell.paragraphs[0].text = ''

    # Add logo if exists
    if logo_path and os.path.exists(str(logo_path)):
        p = cell.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        try:
            p.add_run().add_picture(str(logo_path), width=Inches(2.2))
        except:
            pass

    # Spacing
    cell.add_paragraph()
    cell.add_paragraph()

    # Title
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('Copilot Readiness Assessment')
    r.font.size = Pt(28)
    r.font.bold = True
    r.font.color.rgb = RGBColor(255, 255, 255)

    # Company name
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"Prepared for: {company_name}")
    r.font.size = Pt(16)
    r.font.color.rgb = RGBColor(255, 255, 255)

    # Assessment date
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"Assessment date: {_format_date(assessment_date)}")
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor(255, 255, 255)

    # Prepared by
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Prepared by: CRA Tool")
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor(200, 200, 200)

    doc.add_page_break()


def _add_toc_page(doc):
    """PAGE 2: Table of Contents."""
    _add_heading1(doc, "Table of Contents")
    doc.add_paragraph()

    entries = [
        ("Executive Summary", "3"),
        ("Purpose", "3"),
        ("Evaluation Summary", "4"),
        ("3 Pillars of Microsoft 365 Copilot Readiness Assessment", "4"),
        ("M365 Services assessed in CRA", "4"),
        ("Risk Category of Parameters Assessed", "4"),
        ("Summary of Assessment", "5"),
        ("Key Observations", "5"),
        ("Risks of Immediate Deployment", "6"),
        ("Recommendations", "6"),
        ("Detailed Assessment", "7"),
        ("Conclusion", "50"),
    ]

    for title, page in entries:
        p = doc.add_paragraph(title, style='List Bullet')
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.right_indent = Inches(0)
        p.add_run(f" ........................... {page}").font.size = Pt(11)

    doc.add_page_break()


def _add_executive_summary_page(doc, company_name, partner_name):
    """PAGE 3: Executive Summary and Purpose."""
    _add_heading1(doc, "Executive Summary")

    doc.add_paragraph(
        f"As part of its digital transformation strategy, {company_name} engaged {partner_name} "
        "for a Copilot Readiness Assessment. The purpose of this engagement was to evaluate the Client's "
        "Microsoft 365 environment across areas including security, governance, and best practices to "
        "determine readiness for the secure and responsible adoption of Microsoft 365 Copilot."
    )

    doc.add_paragraph(
        "The assessment covered critical services including Entra ID, Exchange Online, Microsoft Teams, "
        "SharePoint Online, OneDrive for Business, and Microsoft Purview. It aimed to identify configuration "
        "gaps, policy misalignments, and potential vulnerabilities that could impact the responsible use of "
        "AI-powered tools like Copilot."
    )

    doc.add_paragraph(
        f"The findings serve as a strategic foundation for {company_name} to enhance its digital workplace, "
        "mitigate operational and compliance risks, and unlock the full potential of Microsoft 365 Copilot."
    )

    doc.add_paragraph()
    _add_heading1(doc, "Purpose")

    purposes = [
        "Evaluate the environment for alignment with industry best practices.",
        "Assess the environment across Microsoft 365 products and services like SharePoint, Teams, OneDrive for Business etc.",
        "Identify gaps that could pose security or compliance risks upon integrating Copilot.",
        "Establish a baseline for future audits and compliance tracking related to AI usage within Microsoft 365.",
        "Highlight licensing readiness and user eligibility for Microsoft 365 Copilot deployment.",
        "Provide a risk-based prioritization of remediation efforts to guide Copilot enablement planning.",
        "Offer actionable insights to strengthen governance, data protection, and identity management in preparation for AI integration.",
        "Support strategic decision-making by outlining Copilot deployment prerequisites and dependencies.",
    ]

    for purpose in purposes:
        doc.add_paragraph(purpose, style='List Bullet')

    doc.add_page_break()


def _add_evaluation_summary_page(doc, findings):
    """PAGE 4: Evaluation Summary with charts and tables."""
    _add_heading1(doc, "Evaluation Summary")

    # 3 Pillars Table
    _add_heading2(doc, "3 Pillars of Microsoft 365 Copilot Readiness Assessment")
    table = doc.add_table(rows=1, cols=3)

    for i, pillar in enumerate(['GOVERNANCE', 'SECURITY', 'BEST PRACTICES']):
        cell = table.rows[0].cells[i]
        _set_cell_bg(cell, '003366')
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(pillar)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)
        r.font.size = Pt(14)

    doc.add_paragraph()

    # M365 Services Table
    _add_heading2(doc, "M365 Services assessed in CRA")
    table = doc.add_table(rows=3, cols=2)

    services_grid = [
        ['Entra ID', 'Exchange Online'],
        ['Microsoft Purview', 'Microsoft Teams'],
        ['OneDrive for Business', 'SharePoint Online']
    ]

    for row_idx, row_services in enumerate(services_grid):
        for col_idx, service in enumerate(row_services):
            cell = table.rows[row_idx].cells[col_idx]
            _set_cell_bg(cell, 'D6E4F0')
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(service)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0, 51, 102)

    doc.add_paragraph()

    # Risk Score Matrix
    _add_heading2(doc, "Risk Score Matrix")
    doc.add_paragraph(
        "The findings presented in this report are graded according to the following levels of severity:"
    )

    table = doc.add_table(rows=1, cols=5)
    severity_levels = [
        ('CRITICAL', 'FF0000'),
        ('HIGH', 'FF6600'),
        ('MEDIUM', 'FFA500'),
        ('LOW', 'FFD700'),
        ('INFORMATIONAL', '808080'),
    ]

    for i, (label, color) in enumerate(severity_levels):
        cell = table.rows[0].cells[i]
        _set_cell_bg(cell, color)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(label)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)
        r.font.size = Pt(11)

    doc.add_paragraph()

    # Risk Category Pie Chart
    _add_heading2(doc, "Risk Category of Parameters Assessed")
    doc.add_paragraph(
        "The following chart provides consolidated parameters based on risk category assessed during the engagement:"
    )

    severity_counts = Counter()
    for f in findings:
        severity = f.get('severity', 'Informational')
        severity_counts[severity] += 1

    labels = ['Critical', 'High', 'Medium', 'Low', 'Informational']
    values = [severity_counts.get(l, 0) for l in labels]
    colors = ['#FF0000', '#FF6600', '#FFA500', '#FFD700', '#808080']

    chart_path = _create_pie_chart(labels, values, colors, "Risk-wise Parameters")
    if chart_path:
        _add_image(doc, chart_path, width_inches=4)

    doc.add_page_break()


def _add_summary_assessment_page(doc, findings, assessment_data):
    """PAGE 5: Summary of Assessment with charts."""
    _add_heading1(doc, "Summary of Assessment")

    assessment = assessment_data.get('assessment')
    summary = assessment_data.get('summary', {})

    doc.add_paragraph(
        "The Copilot Readiness Assessment uncovered several configuration gaps and policy deficiencies "
        "that could impact the secure and compliant adoption of Microsoft Copilot. Each finding has been "
        "categorized by severity and mapped to specific areas of risk within the Microsoft 365 environment."
    )

    # Count pass/fail
    pass_count = len([f for f in findings if f.get('status') == 'pass'])
    fail_count = len([f for f in findings if f.get('status') != 'pass'])
    total_count = len(findings)

    readiness_pct = int((pass_count / total_count * 100)) if total_count > 0 else 0
    readiness_level = 'Ready' if readiness_pct >= 50 else 'Not Ready'

    p = doc.add_paragraph()
    p.add_run("Overall Readiness: ").bold = True

    doc.add_paragraph(
        f"Based on the findings, the Client's current readiness level for Copilot integration is assessed as:"
    )

    p = doc.add_paragraph()
    r = p.add_run(f"Readiness Level: {readiness_level}")
    r.bold = True
    r.font.color.rgb = RGBColor(255, 0, 0) if readiness_level == 'Not Ready' else RGBColor(0, 176, 80)
    r.font.size = Pt(12)

    p = doc.add_paragraph()
    r = p.add_run(f"Readiness Gaps: {fail_count} out of {total_count}")
    r.bold = True
    r.font.size = Pt(12)

    doc.add_paragraph(
        "Significant remediation is required prior to enabling Copilot in the production environment."
    )

    doc.add_paragraph()

    # Overall Readiness Chart
    chart_path = _create_bar_chart(['Pass', 'Fail'], [pass_count, fail_count],
                                   ['#00B050', '#FF0000'], "Overall Readiness")
    if chart_path:
        _add_image(doc, chart_path, width_inches=5)

    doc.add_paragraph()

    # Key Observations
    _add_heading2(doc, "Key Observations:")

    observations = [
        f"A total of {fail_count} gaps out of {total_count} parameters were identified, distributed across Security, Governance, and Best Practice categories.",
        "Medium to Critical severity issues make up most of the findings, indicating substantial exposure to operational and compliance risks.",
        "Gap findings reveal significant exposure across the Security, Governance, and Best Practices pillars.",
        f"Current environment readiness score: {readiness_pct}% (Pass parameters: {pass_count}).",
    ]

    for obs in observations:
        doc.add_paragraph(obs, style='List Bullet')

    doc.add_paragraph()

    # Risks section
    _add_heading2(doc, "Risks of Immediate Deployment:")
    doc.add_paragraph(
        "Proceeding with Copilot activation in the current state may lead to:"
    )

    risks = [
        "Data exposure through inadequate sensitivity labelling",
        "Compliance violations due to policy gaps",
        "Security vulnerabilities from weak identity controls",
        "Operational risks from misconfigured environments",
    ]

    for risk in risks:
        doc.add_paragraph(risk, style='List Bullet')

    doc.add_paragraph()

    # Recommendations
    _add_heading2(doc, "Recommendations:")

    recommendations = [
        "Remediation of identified gaps: Address all findings regardless of severity to meet cybersecurity baseline standards.",
        "Postpone Deployment: Due to the current maturity level of the environment, it is recommended to adopt Copilot deployment after all critical and high-priority gaps are resolved.",
        "Futureproofing: Implementing the recommendations provided will reduce security risks and ensure regulatory compliance during and after Copilot integration.",
    ]

    for rec in recommendations:
        doc.add_paragraph(rec, style='List Bullet')

    doc.add_page_break()


def _add_detailed_assessment_pages(doc, assessment_data):
    """PAGES 6+: Detailed Assessment - All 65 findings grouped by service."""
    _add_heading1(doc, "Detailed Assessment")

    doc.add_paragraph(
        "The following sections provide a comprehensive summary of all findings discovered during the engagement:"
    )
    doc.add_paragraph()

    parameter_rows = assessment_data.get('parameter_rows', [])
    sections = assessment_data.get('sections', {})

    if not parameter_rows:
        doc.add_paragraph("No findings to display.")
        doc.add_page_break()
        return

    # Group parameter_rows by service for detailed display
    grouped_by_service = defaultdict(list)
    for row in parameter_rows:
        service = row.get('service', 'General')
        grouped_by_service[service].append(row)

    # Process each service in order
    for service in SERVICE_ORDER:
        if service not in grouped_by_service:
            continue

        service_rows = grouped_by_service[service]

        # Service heading
        _add_heading2(doc, service)

        # Service summary table
        table = doc.add_table(rows=len(service_rows) + 1, cols=5)
        table.style = 'Table Grid'

        # Header row
        headers = ['S.No', 'Parameter', 'CRA Pillar', 'Finding', 'Severity']
        header_widths = [0.6, 2.8, 1.3, 0.8, 1.0]

        hrow = table.rows[0]
        for i, (header, width) in enumerate(zip(headers, header_widths)):
            cell = hrow.cells[i]
            cell.width = Inches(width)
            _set_cell_bg(cell, '003366')
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(header)
            r.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            r.font.size = Pt(10)

        # Data rows
        for row_idx, row in enumerate(service_rows, 1):
            trow = table.rows[row_idx]

            # S.No
            trow.cells[0].text = str(row_idx).zfill(2)

            # Parameter name
            param_name = row.get('title', row.get('parameter_key', ''))
            trow.cells[1].text = param_name

            # CRA Pillar
            pillar = row.get('pillar', 'Best Practice')
            trow.cells[2].text = pillar

            # Finding (Pass/Fail)
            status = row.get('status', '')
            finding_text = 'Pass' if status == 'pass' else 'Fail'
            trow.cells[3].text = finding_text
            if status == 'pass':
                _set_cell_bg(trow.cells[3], '90EE90')
            else:
                _set_cell_bg(trow.cells[3], 'FFB6C6')

            # Severity
            severity = row.get('severity', 'Informational').title()
            trow.cells[4].text = severity

            # Color code severity
            severity_lower = severity.lower()
            if severity_lower == 'critical':
                trow.cells[4].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 0, 0)
            elif severity_lower == 'high':
                trow.cells[4].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 102, 0)

        doc.add_paragraph()

        # Individual findings for this service
        for row_idx, row in enumerate(service_rows, 1):
            param_name = row.get('title', row.get('parameter_key', ''))
            _add_heading3(doc, f"{row_idx}: {param_name}")

            # Risk rating
            severity = row.get('severity', 'Informational').title()
            status = row.get('status', '')
            finding_text = 'Pass' if status == 'pass' else 'Fail'

            p = doc.add_paragraph()
            r = p.add_run(f"Risk Rating: {severity} - {finding_text}")
            r.bold = True

            # Color code the risk rating
            severity_lower = severity.lower()
            if severity_lower == 'critical' or finding_text == 'Fail':
                r.font.color.rgb = RGBColor(255, 0, 0)
            elif severity_lower == 'high':
                r.font.color.rgb = RGBColor(255, 102, 0)
            elif finding_text == 'Pass':
                r.font.color.rgb = RGBColor(0, 176, 80)

            # Description
            description = row.get('description', '')
            if description:
                p = doc.add_paragraph()
                p.add_run("Description: ").bold = True
                p.add_run(description)

            # Risk text
            if description:  # Use description as risk text too
                p = doc.add_paragraph()
                p.add_run("Risk: ").bold = True
                p.add_run(description)

            doc.add_paragraph()

        doc.add_page_break()


def _add_conclusion_page(doc, company_name, partner_name, findings, total_params):
    """Last page: Conclusion."""
    _add_heading1(doc, "Conclusion")

    fail_count = len([f for f in findings if f.get('status') != 'pass'])

    doc.add_paragraph(
        f"The Copilot Readiness Assessment for {company_name} reveals that the current Microsoft 365 "
        f"environment is not yet prepared for the secure and compliant deployment of Microsoft 365 Copilot. "
        f"With {fail_count} out of {total_params} parameters failing to meet readiness standards, many of which fall under "
        "critical and high-risk categories, there is a clear need for immediate and comprehensive remediation."
    )

    doc.add_paragraph(
        "Key gaps were identified across all three foundational pillars: Security, Governance, and Best Practices. "
        "Notably, critical vulnerabilities such as the absence of sensitivity labels, permissive external sharing "
        "configurations, and insufficient audit logging significantly elevate the risk of data exposure and non-compliance."
    )

    doc.add_paragraph(
        f"To mitigate these risks and ensure a successful Copilot rollout, {partner_name} strongly recommends a phased "
        "remediation strategy. This should prioritise the resolution of critical and high-severity issues, followed by "
        "medium and low-risk items. Only after these gaps are addressed should the organisation consider enabling "
        "Copilot in the production environment."
    )

    doc.add_paragraph(
        f"By aligning with the recommendations outlined in this report, {company_name} can enhance its security posture, "
        "ensure regulatory compliance, and fully leverage the transformative potential of Microsoft 365 Copilot."
    )


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def build_docx_report(assessment_data: dict, output_path: str,
                      company_name: str = None, company_address: str = None,
                      logo_path: str = None) -> str:
    """
    Build complete 50-page CRA report DOCX file.

    Args:
        assessment_data: Full dict from build_report_data() containing:
            - assessment: Assessment model object
            - parameter_rows: List of dicts with finding data
            - summary: Dict with summary metrics
            - sections: Dict with findings grouped by service
        output_path: Path where DOCX will be saved
        company_name: Override company name
        company_address: Override company address
        logo_path: Path to logo image file

    Returns:
        Path to generated DOCX file
    """

    try:
        logger.info("[REPORT_BUILDER] Starting report generation")

        # Extract data from assessment_data
        assessment = assessment_data.get('assessment')
        parameter_rows = assessment_data.get('parameter_rows', [])
        summary = assessment_data.get('summary', {})

        logger.info(f"[REPORT_BUILDER] Found {len(parameter_rows)} parameters")

        # Convert parameter_rows to findings list format for processing
        findings = []
        for row in parameter_rows:
            findings.append({
                'service': row.get('service', 'Unknown'),
                'parameter': row.get('title', row.get('parameter_key', '')),
                'pillar': row.get('pillar', 'Best Practice'),
                'status': row.get('status', ''),
                'severity': row.get('severity', 'Informational'),
                'description': row.get('description', ''),
            })

        logger.info(f"[REPORT_BUILDER] Converted to {len(findings)} findings")

        # Get metadata
        company = company_name or summary.get('customer_name') or summary.get('tenant_name', 'Client')
        partner = summary.get('partner_name', 'CRA Assessment Team')
        assessment_date = assessment.created_at if assessment else None

        logger.info(f"[REPORT_BUILDER] Building report for {company}")

        # Create document
        doc = Document()

        # Set margins
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        # Build all pages
        _add_cover_page(doc, company, logo_path, assessment_date)
        _add_toc_page(doc)
        _add_executive_summary_page(doc, company, partner)
        _add_evaluation_summary_page(doc, findings)
        _add_summary_assessment_page(doc, findings, assessment_data)
        _add_detailed_assessment_pages(doc, assessment_data)
        _add_conclusion_page(doc, company, partner, findings, len(parameter_rows))

        # Save document
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path_obj))

        file_size = output_path_obj.stat().st_size
        logger.info(f"[REPORT_BUILDER] Report saved: {output_path_obj} ({file_size} bytes)")

        return str(output_path_obj)

    except Exception as e:
        logger.error(f"[REPORT_BUILDER] Error: {e}", exc_info=True)
        raise
