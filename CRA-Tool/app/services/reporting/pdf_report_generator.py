"""
PDF Report Generator using ReportLab
Generates professional CRA reports as PDF using ReportLab (Platypus).
Charts are rendered natively by Matplotlib → embedded as PNG via BytesIO.
No LibreOffice. No DOCX conversion. Pure Python PDF generation.
"""
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.platypus import KeepTogether, PageTemplate, Frame
from reportlab.pdfgen import canvas

from app.services.reporting.chart_generator import (
    generate_severity_pie_chart,
    generate_pass_fail_chart,
    generate_service_chart,
    generate_pillar_chart,
    generate_risk_category_chart,
)

logger = logging.getLogger(__name__)

# CRA Brand Colors (hex)
PRIMARY_COLOR = HexColor("#1E3A5F")
ACCENT_COLOR = HexColor("#3B82F6")
CRITICAL_COLOR = HexColor("#DC2626")
HIGH_COLOR = HexColor("#EA580C")
MEDIUM_COLOR = HexColor("#D97706")
LOW_COLOR = HexColor("#65A30D")
PASS_COLOR = HexColor("#16A34A")
FAIL_COLOR = HexColor("#DC2626")
LIGHT_GRAY = HexColor("#F8FAFC")
DARK_GRAY = HexColor("#475569")
LIGHT_BLUE = HexColor("#EFF6FF")

SEVERITY_COLORS = {
    'critical': CRITICAL_COLOR,
    'high': HIGH_COLOR,
    'medium': MEDIUM_COLOR,
    'low': LOW_COLOR,
    'info': ACCENT_COLOR,
    'pass': PASS_COLOR,
    'fail': FAIL_COLOR,
}


def _create_header_footer(canvas_obj, doc, logo_bytes_data):
    """Draw logo header on each page."""
    if logo_bytes_data:
        try:
            logo_bytes_data.seek(0)
            logo_width = 1.8 * inch
            logo_height = 1.8 * inch

            canvas_obj.saveState()
            canvas_obj.drawImage(
                logo_bytes_data,
                doc.leftMargin - 0.1 * inch,
                doc.height + doc.topMargin + 0.2 * inch,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                kind='proportional'
            )
            canvas_obj.restoreState()
        except Exception as e:
            logger.warning(f"Could not draw logo header: {e}")


def _get_styles():
    """Get custom styles for the PDF."""
    styles = getSampleStyleSheet()

    # Title style
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=PRIMARY_COLOR,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))

    # Subtitle style
    styles.add(ParagraphStyle(
        name='CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=ACCENT_COLOR,
        spaceAfter=12,
        alignment=TA_LEFT,
    ))

    # Heading1 style
    styles.add(ParagraphStyle(
        name='CustomHeading1',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=PRIMARY_COLOR,
        spaceAfter=6,
    ))

    # Heading2 style
    styles.add(ParagraphStyle(
        name='CustomHeading2',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=PRIMARY_COLOR,
        spaceAfter=6,
    ))

    # Body text
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=DARK_GRAY,
        spaceAfter=6,
    ))

    return styles


def render_pdf_report(
    output_path: Path,
    report_data: Dict[str, Any],
    logo_path: Optional[str] = None,
    company_name: Optional[str] = None,
    address: Optional[str] = None,
) -> Path:
    """
    Generate CRA PDF report using ReportLab.

    Args:
        output_path: Path where to save the .pdf file
        report_data: Complete report data dict from report service
        logo_path: Optional path to logo file
        company_name: Optional company name override
        address: Optional company address

    Returns:
        Path: Path to the generated .pdf file
    """
    logger.info(f"Generating PDF report for assessment: "
                f"{report_data.get('assessment_id', 'unknown')}")

    # Inject customization into report_data
    if company_name:
        report_data['company_name'] = company_name
    if address:
        report_data['address'] = address

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create PDF document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.9*inch,
        leftMargin=0.9*inch,
        topMargin=0.9*inch,
        bottomMargin=0.9*inch,
    )

    styles = _get_styles()
    story = []

    # Load logo if provided
    logo_bytes = None
    logo_file_bytes = None
    if logo_path:
        try:
            with open(logo_path, 'rb') as f:
                logo_file_bytes = f.read()
                logo_bytes = io.BytesIO(logo_file_bytes)
        except Exception as e:
            logger.warning(f"Could not load logo from {logo_path}: {e}")

    # Define a custom callback to draw logo on every page
    def draw_page_header(canvas_obj, doc):
        if logo_file_bytes:
            _create_header_footer(canvas_obj, doc, io.BytesIO(logo_file_bytes))

    # Update document to use custom header callback
    doc.onFirstPage = draw_page_header
    doc.onLaterPages = draw_page_header

    # Increase top margin to accommodate logo header
    doc.topMargin = 1.8 * inch

    # ── Cover Page ──────────────────────────────────────────────
    if logo_bytes:
        try:
            logo_bytes.seek(0)
            logo_img = Image(logo_bytes, width=2.5*inch, height=2.5*inch, kind='proportional')
            story.append(logo_img)
        except Exception as e:
            logger.warning(f"Could not embed logo: {e}")

    story.append(Spacer(1, 0.2*inch))

    # Title
    story.append(Paragraph("Microsoft Copilot", styles['CustomTitle']))
    story.append(Paragraph("Readiness Assessment Report", styles['CustomSubtitle']))
    story.append(Spacer(1, 0.3*inch))

    # Company details
    summary = report_data.get('summary', {})
    assessment = report_data.get('assessment', {})
    tenant_name = str(report_data.get('tenant_name',
                                       assessment.get('tenant_id', 'N/A')
                                       if hasattr(assessment, 'get')
                                       else getattr(assessment, 'tenant_id', 'N/A')))
    company_display = report_data.get('company_name', tenant_name)
    address_display = report_data.get('address', '')
    assessment_date = report_data.get('assessment_date',
                                      datetime.utcnow().strftime('%B %d, %Y'))
    overall_score = summary.get('overall_score', 0)

    # Details table
    details_data = [
        ['Organization', company_display],
        ['Tenant', tenant_name],
        ['Assessment Date', assessment_date],
        ['Overall Readiness Score',
         f"{overall_score:.1f}% — "
         f"{'Good' if overall_score >= 70 else 'Needs Improvement' if overall_score >= 40 else 'Critical'}"],
    ]
    if address_display:
        details_data.insert(2, ['Address', address_display])

    details_table = Table(details_data, colWidths=[1.5*inch, 3.5*inch])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, -1), black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, HexColor("#E2E8F0")),
    ]))
    story.append(details_table)
    story.append(PageBreak())

    # ── Executive Summary ────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", styles['CustomHeading1']))
    story.append(Spacer(1, 0.15*inch))

    # Readiness gauge
    try:
        gauge_img = generate_risk_category_chart({'critical': 5, 'high': 3, 'medium': 2})
        gauge_img.seek(0)
        img = Image(gauge_img, width=3*inch, height=2.25*inch)
        story.append(img)
        story.append(Paragraph("Overall Copilot Readiness Score",
                              ParagraphStyle('Caption',
                                            parent=styles['Normal'],
                                            fontSize=9,
                                            textColor=DARK_GRAY,
                                            alignment=TA_CENTER)))
    except Exception as e:
        logger.error(f"Error generating gauge: {e}")

    story.append(Spacer(1, 0.2*inch))

    # Key metrics
    story.append(Paragraph("Key Metrics", styles['CustomHeading2']))

    total_checks = summary.get('total_checks', summary.get('parameter_total', 0))
    pass_count = summary.get('pass_count', summary.get('pass_total', 0))
    fail_count = summary.get('fail_count', summary.get('failed_total', 0))
    critical_count = summary.get('critical_count', summary.get('critical_findings', 0))
    high_count = summary.get('high_count', summary.get('high_findings', 0))

    metrics = [
        ['Total Checks Performed', str(total_checks)],
        ['Checks Passed', str(pass_count)],
        ['Checks Failed', str(fail_count)],
        ['Critical Findings', str(critical_count)],
        ['High Severity Findings', str(high_count)],
        ['Overall Readiness Score', f'{overall_score:.1f}%'],
    ]

    metrics_table = Table(metrics, colWidths=[2.0*inch, 2.5*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('TEXTCOLOR', (0, 0), (-1, -1), black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [HexColor("#FFFFFF"), HexColor("#F8FAFC")]),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.3*inch))
    story.append(PageBreak())

    # ── Analytics Section ────────────────────────────────────────
    story.append(Paragraph("2. Analytics Overview", styles['CustomHeading1']))
    story.append(Spacer(1, 0.15*inch))

    analytics = report_data.get('analytics', {})

    # Severity distribution
    severity_dist = analytics.get('severity_distribution', {})
    if severity_dist:
        story.append(Paragraph("Findings by Severity", styles['CustomHeading2']))
        try:
            pie_img = generate_severity_pie_chart(severity_dist)
            pie_img.seek(0)
            img = Image(pie_img, width=3.5*inch, height=2.6*inch)
            story.append(img)
            story.append(Paragraph(
                "Distribution of findings across severity levels",
                ParagraphStyle('Caption', parent=styles['Normal'],
                              fontSize=9, textColor=DARK_GRAY, alignment=TA_CENTER)))
        except Exception as e:
            logger.error(f"Error generating severity chart: {e}")
        story.append(Spacer(1, 0.2*inch))

    # Pass vs Fail
    story.append(Paragraph("Pass vs Fail Breakdown", styles['CustomHeading2']))
    try:
        pf_img = generate_pass_fail_chart(pass_count, fail_count)
        pf_img.seek(0)
        img = Image(pf_img, width=3.75*inch, height=1.6*inch)
        story.append(img)
        story.append(Paragraph(
            "Overall pass and fail counts across all checks",
            ParagraphStyle('Caption', parent=styles['Normal'],
                          fontSize=9, textColor=DARK_GRAY, alignment=TA_CENTER)))
    except Exception as e:
        logger.error(f"Error generating pass/fail chart: {e}")

    story.append(Spacer(1, 0.2*inch))
    story.append(PageBreak())

    # Service distribution
    service_dist = analytics.get('service_distribution', {})
    if service_dist:
        story.append(Paragraph("Results by Service", styles['CustomHeading2']))
        try:
            svc_img = generate_service_chart(service_dist)
            svc_img.seek(0)
            img = Image(svc_img, width=4.25*inch, height=2.0*inch)
            story.append(img)
            story.append(Paragraph(
                "Pass/fail breakdown per Microsoft 365 service",
                ParagraphStyle('Caption', parent=styles['Normal'],
                              fontSize=9, textColor=DARK_GRAY, alignment=TA_CENTER)))
        except Exception as e:
            logger.error(f"Error generating service chart: {e}")
        story.append(Spacer(1, 0.2*inch))

    # Pillar distribution
    pillar_dist = analytics.get('pillar_distribution', {})
    if pillar_dist:
        story.append(Paragraph("Findings by Pillar", styles['CustomHeading2']))
        try:
            pillar_img = generate_pillar_chart(pillar_dist)
            pillar_img.seek(0)
            img = Image(pillar_img, width=4.25*inch, height=1.75*inch)
            story.append(img)
            story.append(Paragraph(
                "Finding counts across assessment pillars",
                ParagraphStyle('Caption', parent=styles['Normal'],
                              fontSize=9, textColor=DARK_GRAY, alignment=TA_CENTER)))
        except Exception as e:
            logger.error(f"Error generating pillar chart: {e}")

    # ── Build and save PDF ──────────────────────────────────────
    try:
        doc.build(story)
        logger.info(f"PDF report generation complete: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error building PDF: {e}")
        raise
