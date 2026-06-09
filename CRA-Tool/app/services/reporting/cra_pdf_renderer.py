from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from reportlab.platypus import Flowable


SERVICE_NAMES = [
    "Entra ID",
    "Exchange Online",
    "Microsoft Teams",
    "SharePoint Online",
    "OneDrive",
    "Microsoft Purview",
]

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}

PALETTE = {
    "navy": "#0f172a",
    "blue": "#0078d4",
    "light_blue": "#e8f2ff",
    "border": "#cbd5e1",
    "muted": "#475569",
    "paper": "#f8fafc",
    "critical": "#8b1e1e",
    "high": "#c2410c",
    "medium": "#facc15",
    "low": "#2563eb",
    "pass": "#15803d",
    "licensing_required": "#7c3aed",
    "manual_validation_required": "#64748b",
    "not_collected": "#94a3b8",
    "failed": "#991b1b",
}

OUT_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "out"


def render_pdf(path: Path, report: dict[str, Any]) -> Path:
    import reportlab  # noqa: F401 - fail fast when the enterprise PDF engine is unavailable.

    path.parent.mkdir(parents=True, exist_ok=True)
    if (OUT_TEMPLATE_DIR / "index.html").exists():
        return _render_exact_out_template(path, report, OUT_TEMPLATE_DIR)
    return _render_reportlab(path, report)


def _render_exact_out_template(path: Path, report: dict[str, Any], template_dir: Path) -> Path:
    html_path = path.with_suffix(".html")
    _copy_out_template_assets(template_dir, html_path.parent)
    html_path.write_text(_build_exact_template_html(report, template_dir), encoding="utf-8")
    browser = _browser_executable()
    if browser is None:
        return _render_out_template_reportlab(path, report, template_dir)
    _print_html_to_pdf(browser, html_path, path)
    return path


def _build_exact_template_html(report: dict[str, Any], template_dir: Path) -> str:
    template = (template_dir / "index.html").read_text(encoding="utf-8")
    template_data = _extract_template_report_data(template)
    report_data = _merge_cra_results_into_template_data(template_data, report)
    rendered_data = json.dumps(report_data, ensure_ascii=False, indent=2)
    return re.sub(
        r"(// START_REPORT_DATA\s*let\s+REPORT_DATA\s*=\s*).*?(\s*;\s*// END_REPORT_DATA)",
        rf"\1{rendered_data}\2",
        template,
        flags=re.DOTALL,
    )


def _extract_template_report_data(template: str) -> dict[str, Any]:
    match = re.search(
        r"// START_REPORT_DATA\s*let\s+REPORT_DATA\s*=\s*(.*?)\s*;\s*// END_REPORT_DATA",
        template,
        flags=re.DOTALL,
    )
    if not match:
        raise RuntimeError("out/index.html does not contain a REPORT_DATA template block.")
    return json.loads(match.group(1))


def _merge_cra_results_into_template_data(template_data: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    data = json.loads(json.dumps(template_data, ensure_ascii=False))
    summary = report.get("summary") or {}
    rows = report.get("parameter_rows") or []
    customer = _customer_label(summary)
    date = str(summary.get("assessment_date") or data.get("date") or "DD-MM-YYYY")
    total = int(summary.get("parameter_total") or len(rows) or 0)
    failed = _total_gap_count(rows)
    readiness = float(summary.get("overall_readiness") or _readiness_from_rows(rows))

    data["customerName"] = customer
    data["date"] = date
    data["overallReadiness"] = {
        **(data.get("overallReadiness") or {}),
        "level": _readiness_level(summary, rows),
        "gapsCount": str(failed),
        "totalParameters": str(total),
        "failedPercentage": f"{round(100 - readiness, 2):g}%",
    }

    data["executiveSummary"] = _replace_template_placeholders(data.get("executiveSummary") or [], customer)
    data["purpose"] = _replace_template_placeholders(data.get("purpose") or [], customer)
    data["keyObservations"] = _replace_template_placeholders(data.get("keyObservations") or [], customer)
    data["conclusion"] = _replace_template_placeholders(data.get("conclusion") or [], customer)

    rows_by_title = {_slug(row.get("title")): row for row in rows}
    rows_by_key = {_slug(row.get("parameter_key")): row for row in rows}
    for service in data.get("detailedAssessment") or []:
        summary_by_id = {item.get("sNo"): item for item in service.get("summaryTable") or []}
        for parameter in service.get("parameters") or []:
            row = _matching_parameter_row(parameter, rows_by_title, rows_by_key)
            summary_row = summary_by_id.get(parameter.get("id"))
            if row is None:
                parameter["status"] = "Fail"
                parameter["description"] = "Tenant evidence was not collected for this template parameter."
                parameter["risk"] = parameter.get("risk") or "No readiness conclusion can be certified until this parameter is collected from the tenant."
                parameter["documentationText"] = parameter.get("documentationText") or "Microsoft Documentation"
                if summary_row is not None:
                    summary_row["finding"] = "Fail"
                continue
            status = _template_status(row)
            severity = _template_severity(row)
            parameter["status"] = status
            parameter["severity"] = severity
            parameter["description"] = _template_result_text(row)
            if parameter.get("documentationUrl") in {None, ""}:
                parameter["documentationUrl"] = _microsoft_reference(row)
                parameter["documentationText"] = "Microsoft Documentation"
            if summary_row is not None:
                summary_row["finding"] = status
                summary_row["severity"] = severity
                summary_row["pillar"] = _pillar_name(row)
    return data


def _matching_parameter_row(
    parameter: dict[str, Any],
    rows_by_title: dict[str, dict[str, Any]],
    rows_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    aliases = {
        "devicewithoutcompliancepolicies": "deviceswithoutcompliancepolicies",
        "entratenantcreationbynonadmins": "entratenantcreationbynonadmin",
        "tenantcollaborationinvitation": "tenantcollaborationinvitations",
        "administratorconsentworkflows": "adminconsentworkflow",
        "autoexpirationpolicyform365groups": "autoexpirationpolicyforinactivem365groups",
        "numberofaccountsenabled": "accountenabled",
        "mailboxstatusactiveinactive": "mailboxesstatusactiveinactive",
        "activeinactiveteamsusers": "activerinactiveteamsusers",
        "permissionsettingsforanyonelinks": "permissionsettingforanyonelinks",
        "sensitivesharepointsitesexcludedfromcopilot": "gettingallsiteswithsensitivitykeywordsonatenant",
    }
    candidates = [
        parameter.get("name"),
        parameter.get("rawTitle"),
        parameter.get("parameter"),
    ]
    for candidate in candidates:
        slug = _slug(candidate)
        row = rows_by_title.get(slug)
        if row is not None:
            return row
        row = rows_by_key.get(slug)
        if row is not None:
            return row
        alias = aliases.get(slug)
        if alias:
            row = rows_by_title.get(alias) or rows_by_key.get(alias)
            if row is not None:
                return row
    return None


def _copy_out_template_assets(template_dir: Path, target_dir: Path) -> None:
    for asset in template_dir.iterdir():
        if asset.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            continue
        shutil.copy2(asset, target_dir / asset.name)


def _browser_executable() -> Path | None:
    return None


def _print_html_to_pdf(browser: Path, html_path: Path, pdf_path: Path) -> None:
    pdf_path.unlink(missing_ok=True)
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--allow-file-access-from-files",
        f"--print-to-pdf={pdf_path.resolve()}",
        html_path.resolve().as_uri(),
    ]
    result = subprocess.run(command, cwd=str(html_path.parent), capture_output=True, text=True, timeout=90)
    if result.returncode != 0 or not pdf_path.exists():
        message = (result.stderr or result.stdout or "Browser PDF rendering failed.").strip()
        raise RuntimeError(message)


def _replace_template_placeholders(values: list[Any], customer: str) -> list[str]:
    return [
        str(value)
        .replace("________.", customer)
        .replace("_________", customer)
        .replace("__________", customer)
        .replace("________", customer)
        .replace("_____.", customer)
        .replace("_____", customer)
        for value in values
    ]


def _template_status(row: dict[str, Any]) -> str:
    status = _normalized_status(row)
    if status == "pass":
        return "Pass"
    return "Fail"


def _template_severity(row: dict[str, Any]) -> str:
    severity = str(row.get("severity") or "info").strip().lower()
    return "Informational" if severity in {"info", "informational"} else severity.title()


def _template_result_text(row: dict[str, Any]) -> str:
    result = str(row.get("actual_result") or row.get("finding") or "").strip()
    if result and result.lower() not in {"not collected", "not_collected", "none", "n/a", "unknown"}:
        return result
    return _evidence_summary(row)


def _slug(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"^\s*\d+\s*[:.)-]\s*", "", text)
    text = text.replace("–", "-").replace("—", "-").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", text)


def _render_out_template_reportlab(path: Path, report: dict[str, Any], template_dir: Path) -> Path:
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        Image,
        KeepTogether,
        PageBreak,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TemplateTitle", parent=styles["Heading1"], fontSize=26, leading=31, textColor=_color("navy")))
    styles.add(ParagraphStyle(name="TemplateSubtitle", parent=styles["BodyText"], fontSize=11, leading=15, textColor=_color("muted")))
    styles.add(ParagraphStyle(name="TemplateSection", parent=styles["Heading1"], fontSize=18, leading=22, spaceBefore=6, spaceAfter=10, textColor=_color("navy")))
    styles.add(ParagraphStyle(name="TemplateHeading", parent=styles["Heading2"], fontSize=12, leading=15, spaceBefore=4, spaceAfter=6, textColor=_color("navy")))
    styles.add(ParagraphStyle(name="TemplateBody", parent=styles["BodyText"], fontSize=8.8, leading=11.5))
    styles.add(ParagraphStyle(name="TemplateSmall", parent=styles["BodyText"], fontSize=7.2, leading=9.2))
    styles.add(ParagraphStyle(name="TemplateFine", parent=styles["BodyText"], fontSize=6.5, leading=8.5))
    styles.add(ParagraphStyle(name="TemplateMuted", parent=styles["BodyText"], fontSize=8, leading=10.5, textColor=_color("muted")))
    styles.add(ParagraphStyle(name="TemplateKpi", parent=styles["Heading1"], fontSize=17, leading=20, alignment=TA_CENTER, textColor=_color("navy")))
    styles.add(ParagraphStyle(name="TemplateKpiLabel", parent=styles["BodyText"], fontSize=7, leading=8.5, alignment=TA_CENTER, textColor=_color("muted")))

    doc = BaseDocTemplate(str(path), pagesize=A4, pageCompression=0)
    margin_x = 34
    margin_top = 46
    margin_bottom = 34
    doc.addPageTemplates([
        PageTemplate(
            id="Template",
            pagesize=A4,
            frames=[Frame(margin_x, margin_bottom, A4[0] - margin_x * 2, A4[1] - margin_top - margin_bottom, id="main")],
            onPage=_out_template_header_footer,
        ),
    ])

    summary = report["summary"]
    rows = report.get("parameter_rows") or []
    story: list[Any] = []

    # Page 1 — Cover
    _out_cover(story, styles, summary, template_dir)
    story.append(PageBreak())

    # Page 2 — Table of Contents
    _out_template_toc(story, styles, rows)
    story.append(PageBreak())

    # Page 3 — Executive Summary (includes Purpose)
    _out_executive_summary(story, styles, summary, rows)
    story.append(PageBreak())

    # Page 4 — Evaluation Summary (3 pillars, services, risk matrix)
    _out_template_evaluation_summary(story, styles, rows)
    story.append(PageBreak())

    # Page 5 — Summary of Assessment (score + service breakdown)
    _out_dashboard(story, styles, summary, rows)
    story.append(PageBreak())

    # Page 6 — Key Observations & Recommendations
    _out_key_observations(story, styles, summary, rows)
    story.append(PageBreak())

    # Pages 7+ — Detailed Assessment (by service domain)
    _out_detailed_assessment(story, styles, rows, template_dir)
    story.append(PageBreak())

    # Last page — Conclusion
    _out_conclusion(story, styles, summary, rows)

    doc.build(story)
    return path


def _out_template_toc(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    _out_section(story, styles, "Table of Contents")

    toc_entries = [
        ("1", "Executive Summary"),
        ("2", "Purpose & Evaluation Scope"),
        ("3", "Evaluation Summary"),
        ("4", "Summary of Assessment"),
        ("5", "Key Observations"),
        ("6", "Recommended Actions"),
        ("7", "Detailed Assessment"),
    ]
    services = list(_rows_by_service(rows).keys())
    sub_num = 8
    for svc in services:
        toc_entries.append((f"  {sub_num}", svc))
        sub_num += 1
    toc_entries.append((str(sub_num), "Conclusion"))

    tbl_data = []
    for num, title in toc_entries:
        is_sub = title.startswith("  ") or num.strip() != num
        style = styles["TemplateSmall"] if is_sub else styles["TemplateBody"]
        dots = "." * 60
        tbl_data.append([
            Paragraph(f"<b>{num.strip()}</b>" if not is_sub else num.strip(), styles["TemplateSmall"]),
            Paragraph(_escape(title.strip()), style),
            Paragraph(dots, styles["TemplateFine"]),
        ])

    tbl = Table(tbl_data, colWidths=[24, 340, None])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#e2e8f0")),
    ]))
    story.append(tbl)


def _out_template_evaluation_summary(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    _out_section(story, styles, "Evaluation Summary")

    # 3 Pillars
    story.append(Paragraph("<b>Assessment Pillars</b>", styles["TemplateHeading"]))
    for pillar, desc in [
        ("Security", "Identity management, authentication controls, privileged access, guest access, and threat protection policies."),
        ("Governance", "Data lifecycle, compliance policies, information barriers, DLP configuration, and Teams governance."),
        ("Best Practices", "Licensing coverage, service adoption, OneDrive/SharePoint configuration, and operational hygiene."),
    ]:
        story.append(Paragraph(f"<b>{pillar}</b>: {_escape(desc)}", styles["TemplateBody"], bulletText="•"))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))

    # M365 Services evaluated
    story.append(Paragraph("<b>M365 Services Evaluated</b>", styles["TemplateHeading"]))
    for svc in [
        "Entra ID — Identity, conditional access, MFA, guest accounts, privileged roles",
        "Exchange Online — Mail flow, anti-phishing, DMARC/DKIM, mailbox auditing",
        "Microsoft Teams — Meeting policies, external access, app governance",
        "SharePoint Online — Sharing controls, external access, site policies",
        "OneDrive for Business — Sync controls, sharing policies, activity",
        "Microsoft Purview — Sensitivity labels, DLP policies, retention, compliance posture",
    ]:
        story.append(Paragraph(_escape(svc), styles["TemplateBody"], bulletText="•"))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 14))

    # Risk Score Matrix table
    story.append(Paragraph("<b>Risk Score Matrix</b>", styles["TemplateHeading"]))
    story.append(Spacer(1, 4))

    matrix_data = [
        ["Rating", "Score Impact", "Description", "Action Required"],
        ["Critical", "–20 to –30", "Immediate Copilot blocker; data exposure or access control failure", "Remediate before deployment"],
        ["High",     "–10 to –20", "Significant gap; elevated risk during Copilot rollout",            "Remediate within 30 days"],
        ["Medium",   "–5 to –10",  "Control gap that increases risk surface; may affect Copilot UX",  "Address within 60 days"],
        ["Low",      "–1 to –5",   "Minor deviation; improvement recommended for best practice",       "Address within 90 days"],
        ["Pass",     "0",          "Control meets the Copilot readiness requirement",                  "No action required"],
    ]

    row_colors = {
        "Critical": "#fef2f2",
        "High":     "#fff7ed",
        "Medium":   "#fefce8",
        "Low":      "#eff6ff",
        "Pass":     "#f0fdf4",
    }
    text_colors = {
        "Critical": "#991b1b",
        "High":     "#c2410c",
        "Medium":   "#854d0e",
        "Low":      "#1e40af",
        "Pass":     "#15803d",
    }

    tbl_data = []
    hdr = matrix_data[0]
    tbl_data.append([
        Paragraph(f"<b>{c}</b>", styles["TemplateSmall"]) for c in hdr
    ])
    for row in matrix_data[1:]:
        rating = row[0]
        color = text_colors.get(rating, "#0f172a")
        tbl_data.append([
            Paragraph(f"<b><font color='{color}'>{_escape(row[0])}</font></b>", styles["TemplateSmall"]),
            Paragraph(_escape(row[1]), styles["TemplateSmall"]),
            Paragraph(_escape(row[2]), styles["TemplateSmall"]),
            Paragraph(_escape(row[3]), styles["TemplateSmall"]),
        ])

    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f172a")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 7.5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor(row_colors.get(r[0], "#ffffff")) for r in matrix_data[1:]]),
    ]
    for i, row in enumerate(matrix_data[1:], start=1):
        rating = row[0]
        if rating in row_colors:
            ts.append(("BACKGROUND", (0, i), (-1, i), HexColor(row_colors[rating])))

    tbl = Table(tbl_data, colWidths=[55, 65, 230, 120])
    tbl.setStyle(TableStyle(ts))
    story.append(tbl)


def _out_cover(story: list[Any], styles, summary: dict[str, Any], template_dir: Path) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    accent = _out_image(template_dir / "3.png", width=112)
    customer = _customer_label(summary)
    date = str(summary.get("assessment_date") or "DD-MM-YYYY")
    cover_badge = ParagraphStyle(
        "CoverBadge",
        parent=styles["TemplateSmall"],
        fontSize=7.5,
        leading=10,
        textColor=HexColor("#bfdbfe"),
    )
    cover_title = ParagraphStyle(
        "CoverTitle",
        parent=styles["TemplateTitle"],
        fontSize=28,
        leading=33,
        textColor=HexColor("#ffffff"),
    )
    cover_subtitle = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["TemplateBody"],
        fontSize=9.5,
        leading=14,
        textColor=HexColor("#dbeafe"),
    )
    hero_text = [
        Paragraph("<b>MICROSOFT 365 COPILOT READINESS</b>", cover_badge),
        Spacer(1, 12),
        Paragraph("Readiness Assessment Report", cover_title),
        Spacer(1, 10),
        Paragraph(
            "Executive assessment of security, governance, collaboration, compliance, and operational readiness for Microsoft 365 Copilot adoption.",
            cover_subtitle,
        ),
    ]
    hero = Table([[hero_text, accent or ""]], colWidths=[350, 125], rowHeights=[188])
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#0f172a")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 28),
        ("RIGHTPADDING", (0, 0), (0, 0), 20),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("RIGHTPADDING", (1, 0), (1, 0), 22),
        ("TOPPADDING", (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("BOX", (0, 0), (-1, -1), 0.7, HexColor("#1e293b")),
    ]))

    prepared = Table(
        [[
            Paragraph(
                f"<b>Prepared for</b><br/>{_escape(customer)}",
                styles["TemplateSubtitle"],
            ),
            Paragraph(
                f"<b>Prepared by</b><br/>CRA Platform",
                styles["TemplateSubtitle"],
            ),
        ]],
        colWidths=[300, 175],
        rowHeights=[74],
    )
    prepared.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#ffffff")),
        ("BOX", (0, 0), (-1, -1), 0.6, HexColor("#cbd5e1")),
        ("LINEBEFORE", (1, 0), (1, 0), 3, HexColor("#0078d4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    note = Paragraph(
        "This report summarizes validated assessment evidence and prioritized readiness gaps for executive review.",
        styles["TemplateMuted"],
    )
    story.extend([
        Spacer(1, 56),
        hero,
        Spacer(1, 28),
        prepared,
        Spacer(1, 14),
        note,
    ])


def _out_dashboard(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    _out_section(story, styles, "Executive Overview")
    total = int(summary.get("parameter_total") or len(rows) or 0)
    passed = len([row for row in rows if _normalized_status(row) == "pass"])
    gaps = _total_gap_count(rows)
    readiness = float(summary.get("overall_readiness") or _readiness_from_rows(rows))
    kpis = [
        ("Readiness", _readiness_level(summary, rows)),
        ("Score", f"{readiness:g}%"),
        ("Passed", f"{passed}/{total}"),
        ("Gaps", str(gaps)),
    ]
    story.append(_out_kpi_grid(kpis, styles))
    story.append(Spacer(1, 16))
    story.append(_readiness_bar_visual(readiness))
    story.append(Spacer(1, 18))
    story.append(_out_two_column_tables(
        "Severity Mix",
        _risk_count_rows(rows),
        "Service Readiness",
        _service_readiness_rows(rows),
        styles,
    ))


def _out_executive_summary(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    customer = _customer_label(summary)
    _out_section(story, styles, "Executive Summary")
    paragraphs = [
        (
            f"As part of its digital transformation strategy, {customer} engaged CRA Platform for a Copilot Readiness Assessment. "
            "The assessment evaluates the Microsoft 365 environment across security, governance, and best practices to determine readiness "
            "for secure adoption of Microsoft 365 Copilot."
        ),
        (
            "The assessment covers Entra ID, Exchange Online, Microsoft Teams, SharePoint Online, OneDrive for Business, and Microsoft Purview. "
            "It identifies configuration gaps, policy misalignment, and controls that can affect Copilot deployment confidence."
        ),
        (
            f"The current readiness level is {_readiness_level(summary, rows)} with {_total_gap_count(rows)} readiness gaps across "
            f"{int(summary.get('parameter_total') or len(rows) or 0)} assessed parameters."
        ),
    ]
    for paragraph in paragraphs:
        story.append(Paragraph(_escape(paragraph), styles["TemplateBody"]))
        story.append(Spacer(1, 8))
    story.append(Paragraph("Purpose & Evaluation Scope", styles["TemplateHeading"]))
    for item in [
        f"Evaluate the {customer} Microsoft 365 environment against Copilot readiness expectations.",
        "Assess governance, security, and best-practice controls across Microsoft 365 services.",
        "Identify gaps that could introduce security, compliance, or operational risk during Copilot rollout.",
        "Provide a prioritized remediation baseline for deployment planning and future reassessment.",
    ]:
        story.append(Paragraph(_escape(item), styles["TemplateBody"], bulletText="-"))


def _out_key_observations(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _out_section(story, styles, "Key Observations & Recommendations")
    for item in _observation_bullets(summary, rows):
        story.append(Paragraph(_escape(item), styles["TemplateBody"], bulletText="-"))
        story.append(Spacer(1, 5))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Recommended Actions", styles["TemplateHeading"]))
    for item in [
        "Remediate all critical and high-risk gaps before production Copilot rollout.",
        "Validate controls marked not collected, failed, licensing required, or manual validation required.",
        "Use a staged deployment model and reassess readiness after remediation is complete.",
    ]:
        story.append(Paragraph(_escape(item), styles["TemplateBody"], bulletText="-"))


def _out_detailed_assessment(story: list[Any], styles, rows: list[dict[str, Any]], template_dir: Path) -> None:
    from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle

    _out_section(story, styles, "Detailed Assessment")
    for service, service_rows in _rows_by_service(rows).items():
        story.append(KeepTogether([
            Paragraph(_escape(service), styles["TemplateSection"]),
            _out_parameter_table(service_rows, styles),
        ]))
        story.append(Spacer(1, 12))
        for index, row in enumerate(service_rows, start=1):
            story.append(_out_parameter_card(index, row, styles, template_dir))
            story.append(Spacer(1, 8))
        story.append(PageBreak())
    if story and isinstance(story[-1], PageBreak):
        story.pop()


def _out_conclusion(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _out_section(story, styles, "Conclusion")
    for paragraph in _conclusion(summary, rows):
        story.append(Paragraph(paragraph, styles["TemplateBody"]))
        story.append(Spacer(1, 8))


def _out_section(story: list[Any], styles, title: str) -> None:
    from reportlab.platypus import Paragraph, Spacer

    story.append(Paragraph(_escape(title), styles["TemplateSection"]))
    story.append(Spacer(1, 4))


def _out_kpi_grid(kpis: list[tuple[str, str]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    cells = [
        [Paragraph(_escape(value), styles["TemplateKpi"]), Paragraph(_escape(label), styles["TemplateKpiLabel"])]
        for label, value in kpis
    ]
    table = Table([cells], colWidths=[124, 124, 124, 124], rowHeights=[58])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _color("paper")),
        ("BOX", (0, 0), (-1, -1), 0.6, _color("border")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, _color("border")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _out_two_column_tables(left_title: str, left_rows: list[list[Any]], right_title: str, right_rows: list[list[Any]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    left = _out_metric_table(left_title, left_rows, styles)
    right = _out_metric_table(right_title, right_rows, styles)
    table = Table([[left, right]], colWidths=[244, 244])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def _out_metric_table(title: str, rows: list[list[Any]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    data = [[Paragraph(_escape(title), styles["TemplateHeading"]), ""]]
    data.extend([[Paragraph(_escape(row[0]), styles["TemplateSmall"]), Paragraph(_escape(row[1]), styles["TemplateSmall"])] for row in rows])
    table = Table(data, colWidths=[158, 72])
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), _color("light_blue")),
        ("BACKGROUND", (0, 1), (-1, -1), _color("paper")),
        ("GRID", (0, 0), (-1, -1), 0.35, _color("border")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _out_parameter_table(rows: list[dict[str, Any]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    data = [["S. No", "Parameter Name", "CRA Pillar", "Finding", "Severity"]]
    for index, row in enumerate(rows, start=1):
        data.append([
            f"{index:02d}",
            Paragraph(_clean(row.get("title")), styles["TemplateSmall"]),
            Paragraph(_escape(_pillar_name(row)), styles["TemplateSmall"]),
            Paragraph(_escape(_status_label(row)), styles["TemplateSmall"]),
            Paragraph(_escape(str(row.get("severity") or "info").title()), styles["TemplateSmall"]),
        ])
    table = Table(data, colWidths=[35, 220, 90, 70, 75], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _color("navy")),
        ("TEXTCOLOR", (0, 0), (-1, 0), _white()),
        ("GRID", (0, 0), (-1, -1), 0.35, _color("border")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, -1), _color("paper")),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _out_parameter_card(index: int, row: dict[str, Any], styles, template_dir: Path):
    from reportlab.platypus import Image, KeepTogether, Paragraph, Table, TableStyle

    image = _out_image(template_dir / f"{min(index + 4, 69)}.png", width=72) or _out_image(template_dir / f"{min(index + 4, 69)}.jpeg", width=72)
    status = _status_label(row)
    severity = str(row.get("severity") or "info").title()
    title = Paragraph(f"<b>{index:02d}: {_clean(row.get('title'))}</b><br/><font color='{PALETTE['muted']}'>Risk Rating: {_escape(severity)} - {_escape(status)}</font>", styles["TemplateBody"])
    body = [
        [Paragraph("<b>Description</b>", styles["TemplateSmall"]), Paragraph(_escape(_executive_result(row)), styles["TemplateSmall"])],
        [Paragraph("<b>Risk</b>", styles["TemplateSmall"]), Paragraph(_escape(_copilot_impact(row)), styles["TemplateSmall"])],
        [Paragraph("<b>Recommendation</b>", styles["TemplateSmall"]), Paragraph(_escape(_remediation_guidance(row)), styles["TemplateSmall"])],
        [Paragraph("<b>Microsoft Reference</b>", styles["TemplateSmall"]), Paragraph(_escape(_microsoft_reference(row)), styles["TemplateSmall"])],
    ]
    detail = Table(body, colWidths=[90, 300])
    detail.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, _color("border")),
        ("BACKGROUND", (0, 0), (0, -1), _color("light_blue")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    card = Table([[image or "", [title, detail]]], colWidths=[82, 405])
    card.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, _color("border")),
        ("BACKGROUND", (0, 0), (-1, -1), _white()),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return KeepTogether([card])


def _out_image(path: Path, *, width: float):
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image

    if not path.exists():
        return None
    img = ImageReader(str(path))
    source_width, source_height = img.getSize()
    height = width * source_height / source_width
    return Image(str(path), width=width, height=height)


def _out_template_header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFillColor(_color("navy"))
    canvas.rect(0, height - 26, width, 26, fill=1, stroke=0)
    canvas.setFillColor(_white())
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(34, height - 17, "Microsoft 365 Copilot Readiness Assessment")
    canvas.setFillColor(_color("muted"))
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - 34, 18, f"Page {doc.page}")
    canvas.restoreState()


def _risk_count_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    counts = _risk_counts(rows)
    return [[label, counts.get(label, 0)] for label in ["Critical", "High", "Medium", "Low"]]


def _service_readiness_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    result = []
    for service, service_rows in _rows_by_service(rows).items():
        passed = len([row for row in service_rows if _normalized_status(row) == "pass"])
        total = len(service_rows)
        result.append([service, f"{round(passed / total * 100, 0):g}%"])
    return result or [["Microsoft 365", "0%"]]


def _rows_by_service(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    order = SERVICE_NAMES + ["Teams", "SharePoint", "OneDrive", "Licensing", "Microsoft 365"]
    for row in rows:
        grouped[_canonical_service(row.get("service"))].append(row)
    return {service: grouped[service] for service in order if grouped.get(service)}


def _render_reportlab(path: Path, report: dict[str, Any]) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.5, leading=9.5))
    styles.add(ParagraphStyle(name="Fine", parent=styles["BodyText"], fontSize=6.5, leading=8))
    styles.add(ParagraphStyle(name="Muted", parent=styles["BodyText"], textColor=_color("muted"), fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="CardValue", parent=styles["Heading1"], fontSize=18, leading=20, textColor=_color("navy")))
    styles.add(ParagraphStyle(name="CardLabel", parent=styles["BodyText"], fontSize=7.5, leading=9, textColor=_color("muted")))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading1"], textColor=_color("navy"), spaceBefore=8, spaceAfter=8))
    styles.add(ParagraphStyle(name="CenterTitle", parent=styles["Heading1"], alignment=TA_CENTER, textColor=_color("navy")))

    portrait = A4
    appendix = landscape(A4)
    margin_x = 34
    margin_top = 46
    margin_bottom = 34
    doc = BaseDocTemplate(str(path), pagesize=portrait)
    doc.addPageTemplates([
        PageTemplate(
            id="Cover",
            pagesize=portrait,
            frames=[Frame(margin_x, margin_bottom, portrait[0] - margin_x * 2, portrait[1] - margin_top - margin_bottom, id="cover")],
            onPage=_blank_page,
        ),
        PageTemplate(
            id="Portrait",
            pagesize=portrait,
            frames=[Frame(margin_x, margin_bottom, portrait[0] - margin_x * 2, portrait[1] - margin_top - margin_bottom, id="portrait")],
            onPage=_page_header_footer,
        ),
        PageTemplate(
            id="Landscape",
            pagesize=appendix,
            frames=[Frame(margin_x, margin_bottom, appendix[0] - margin_x * 2, appendix[1] - margin_top - margin_bottom, id="landscape")],
            onPage=_page_header_footer,
        ),
    ])

    summary = report["summary"]
    narrative = report.get("narrative") or {}
    rows = report.get("parameter_rows") or []
    service_summary = _service_summary(rows)
    story: list[Any] = []

    _cover_page(story, styles, summary)
    story.append(NextPageTemplate("Portrait"))
    story.append(PageBreak())
    _table_of_contents(story, styles)
    story.append(PageBreak())
    _sample_executive_summary(story, styles, summary, rows)
    story.append(PageBreak())
    _sample_evaluation_summary(story, styles, rows, service_summary)
    story.append(PageBreak())
    _sample_risk_matrix(story, styles, rows)
    story.append(PageBreak())
    _sample_assessment_summary(story, styles, summary, rows)
    story.append(PageBreak())
    _sample_key_observations(story, styles, summary, rows)
    story.append(PageBreak())
    _sample_service_adoption(story, styles, rows)
    story.append(PageBreak())
    _sample_deployment_risks(story, styles, rows)
    story.append(PageBreak())
    _sample_detailed_assessment(story, styles, rows)
    story.append(PageBreak())
    _conclusion_section(story, styles, summary, rows)
    story.append(NextPageTemplate("Landscape"))
    story.append(PageBreak())
    _appendix_section(story, styles, rows)

    doc.build(story)
    return path


def _cover_page(story: list[Any], styles, summary: dict[str, Any]) -> None:
    customer = _customer_label(summary)
    story.append(_CoverPageFlowable(
        customer=customer,
        tenant=_tenant_label(summary, customer),
        date=str(summary.get("assessment_date") or "DD-MM-YYYY"),
        prepared_by="CRA Platform",
    ))


def _sample_executive_summary(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    customer = _customer_label(summary)
    _section(story, styles, "Executive Summary")
    paragraphs = [
        (
            f"As part of its digital transformation strategy, {customer} engaged CRA Platform for a Copilot Readiness Assessment. "
            "The purpose of this engagement was to evaluate the Client's Microsoft 365 environment across areas including security, "
            "governance, and best practices to determine readiness for the secure and responsible adoption of Microsoft 365 Copilot."
        ),
        (
            "The assessment covered critical services including Entra ID, Exchange Online, Microsoft Teams, SharePoint Online, "
            "OneDrive for Business, and Microsoft Purview. It aimed to identify configuration gaps, policy misalignments, and "
            "potential vulnerabilities that could impact the responsible use of AI-powered tools like Copilot. By benchmarking the "
            "current environment against industry standards and Microsoft's Copilot deployment criteria, the assessment provides a "
            "clear roadmap for remediation and optimization."
        ),
        (
            f"The findings serve as a strategic foundation for {customer} to enhance its digital workplace, mitigate operational and "
            "compliance risks, and unlock the full potential of Microsoft 365 Copilot. With targeted improvements, the organization "
            "can ensure a secure and scalable AI integration that aligns with its long-term business goals."
        ),
    ]
    for paragraph in paragraphs:
        story.append(Paragraph(paragraph, styles["BodyText"]))
        story.append(Spacer(1, 8))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Purpose", styles["Heading2"]))
    purpose_items = [
        f"Evaluate the {customer} environment for alignment with industry best practices.",
        "Assess the environment across Microsoft 365 products and services like SharePoint, Teams, OneDrive for Business etc.",
        "Identify gaps that could pose security or compliance risks upon integrating Copilot.",
        "Establish a baseline for future audits and compliance tracking related to AI usage within Microsoft 365.",
        "Highlight licensing readiness and user eligibility for Microsoft 365 Copilot deployment.",
        "Provide a risk-based prioritization of remediation efforts to guide Copilot enablement planning.",
        "Offer actionable insights to strengthen governance, data protection, and identity management in preparation for AI integration.",
        "Support strategic decision-making by outlining Copilot deployment prerequisites and dependencies.",
    ]
    for item in purpose_items:
        story.append(Paragraph(item, styles["BodyText"], bulletText="-"))
        story.append(Spacer(1, 2))


def _table_of_contents(story: list[Any], styles) -> None:
    from reportlab.platypus import PageBreak

    entries = _toc_entries()
    chunks = [entries[:36], entries[36:73], entries[73:]]
    for index, chunk in enumerate(chunks):
        story.append(_toc_table(chunk, styles))
        if index < len(chunks) - 1:
            story.append(PageBreak())


def _toc_entries() -> list[tuple[str, int, int]]:
    raw = [
        ("Executive Summary", 5, 0), ("Purpose", 5, 0), ("Evaluation Summary", 6, 0),
        ("3 Pillars of Microsoft 365 Copilot Readiness Assessment", 6, 1), ("M365 Services assessed in CRA", 6, 1),
        ("Risk Category of Parameters Assessed", 7, 0), ("Summary of Assessment", 8, 0), ("Key Observations:", 9, 0),
        ("Risks of Immediate Deployment:", 12, 0), ("Recommendations:", 12, 0), ("Detailed Assessment", 13, 0),
        ("ENTRA ID", 13, 0), ("01: Custom Banned Password List", 15, 1),
        ("02: Restricted Access to Microsoft Entra Admin Centre", 15, 1), ("03: Emergency Access Accounts", 16, 1),
        ("04: Device without Compliance Policies", 16, 1), ("05: Authentication Methods Enabled", 17, 1),
        ("06: Entra - Tenant creation by non-admins", 17, 1), ("07: Global Administrator Accounts", 18, 1),
        ("08: Self-Service Password Reset Authentication Method", 18, 1), ("09: Tenant Collaboration Invitation", 19, 1),
        ("10: Administrator Consent Workflows", 19, 1), ("11: CAP Policies for Risky Sign -Ins", 20, 1),
        ("12: Conditional Access Policies (Exclusion)", 20, 1), ("13: User Consent for Applications", 21, 1),
        ("14: Entra - Third-Party App Integrations", 21, 1), ("15: Users without MFA", 22, 1),
        ("16: Auto-expiration policy for M365 Groups", 22, 1), ("17: Customer Lockbox", 23, 1),
        ("18: Guest Invite Settings", 23, 1), ("19: Guest Users count", 24, 1), ("20: User Information", 24, 1),
        ("21: Number of accounts enabled", 25, 1), ("EXCHANGE ONLINE", 26, 0),
        ("01: Mailbox Status (Active/Inactive)", 27, 1), ("02: External Storage providers in OWA", 27, 1),
        ("03: Mailbox Storage usage", 28, 1), ("04: Full Calendar Schedules able to be shared Externally", 28, 1),
        ("05: Number of Emails read/received", 29, 1), ("06: Number of emails sent", 29, 1),
        ("MICROSOFT PURVIEW", 30, 0), ("01: Audit Logs Enabled", 31, 1), ("02: Secure Score Percentage", 31, 1),
        ("03: Sensitivity Labels configured and applied", 32, 1), ("04: Sensitivity Labels applied to Teams", 32, 1),
        ("05: Compliance Score Overview", 33, 1), ("06: Information Protection Labels applied", 33, 1),
        ("07: DLP Rules configured", 34, 1), ("08: Audit Log Retention Duration", 34, 1),
        ("MICROSOFT TEAMS", 35, 0), ("01: Copilot Integration Enabled", 36, 1),
        ("02: Third Party apps allowed", 36, 1), ("03: Active/Inactive Teams", 37, 1),
        ("04: Minimum number of Owners", 37, 1), ("05: Teams with External Users", 38, 1),
        ("06: Meeting Policies Configuration", 38, 1), ("07: Orphan Teams", 39, 1),
        ("08: Teams with external guest as owner", 39, 1), ("09: Meeting Transcription enabled", 40, 1),
        ("10: Guest access enabled/disabled", 40, 1), ("11: Teams - Lobby Bypass", 41, 1),
        ("12: Teams - File Storage Option", 41, 1), ("13: Active/Inactive Teams Users", 42, 1),
        ("14: Teams - Meeting Chat", 42, 1), ("15: Meeting Recording Retention Policies", 43, 1),
        ("16: Teams - Channel Email Addresses", 43, 1), ("ONEDRIVE FOR BUSINESS", 44, 0),
        ("01: External Sharing Settings", 45, 1), ("02: Days to retain a deleted user's OneDrive", 45, 1),
        ("03: Total Active users on OneDrive", 46, 1), ("SHAREPOINT ONLINE", 47, 0),
        ("01: Permission Settings for anyone links", 48, 1),
        ("02: Sensitive SharePoint sites excluded from Copilot", 48, 1),
        ("03: Sharing Settings (External/Internal)", 49, 1),
        ("04: SharePoint and OneDrive Guest Access Expiry", 49, 1),
        ("05: Expiration Policy for Anyone links", 50, 1), ("06: Inactive site policies", 50, 1),
        ("07: Active Sites count", 51, 1), ("08: Site Ownership policies", 51, 1),
        ("09: Active Users on SharePoint", 52, 1), ("10: SharePoint - Modern Authentication", 52, 1),
        ("11: Storage Quota Consumption", 53, 1), ("Conclusion", 54, 0),
    ]
    return raw


def _toc_table(entries: list[tuple[str, int, int]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    rows = []
    for title, page, indent in entries:
        text = ("&nbsp;&nbsp;&nbsp;&nbsp;" * indent) + _escape(title)
        leader = "." * (72 - min(60, len(title)))
        rows.append([Paragraph(text, styles["Fine"]), Paragraph(leader, styles["Fine"]), Paragraph(str(page), styles["Fine"])])
    table = Table(rows, colWidths=[245, 200, 34], rowHeights=12)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]
    for idx, (title, _page, indent) in enumerate(entries):
        if indent == 0:
            style.append(("FONTNAME", (0, idx), (2, idx), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table


def _sample_evaluation_summary(story: list[Any], styles, rows: list[dict[str, Any]], service_summary: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Evaluation Summary")
    story.append(Paragraph("3 Pillars of Microsoft 365 Copilot Readiness Assessment", styles["Heading2"]))
    for item in ["Governance", "Security", "Best Practices"]:
        story.append(Paragraph(item, styles["BodyText"], bulletText="-"))
    story.append(Spacer(1, 10))
    story.append(_pie_chart_box("3 Pillars of CRA", _pillar_distribution(rows), width=458, height=180))
    story.append(Spacer(1, 20))
    story.append(Paragraph("M365 Services assessed in CRA", styles["Heading2"]))
    for item in ["Entra ID", "Exchange Online", "Microsoft Purview", "Microsoft Teams", "OneDrive for Business", "SharePoint Online"]:
        story.append(Paragraph(item, styles["BodyText"], bulletText="-"))
    story.append(Spacer(1, 10))
    service_counts = {item["service"]: item["pass"] + item["fail"] for item in service_summary}
    story.append(_pie_chart_box("M365 Services", service_counts, width=458, height=190))


def _sample_risk_matrix(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Risk Score Matrix")
    story.append(Paragraph("The findings presented in this report are graded according to the following levels of severity:", styles["BodyText"]))
    story.append(Spacer(1, 28))
    story.append(_risk_score_matrix_visual())
    story.append(Spacer(1, 28))
    story.append(Paragraph("Risk Category of Parameters Assessed", styles["Heading2"]))
    story.append(Paragraph("The following chart provides consolidated parameters based on risk category assessed during the engagement:", styles["BodyText"]))
    story.append(Spacer(1, 18))
    story.append(_pie_chart_box("Risk-wise Parameters", {**_risk_counts(rows), "Informational": _info_count(rows)}, width=440, height=205))


def _sample_assessment_summary(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Summary of Assessment")
    total = int(summary.get("parameter_total") or len(rows) or 0)
    failed = _total_gap_count(rows)
    readiness = float(summary.get("overall_readiness") or _readiness_from_rows(rows))
    story.append(Paragraph(
        "The Copilot Readiness Assessment uncovered configuration gaps and policy deficiencies that could impact the secure "
        "and compliant adoption of Microsoft Copilot. Each finding has been categorized by severity and mapped to specific "
        "areas of risk within the Microsoft 365 environment.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Overall Readiness:</b>", styles["BodyText"]))
    story.append(Paragraph("Based on the findings, the Client's current readiness level for Copilot integration is assessed as:", styles["BodyText"]))
    story.append(Paragraph(f"<b>Readiness Level: <font color='red'>{_readiness_level(summary, rows)}</font></b>", styles["BodyText"]))
    story.append(Paragraph(f"<b>Readiness Gaps: <font color='red'>{failed} out of {total}</font></b>", styles["BodyText"]))
    story.append(Paragraph("<font color='red'><i>Significant remediation is required prior to enabling Copilot in the production environment.</i></font>", styles["BodyText"]))
    story.append(Spacer(1, 10))
    story.append(_readiness_bar_visual(readiness))
    story.append(Spacer(1, 14))
    story.append(_stacked_service_pillar_chart(rows, "Executive Summary - M365 Services and 3 Pillars", mode="service_pillar"))


def _sample_key_observations(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    story.append(_stacked_service_pillar_chart(rows, "Executive Summary - Severity and 3 Pillars", mode="severity_pillar"))
    story.append(Spacer(1, 22))
    _section(story, styles, "Key Observations")
    for item in _observation_bullets(summary, rows):
        story.append(Paragraph(item, styles["BodyText"], bulletText="-"))
        story.append(Spacer(1, 5))
    story.append(Spacer(1, 18))
    story.append(_license_chart_visual(rows))
    story.append(Spacer(1, 16))
    story.append(Paragraph(_user_info_sentence(rows), styles["BodyText"], bulletText="-"))
    story.append(Spacer(1, 8))
    story.append(_user_information_chart(rows))


def _sample_deployment_risks(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Risks of Immediate Deployment:")
    story.append(Paragraph("Proceeding with Copilot activation in the current state may lead to:", styles["BodyText"]))
    story.append(Spacer(1, 24))
    story.append(_deployment_risk_visual())
    story.append(Spacer(1, 28))
    _section(story, styles, "Recommendations:")
    recommendations = [
        ("Remediation of identified gaps:", "Address all findings regardless of severity to meet cybersecurity baseline standards."),
        ("Postpone Deployment:", "Due to the current maturity level of the environment, it is recommended to adopt Copilot deployment after all critical and high-priority gaps are resolved."),
        ("Futureproofing:", "Implementing the recommendations provided will reduce security risks and ensure regulatory compliance during and after Copilot integration."),
    ]
    for title, body in recommendations:
        story.append(Paragraph(f"<b>{title}</b> {body}", styles["BodyText"], bulletText="-"))
        story.append(Spacer(1, 6))


def _sample_recommendations(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    _section(story, styles, "Recommendations")
    story.append(_timeline([
        ("Phase 1", "Critical", "0-30 Days", _risk_counts(rows).get("Critical", 0), "Resolve deployment blockers and identity exposure."),
        ("Phase 2", "High", "30-60 Days", _risk_counts(rows).get("High", 0), "Harden collaboration, compliance, and information protection controls."),
        ("Phase 3", "Medium", "60-90 Days", _risk_counts(rows).get("Medium", 0), "Improve operational maturity and governance consistency."),
        ("Phase 4", "Optimization", "90+ Days", _risk_counts(rows).get("Low", 0) + _info_count(rows), "Establish continuous readiness monitoring."),
    ], styles))
    actionable = [row for row in rows if _normalized_status(row) != "pass"]
    if actionable:
        story.append(_recommendation_table(actionable[:12], "high", styles))


def _sample_detailed_assessment(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, PageBreak, Spacer

    _section(story, styles, "Detailed Assessment")
    story.append(Paragraph("The following sections summarize findings discovered during the course of this engagement, organized by Microsoft 365 service.", styles["BodyText"]))
    story.append(Spacer(1, 12))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_canonical_service(row.get("service"))].append(row)
    for service in SERVICE_NAMES:
        service_rows = grouped.get(service, [])
        if not service_rows:
            continue
        story.append(PageBreak())
        _service_findings_summary(story, styles, service, service_rows)
        for start in range(0, len(service_rows), 2):
            story.append(PageBreak())
            _sample_finding_pair_page(story, styles, service_rows[start:start + 2], start + 1)


def _service_overview_page(story: list[Any], styles, service: str, rows: list[dict[str, Any]]) -> None:
    _section(story, styles, service.upper())
    passed = len([row for row in rows if _normalized_status(row) == "pass"])
    failed = len([row for row in rows if _normalized_status(row) in {"fail", "failed"}])
    readiness = round((passed / len(rows)) * 100, 2) if rows else 0
    cards = [
        ("Readiness", f"{readiness}%", "pass" if readiness >= 80 else "high" if readiness >= 50 else "critical"),
        ("Controls", len(rows), "blue"),
        ("Pass", passed, "pass"),
        ("Fail", failed, "failed"),
    ]
    story.append(_card_grid(cards, styles, columns=4))
    story.append(_callout("Service Overview", _service_overview_text(service, readiness), styles, color_key="blue"))
    story.append(_risk_heatmap([*rows], styles))


def _sample_service_adoption(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer, Table

    adoption = _service_adoption(rows)
    story.append(Paragraph(_adoption_sentence(adoption), styles["BodyText"], bulletText="-"))
    story.append(Spacer(1, 18))
    story.append(Table([
        [_adoption_donut("SharePoint Accounts", adoption["SharePoint"]), _adoption_donut("Onedrive Accounts", adoption["OneDrive"])],
        [_adoption_donut("Teams Usage", adoption["Teams"]), _adoption_donut("Outlook Usage", adoption["Outlook"])],
    ], colWidths=[240, 240], rowHeights=[230, 230]))


def _service_adoption(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    return {
        "SharePoint": _extract_percent(rows, ["sharepoint", "active"]),
        "OneDrive": _extract_percent(rows, ["onedrive", "active"]),
        "Teams": _extract_percent(rows, ["teams", "active"]),
        "Outlook": _extract_percent(rows, ["mailbox", "email", "outlook"]),
    }


def _extract_percent(rows: list[dict[str, Any]], tokens: list[str]) -> float | None:
    for row in rows:
        text = f"{row.get('title', '')} {row.get('actual_result', '')} {row.get('finding', '')}".lower()
        if all(token in text for token in tokens[:1]) and any(token in text for token in tokens):
            pct = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            if pct:
                return float(pct.group(1))
            ratio = re.search(r"active ratio[:\s]+(\d+(?:\.\d+)?)", text)
            if ratio:
                value = float(ratio.group(1))
                return value * 100 if value <= 1 else value
            active_total = re.search(r"(\d+)\s+(?:out of|of)\s+(\d+)", text)
            if active_total:
                active = float(active_total.group(1))
                total = float(active_total.group(2))
                return round(active / total * 100, 2) if total else None
    return None


def _adoption_sentence(adoption: dict[str, float | None]) -> str:
    if any(value is None for value in adoption.values()):
        missing = ", ".join(name for name, value in adoption.items() if value is None)
        return f"Service adoption evidence is incomplete for {missing}. The report only displays validated activity percentages where assessment evidence is available."
    return (
        f"In the past 60 days, {adoption['OneDrive']:.0f}% of OneDrive users, {adoption['Teams']:.0f}% of Microsoft Teams users, "
        f"{adoption['Outlook']:.0f}% of outlook users and {adoption['SharePoint']:.0f}% of SharePoint users have been active, "
        "indicating strong engagement across Microsoft 365 core services."
    )


def _adoption_donut(title: str, percent: float | None):
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Circle, Drawing, Rect, String

    drawing = Drawing(205, 205)
    drawing.add(Rect(0, 0, 205, 205, strokeColor=_black(), fillColor=None, strokeWidth=1))
    drawing.add(String(102, 182, title, textAnchor="middle", fontName="Helvetica-Bold", fontSize=11, fillColor=_color("muted")))
    if percent is None:
        drawing.add(Circle(102, 108, 66, fillColor=_color("border"), strokeColor=None))
        drawing.add(Circle(102, 108, 56, fillColor=_white(), strokeColor=None))
        drawing.add(String(102, 105, "No data", textAnchor="middle", fontName="Helvetica-Bold", fontSize=16, fillColor=_black()))
        drawing.add(String(102, 86, "validated", textAnchor="middle", fontSize=8, fillColor=_color("muted")))
        return drawing
    percent = max(0, min(100, float(percent)))
    pie = Pie()
    pie.x = 36
    pie.y = 42
    pie.width = 132
    pie.height = 132
    pie.data = [percent, max(0.001, 100 - percent)]
    pie.labels = ["", ""]
    pie.slices[0].fillColor = _color("pass") if percent else _color("border")
    pie.slices[1].fillColor = _color("border")
    pie.slices[0].strokeWidth = 0
    pie.slices[1].strokeWidth = 0
    drawing.add(pie)
    drawing.add(Circle(102, 108, 56, fillColor=_white(), strokeColor=None))
    drawing.add(String(102, 102, f"{percent:.0f}%", textAnchor="middle", fontName="Helvetica-Bold", fontSize=20, fillColor=_black()))
    return drawing


def _deployment_risk_visual():
    from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String

    drawing = Drawing(500, 210)
    risks = [
        "Unauthorized access to sensitive business data.",
        "Inadequate auditing and monitoring of AI-driven activity.",
        "Compliance violations with internal and external regulations.",
        "Reduced user trust and operational inconsistencies due to misconfigured policies.",
    ]
    y = 172
    for idx, risk in enumerate(risks):
        circle_y = y + 8
        drawing.add(Line(72, circle_y + 34, 112, circle_y - 34, strokeColor=_color("blue"), strokeWidth=1.2))
        drawing.add(Circle(86, circle_y, 24, strokeColor=_color("blue"), fillColor=_color("blue"), strokeWidth=1))
        drawing.add(Rect(108, y - 14, 360, 38, strokeColor=None, fillColor=_black()))
        drawing.add(Rect(108, y - 14, 190, 38, strokeColor=None, fillColor=_color("blue")))
        drawing.add(String(122, y + 1, risk[:72], fontSize=10, fillColor=_white()))
        if len(risk) > 72:
            drawing.add(String(122, y - 11, risk[72:132], fontSize=10, fillColor=_white()))
        y -= 52
    return drawing


def _assessment_table(rows: list[list[Any]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    rendered = []
    for row_index, row in enumerate(rows):
        rendered.append([Paragraph(_clean(value), styles["Fine"] if row_index else styles["CardLabel"]) for value in row])
    table = Table(rendered, repeatRows=1, colWidths=[42, 230, 85, 58, 75])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _color("blue")),
        ("TEXTCOLOR", (0, 0), (-1, 0), _white()),
        ("GRID", (0, 0), (-1, -1), 0.6, _black()),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (4, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for idx, row in enumerate(rows[1:], start=1):
        status = str(row[3]).lower()
        severity = str(row[4]).lower()
        style.append(("TEXTCOLOR", (3, idx), (3, idx), _color("pass") if "pass" in status else _color("failed")))
        style.append(("BACKGROUND", (4, idx), (4, idx), _severity_cell_color(severity)))
        style.append(("TEXTCOLOR", (4, idx), (4, idx), _white() if severity in {"critical", "high"} else _black()))
    table.setStyle(TableStyle(style))
    return table


def _sample_finding_pair_page(story: list[Any], styles, rows: list[dict[str, Any]], start_index: int) -> None:
    from reportlab.platypus import Spacer

    for offset, row in enumerate(rows):
        story.append(_finding_block(row, start_index + offset, styles))
        story.append(Spacer(1, 26))


def _finding_block(row: dict[str, Any], index: int, styles):
    from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

    title = f"{index:02d}: {_clean(row.get('title') or 'Finding')}"
    header = Table([[Paragraph(title, styles["CardLabel"])]], colWidths=[455], rowHeights=[28])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _color("blue")),
        ("TEXTCOLOR", (0, 0), (-1, -1), _white()),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    severity = _severity_label(row.get("severity"))
    status = _finding_outcome(row)
    status_color = "green" if status == "Pass" else "red"
    body = [
        header,
        Spacer(1, 12),
        Paragraph(f"<b>Risk Rating: {severity} - <font color='{status_color}'>{status}</font></b>", styles["BodyText"]),
        _severity_bar(severity),
        Spacer(1, 12),
        Paragraph("<b>Description:</b>", styles["BodyText"]),
        Paragraph(_executive_result(row), styles["BodyText"]),
        Spacer(1, 8),
        Paragraph("<b>Risk:</b>", styles["BodyText"]),
        Paragraph(_copilot_impact(row), styles["BodyText"]),
        Spacer(1, 6),
        Paragraph(f"<font color='blue'><u>{_microsoft_reference(row)}</u></font>", styles["BodyText"]),
    ]
    return KeepTogether(body)


def _severity_bar(severity: str):
    from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String

    labels = ["Critical", "High", "Medium", "Low", "Informational"]
    colors = ["critical", "failed", "high", "medium", "pass"]
    severity = _severity_label(severity)
    drawing = Drawing(460, 68)
    x = 0
    y = 32
    width = 91
    for label, color_key in zip(labels, colors):
        drawing.add(Rect(x, y, width - 2, 20, strokeColor=_black(), fillColor=_color(color_key), strokeWidth=1))
        drawing.add(String(x + width / 2, 8, label, textAnchor="middle", fontSize=9, fillColor=_black()))
        if label == severity:
            drawing.add(Polygon([x + width / 2, y - 2, x + width / 2 - 7, y - 22, x + width / 2 + 7, y - 22], strokeColor=_black(), fillColor=_white(), strokeWidth=1.5))
    drawing.add(Line(0, y - 5, 455, y - 5, strokeColor=_black(), strokeWidth=1.5))
    return drawing


def _severity_cell_color(severity: str):
    if severity == "critical":
        return _color("critical")
    if severity == "high":
        return _color("failed")
    if severity == "medium":
        return _color("high")
    if severity == "low":
        return _color("medium")
    return _color("pass")


def _service_findings_summary(story: list[Any], styles, service: str, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph

    _section(story, styles, service.upper())
    table_rows = [["S. No", "Parameter", "CRA Pillar", "Finding", "Severity"]]
    for index, row in enumerate(rows, start=1):
        table_rows.append([
            f"{index:02d}",
            row.get("title", "-"),
            _pillar_name(row).replace("Best Practices", "Best Practice"),
            _finding_outcome(row),
            _severity_label(row.get("severity")),
        ])
    story.append(_assessment_table(table_rows, styles))


def _sample_finding_page(story: list[Any], styles, row: dict[str, Any], index: int) -> None:
    from reportlab.platypus import Paragraph, Spacer

    title = _clean(row.get("title") or f"Finding {index}")
    severity = _severity_label(row.get("severity"))
    status = _status_label(row)
    story.append(Paragraph(f"{index:02d}: {title}", styles["SectionTitle"]))
    story.append(_callout("Risk Rating", f"{severity} - {status}", styles, color_key=str(row.get("severity") or "low").lower()))
    story.append(Spacer(1, 8))
    blocks = [
        ("Description", row.get("description") or "This readiness control was assessed as part of the Copilot deployment baseline."),
        ("Dynamic Assessment Result", _executive_result(row)),
        ("Risk", _business_risk(row)),
        ("Impact on Copilot", _copilot_impact(row)),
        ("Microsoft Documentation", _microsoft_reference(row)),
        ("Evidence", _evidence_summary(row)),
        ("Recommendation", _remediation_guidance(row)),
    ]
    for heading, body in blocks:
        story.append(Paragraph(heading, styles["Heading3"]))
        story.append(Paragraph(_clean(body), styles["BodyText"]))
        story.append(Spacer(1, 8))


def _executive_dashboard(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Executive Dashboard")
    risk_counts = _risk_counts(rows)
    status_counts = _status_counts(rows)
    cards = [
        ("Readiness Score", f"{summary.get('overall_readiness', 0)}%", "blue"),
        ("Readiness Level", _readiness_level(summary, rows), _readiness_color(summary, rows)),
        ("Critical Findings", risk_counts.get("Critical", 0), "critical"),
        ("High Findings", risk_counts.get("High", 0), "high"),
        ("Medium Findings", risk_counts.get("Medium", 0), "medium"),
        ("Low Findings", risk_counts.get("Low", 0), "low"),
        ("Coverage", _coverage_percent(summary), "pass"),
        ("Eligible Users", _eligible_users(rows), "blue"),
        ("Licensing Gap", status_counts.get("Licensing Required", 0), "licensing_required"),
        ("Copilot Recommendation", _short_recommendation(summary), _readiness_color(summary, rows)),
    ]
    story.append(_card_grid(cards, styles, columns=5))
    story.append(Spacer(1, 18))
    story.append(Paragraph("This dashboard summarizes the current Microsoft 365 Copilot deployment posture for executive review.", styles["Muted"]))


def _visual_scorecards(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]], service_summary: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Spacer, Table

    _section(story, styles, "Visual Scorecards")
    score = float(summary.get("overall_readiness") or 0)
    story.append(Table([[_readiness_gauge(score), _donut_chart("Pass vs Fail", _status_counts(rows)), _donut_chart("Risk Mix", _risk_counts(rows))]], colWidths=[178, 178, 178]))
    story.append(Spacer(1, 12))
    story.append(Table([[
        _donut_chart("Pillar Mix", _pillar_distribution(rows)),
        _donut_chart("Service Distribution", {item["service"]: item["pass"] + item["fail"] for item in service_summary}),
        _donut_chart("Licensing Status", _licensing_status(rows)),
    ]], colWidths=[178, 178, 178]))


def _executive_summary_visuals(story: list[Any], styles, summary: dict[str, Any], narrative: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Executive Summary Visuals")
    story.append(_snapshot_cards(summary, rows, styles))
    story.append(Spacer(1, 12))
    story.append(_two_column_lists("Top 5 Risks", _top_items(rows, passing=False), "Top 5 Strengths", _top_items(rows, passing=True), styles))
    story.append(Spacer(1, 12))
    recommendation = summary.get("deployment_recommendation") or narrative.get("conclusion") or "Prioritize remediation and reassess before broad Copilot deployment."
    story.append(_callout("Deployment Recommendation", recommendation, styles, color_key=_readiness_color(summary, rows)))
    story.append(Spacer(1, 8))
    story.append(_callout("Business Impact Summary", "Current risks can affect Copilot data exposure, identity trust, collaboration governance, compliance assurance, and deployment confidence.", styles, color_key="blue"))


def _risk_heatmap_section(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    _section(story, styles, "Risk Heatmap")
    story.append(_risk_heatmap(rows, styles))


def _pillar_maturity_section(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    _section(story, styles, "Pillar Maturity")
    maturity = _pillar_maturity(rows)
    cards = []
    for pillar, score in maturity.items():
        gap = max(0, 80 - score)
        cards.append((pillar, f"{score}%", "pass" if score >= 80 else "high" if score >= 50 else "critical"))
        cards.append(("Target", "80%", "blue"))
        cards.append(("Gap", f"{gap}%", "medium" if gap else "pass"))
    story.append(_card_grid(cards[:9], styles, columns=3))
    story.append(_maturity_bars(maturity, styles))


def _service_readiness_section(story: list[Any], styles, service_summary: list[dict[str, Any]]) -> None:
    _section(story, styles, "Service Readiness")
    story.append(_service_readiness_bars(service_summary, styles))


def _detailed_findings_section(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph

    _section(story, styles, "Detailed Findings")
    failed_rows = [row for row in rows if _normalized_status(row) in {"fail", "failed"}]
    failed_rows.sort(key=lambda row: SEVERITY_RANK.get(str(row.get("severity", "info")).lower(), 1), reverse=True)
    if not failed_rows:
        story.append(Paragraph("No failed parameters were identified.", styles["BodyText"]))
        return
    for row in failed_rows:
        story.append(_finding_card(row, styles))


def _positive_findings_section(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Positive Findings")
    passed = [row for row in rows if _normalized_status(row) == "pass"]
    if not passed:
        story.append(Paragraph("No passing parameters were identified.", styles["BodyText"]))
        return
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in passed:
        grouped[_canonical_service(row.get("service"))].append(row)
    for service in SERVICE_NAMES:
        items = grouped.get(service, [])
        if not items:
            continue
        story.append(Paragraph(service, styles["Heading2"]))
        story.append(_compact_list_table([[row.get("title"), row.get("actual_result") or row.get("finding") or "-"] for row in items[:14]], styles))
        story.append(Spacer(1, 8))


def _licensing_dashboard(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Spacer, Table

    _section(story, styles, "Licensing Dashboard")
    licensing_required = len([row for row in rows if _normalized_status(row) == "licensing_required"])
    licensed = len([row for row in rows if "license" in str(row.get("title", "")).lower() and _normalized_status(row) == "pass"])
    eligible = _eligible_users(rows)
    cards = [
        ("Eligible Users", eligible, "blue"),
        ("Licensed Users", licensed, "pass"),
        ("Missing Licenses", licensing_required, "licensing_required"),
        ("Copilot Ready Users", eligible if licensing_required == 0 else "Pending", "pass" if licensing_required == 0 else "high"),
    ]
    story.append(_card_grid(cards, styles, columns=4))
    story.append(Spacer(1, 14))
    story.append(Table([[_donut_chart("Licensing Status", _licensing_status(rows)), _license_gap_table(rows, styles)]], colWidths=[230, 300]))


def _recommendations_section(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Recommendations")
    actionable = [row for row in rows if _normalized_status(row) != "pass"]
    if not actionable:
        story.append(Paragraph("No remediation recommendations are required for passing controls.", styles["BodyText"]))
        return
    for severity in ["critical", "high", "medium", "low"]:
        items = [row for row in actionable if str(row.get("severity", "info")).lower() == severity]
        if not items:
            continue
        story.append(Paragraph(severity.title(), styles["Heading2"]))
        story.append(_recommendation_table(items, severity, styles))
        story.append(Spacer(1, 8))


def _roadmap_section(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    _section(story, styles, "Remediation Roadmap")
    counts = Counter(str(row.get("severity", "info")).lower() for row in rows if _normalized_status(row) != "pass")
    phases = [
        ("Phase 1", "Critical", "0-30 Days", counts.get("critical", 0), "Remove deployment blockers."),
        ("Phase 2", "High", "30-60 Days", counts.get("high", 0), "Reduce material security and governance exposure."),
        ("Phase 3", "Medium", "60-90 Days", counts.get("medium", 0), "Improve operational consistency."),
        ("Phase 4", "Optimization", "90+ Days", counts.get("low", 0) + counts.get("info", 0), "Establish continuous readiness monitoring."),
    ]
    story.append(_timeline(phases, styles))


def _conclusion_section(story: list[Any], styles, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    _section(story, styles, "Conclusion")
    for paragraph in _conclusion(summary, rows):
        story.append(Paragraph(paragraph, styles["BodyText"]))
        story.append(Spacer(1, 7))


def _appendix_section(story: list[Any], styles, rows: list[dict[str, Any]]) -> None:
    _section(story, styles, "Appendix A. Complete Parameter Matrix")
    story.append(_parameter_matrix(rows, styles))


def _section(story: list[Any], styles, title: str) -> None:
    from reportlab.platypus import Paragraph, Spacer

    story.append(Paragraph(title, styles["SectionTitle"]))
    story.append(Spacer(1, 6))


def _page_header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setStrokeColor(_color("border"))
    canvas.setLineWidth(0.4)
    canvas.line(34, 30, width - 34, 30)
    canvas.setFillColor(_color("muted"))
    canvas.setFont("Helvetica", 6)
    canvas.drawString(34, 18, "Copilot Readiness Assessment")
    canvas.drawRightString(width - 34, 18, f"{doc.page} | Page")
    canvas.restoreState()


def _blank_page(canvas, doc) -> None:
    return None


def _card_grid(cards: list[tuple[Any, Any, str]], styles, *, columns: int):
    from reportlab.platypus import Paragraph, Table, TableStyle

    rows = []
    width = 520 / columns
    for start in range(0, len(cards), columns):
        table_row = []
        for label, value, color_key in cards[start:start + columns]:
            value_text = _clean(value)
            cell = [
                Paragraph(value_text[:36], styles["CardValue"]),
                Paragraph(_clean(label), styles["CardLabel"]),
            ]
            table_row.append(cell)
        while len(table_row) < columns:
            table_row.append("")
        rows.append(table_row)
    table = Table(rows, colWidths=[width] * columns, rowHeights=[72] * len(rows), hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, _color("border")),
        ("BACKGROUND", (0, 0), (-1, -1), _color("paper")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]
    for index, card in enumerate(cards):
        row = index // columns
        col = index % columns
        style.append(("LINEBEFORE", (col, row), (col, row), 4, _color(card[2])))
    table.setStyle(TableStyle(style))
    return table


class _CoverPageFlowable(Flowable):
    def __init__(self, *, customer: str, tenant: str, date: str, prepared_by: str) -> None:
        super().__init__()
        self.customer = customer
        self.tenant = tenant
        self.date = date
        self.prepared_by = prepared_by
        self.width = 520
        self.height = 742

    def wrap(self, availWidth, availHeight):
        self.width = min(availWidth, 520)
        self.height = min(availHeight, 742)
        return self.width, self.height

    def drawOn(self, canvas, x, y, _sW=0):
        canvas.saveState()
        canvas.translate(x, y)
        self._draw_background(canvas)
        self._draw_title(canvas)
        self._draw_copilot_mark(canvas)
        self._draw_document_art(canvas)
        canvas.restoreState()

    def _draw_background(self, canvas) -> None:
        from reportlab.lib import colors

        canvas.setFillColor(colors.HexColor("#b8d8d6"))
        canvas.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#a9c4cd"))
        canvas.rect(0, 0, self.width, self.height * 0.24, stroke=0, fill=1)

    def _draw_title(self, canvas) -> None:
        canvas.setFillColor(_white())
        canvas.setFont("Helvetica-Bold", 24)
        canvas.drawString(24, self.height - 190, "Copilot Readiness Assessment")
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(52, self.height - 235, _cover_date(self.date))
        canvas.drawString(52, self.height - 265, "Prepared for:")
        canvas.drawString(52, self.height - 295, self.customer)
        canvas.drawString(52, self.height - 325, f"Tenant: {self.tenant}")
        canvas.drawString(52, self.height - 355, f"Prepared by: {self.prepared_by}")

    def _draw_copilot_mark(self, canvas) -> None:
        from reportlab.lib import colors

        x = 30
        y = 125
        colors_list = ["#18a8f2", "#0b49d8", "#b94fed", "#ff7b4a", "#e82736", "#f5cc18", "#45b85b"]
        points = [
            [(x + 20, y + 220), (x + 170, y + 220), (x + 115, y + 85), (x + 0, y + 85)],
            [(x + 145, y + 220), (x + 235, y + 220), (x + 185, y + 80), (x + 110, y + 82)],
            [(x + 185, y + 82), (x + 285, y + 82), (x + 335, y + 185), (x + 225, y + 185)],
            [(x + 120, y + 82), (x + 210, y + 82), (x + 160, y + 10), (x + 90, y + 45)],
        ]
        for idx, poly in enumerate(points):
            canvas.setFillColor(colors.HexColor(colors_list[idx]))
            path = canvas.beginPath()
            path.moveTo(*poly[0])
            for point in poly[1:]:
                path.lineTo(*point)
            path.close()
            canvas.drawPath(path, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#b8d8d6"))
        path = canvas.beginPath()
        path.moveTo(x + 105, y + 82)
        path.curveTo(x + 142, y + 92, x + 168, y + 158, x + 188, y + 185)
        path.lineTo(x + 224, y + 185)
        path.curveTo(x + 202, y + 135, x + 177, y + 90, x + 146, y + 82)
        path.close()
        canvas.drawPath(path, stroke=0, fill=1)

    def _draw_document_art(self, canvas) -> None:
        from reportlab.lib import colors

        x = self.width - 175
        y = self.height - 385
        canvas.setFillColor(colors.HexColor("#f7ad42"))
        canvas.roundRect(x, y - 95, 60, 65, 5, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#ffffff"))
        canvas.roundRect(x + 58, y - 82, 76, 122, 6, stroke=0, fill=1)
        canvas.setStrokeColor(colors.HexColor("#58a6dc"))
        canvas.setLineWidth(2)
        canvas.roundRect(x + 58, y - 82, 76, 122, 6, stroke=1, fill=0)
        canvas.setFillColor(colors.HexColor("#f7ad42"))
        for offset in [8, 32, 56]:
            canvas.circle(x + 72, y + 25 - offset, 4, stroke=0, fill=1)
        canvas.setStrokeColor(colors.HexColor("#58a6dc"))
        for offset in [8, 32, 56]:
            canvas.line(x + 84, y + 25 - offset, x + 118, y + 25 - offset)
        canvas.setFillColor(colors.HexColor("#0ea5e9"))
        canvas.roundRect(x + 130, y - 36, 42, 62, 4, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#ffffff"))
        canvas.rect(x + 140, y - 22, 6, 20, stroke=0, fill=1)
        canvas.rect(x + 150, y - 12, 6, 10, stroke=0, fill=1)
        canvas.rect(x + 160, y - 28, 6, 26, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#dfe9ef"))
        for offset in [0, -16, -32]:
            canvas.ellipse(x + 104, y - 107 + offset, x + 158, y - 91 + offset, stroke=0, fill=1)
            canvas.rect(x + 104, y - 99 + offset, 54, 16, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#ffffff"))
        canvas.ellipse(x + 104, y - 91, x + 158, y - 75, stroke=0, fill=1)


def _cover_date(value: str) -> str:
    if not value or value == "-":
        return "DD-MM-YYYY"
    return value[:10]


def _snapshot_cards(summary: dict[str, Any], rows: list[dict[str, Any]], styles):
    risks = _top_items(rows, passing=False)
    strengths = _top_items(rows, passing=True)
    return _card_grid([
        ("Key Findings", len([row for row in rows if _normalized_status(row) in {"fail", "failed"}]), "critical"),
        ("Top Risk", risks[0] if risks else "No critical risk", "high"),
        ("Top Strength", strengths[0] if strengths else "No pass recorded", "pass"),
        ("Coverage", _coverage_percent(summary), "blue"),
    ], styles, columns=4)


def _pie_chart_box(title: str, values: dict[str, Any], *, width: int, height: int):
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing, Line, Rect, String

    cleaned = {str(key): float(value or 0) for key, value in values.items() if float(value or 0) > 0}
    if not cleaned:
        cleaned = {"No data": 1}
    total = sum(cleaned.values())
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, strokeColor=_black(), fillColor=None, strokeWidth=1))
    drawing.add(String(width / 2, height - 20, title, textAnchor="middle", fontName="Helvetica-Bold", fontSize=13, fillColor=_black()))
    pie = Pie()
    pie.x = width / 2 - 76
    pie.y = 48
    pie.width = 152
    pie.height = 98
    pie.data = list(cleaned.values())
    pie.labels = ["" for _ in cleaned]
    for idx, key in enumerate(cleaned.keys()):
        pie.slices[idx].fillColor = _slice_color(key)
        pie.slices[idx].strokeWidth = 0.4
        pie.slices[idx].popout = 2 if idx == 0 else 0
    drawing.add(pie)
    label_positions = _label_positions(width, height, len(cleaned))
    for idx, (key, value) in enumerate(cleaned.items()):
        pct = round((value / total) * 100)
        lx, ly = label_positions[idx % len(label_positions)]
        drawing.add(Rect(lx - 4, ly - 9, 106, 16, strokeColor=_black(), fillColor=_white(), strokeWidth=0.5))
        drawing.add(String(lx, ly - 4, f"{key} {pct}%", fontSize=6.2, fillColor=_black()))
        drawing.add(Line(lx + 48, ly - 1, width / 2, height / 2, strokeColor=_black(), strokeWidth=0.5))
    legend_y = 20
    legend_x = max(20, width / 2 - (len(cleaned) * 38))
    for idx, key in enumerate(cleaned.keys()):
        x = legend_x + idx * 75
        drawing.add(Rect(x, legend_y, 6, 6, strokeColor=None, fillColor=_slice_color(key)))
        drawing.add(String(x + 9, legend_y, str(key)[:18], fontSize=5.8, fillColor=_black()))
    return drawing


def _label_positions(width: int, height: int, count: int) -> list[tuple[float, float]]:
    base = [
        (width - 120, height - 62),
        (width - 130, 58),
        (48, 68),
        (50, height - 66),
        (width / 2 - 25, height - 42),
        (width / 2 + 75, 34),
    ]
    return base[:max(1, count)]


def _risk_score_matrix_visual():
    from reportlab.graphics.shapes import Circle, Drawing, Polygon, String

    drawing = Drawing(500, 220)
    items = [
        ("Critical", "critical", "The risks posed by this finding are of a critical nature and can lead to full system compromise."),
        ("High", "failed", "The risks posed by this finding are of high impact and can lead to partial or full system compromise."),
        ("Medium", "high", "The risks posed by this finding are of moderate impact, existing controls may mitigate."),
        ("Low", "medium", "The risk posed by this finding is low due to potential impact or difficulty of exploitation."),
        ("Informational", "pass", "A potential indirect risk that may contribute to or lead to an incident."),
    ]
    x = 55
    for label, color_key, body in items:
        drawing.add(Circle(x, 145, 42, strokeColor=_color(color_key), fillColor=_very_light(color_key), strokeWidth=3))
        drawing.add(String(x, 143, label, textAnchor="middle", fontSize=8, fillColor=_black()))
        if label != "Informational":
            drawing.add(Polygon([x + 42, 113, x + 66, 145, x + 42, 187], strokeColor=None, fillColor=_color(color_key)))
        words = body.split()
        lines = [" ".join(words[i:i + 6]) for i in range(0, len(words), 6)]
        y = 78
        for line in lines[:6]:
            drawing.add(String(x - 36, y, line, fontSize=5.5, fillColor=_black()))
            y -= 8
        x += 100
    return drawing


def _readiness_bar_visual(readiness: float):
    from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String

    readiness = max(0, min(100, float(readiness or 0)))
    drawing = Drawing(500, 92)
    bar_x = 55
    bar_y = 34
    bar_w = 390
    drawing.add(Rect(bar_x, bar_y, bar_w * 0.46, 9, strokeColor=None, fillColor=_color("pass")))
    drawing.add(Rect(bar_x + bar_w * 0.46, bar_y, bar_w * 0.54, 9, strokeColor=None, fillColor=_color("failed")))
    marker_x = bar_x + (readiness / 100) * bar_w
    drawing.add(Polygon([marker_x, bar_y + 14, marker_x - 9, bar_y + 38, marker_x + 9, bar_y + 38], strokeColor=None, fillColor=_color("blue")))
    drawing.add(String(marker_x, bar_y + 50, f"{readiness:.2f}%", textAnchor="middle", fontName="Helvetica-Bold", fontSize=13, fillColor=_color("blue")))
    for pct in range(0, 101, 10):
        x = bar_x + (pct / 100) * bar_w
        drawing.add(Line(x, bar_y - 2, x, bar_y + 13, strokeColor=_color("border"), strokeWidth=0.4))
        drawing.add(String(x, bar_y - 18, f"{pct}%", textAnchor="middle", fontSize=6, fillColor=_black()))
    drawing.add(Rect(bar_x + 190, 4, 7, 7, strokeColor=None, fillColor=_color("pass")))
    drawing.add(String(bar_x + 200, 4, "Pass", fontSize=6, fillColor=_black()))
    drawing.add(Rect(bar_x + 235, 4, 7, 7, strokeColor=None, fillColor=_color("failed")))
    drawing.add(String(bar_x + 245, 4, "Fail", fontSize=6, fillColor=_black()))
    return drawing


def _stacked_service_pillar_chart(rows: list[dict[str, Any]], title: str, *, mode: str):
    from reportlab.graphics.shapes import Drawing, Line, Rect, String

    drawing = Drawing(500, 246)
    drawing.add(Rect(0, 0, 500, 246, strokeColor=_black(), fillColor=None, strokeWidth=1))
    drawing.add(String(250, 226, title, textAnchor="middle", fontName="Helvetica-Bold", fontSize=11, fillColor=_black()))
    groups = _stacked_chart_groups(rows, mode)
    max_value = max([sum(values.values()) for _name, values in groups] + [1])
    chart_x = 38
    chart_y = 42
    chart_h = 160
    bar_w = max(8, min(18, 390 / max(1, len(groups)) - 8))
    gap = max(4, (390 - len(groups) * bar_w) / max(1, len(groups)))
    for tick in range(0, int(max_value) + 1, max(1, int(max_value / 5) or 1)):
        y = chart_y + (tick / max_value) * chart_h
        drawing.add(Line(chart_x - 5, y, chart_x + 410, y, strokeColor=_color("border"), strokeWidth=0.25))
        drawing.add(String(chart_x - 22, y - 2, str(tick), fontSize=6, fillColor=_black()))
    x = chart_x + 6
    for name, values in groups:
        y = chart_y
        for key, value in values.items():
            if value <= 0:
                continue
            h = (value / max_value) * chart_h
            drawing.add(Rect(x, y, bar_w, h, strokeColor=None, fillColor=_slice_color(key)))
            drawing.add(String(x + bar_w / 2, y + h / 2 - 2, str(value), textAnchor="middle", fontSize=6, fillColor=_white()))
            y += h
        drawing.add(String(x + bar_w / 2, 15, name[:13], textAnchor="middle", fontSize=5.3, fillColor=_black(), angle=90))
        x += bar_w + gap
    legend = list(next(iter(groups))[1].keys()) if groups else []
    lx = 405
    ly = 170
    for key in legend:
        drawing.add(Rect(lx, ly, 7, 7, strokeColor=None, fillColor=_slice_color(key)))
        drawing.add(String(lx + 10, ly, key, fontSize=6, fillColor=_black()))
        ly -= 14
    return drawing


def _stacked_chart_groups(rows: list[dict[str, Any]], mode: str) -> list[tuple[str, dict[str, int]]]:
    if mode == "severity_pillar":
        result = []
        for pillar in ["Best Practices", "Governance", "Security"]:
            for outcome in ["Fail", "Pass"]:
                subset = [row for row in rows if _pillar_name(row) == pillar and ((_normalized_status(row) == "pass") == (outcome == "Pass"))]
                counts = Counter(str(row.get("severity") or "info").title() for row in subset)
                result.append((outcome, {key: counts.get(key, 0) for key in ["Critical", "High", "Medium", "Low", "Informational"]}))
        return result
    result = []
    for pillar in ["Best Practice", "Governance", "Security"]:
        canonical = "Best Practices" if pillar == "Best Practice" else pillar
        for service in SERVICE_NAMES:
            subset = [row for row in rows if _pillar_name(row) == canonical and _canonical_service(row.get("service")) == service]
            result.append((_service_short(service), {
                "Fail": len([row for row in subset if _normalized_status(row) != "pass"]),
                "Pass": len([row for row in subset if _normalized_status(row) == "pass"]),
            }))
    return result


def _license_chart_visual(rows: list[dict[str, Any]]):
    licensing = _license_counts(rows)
    return _pie_chart_box("Licenses Assigned Data", licensing, width=440, height=205)


def _license_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        text = f"{row.get('title', '')} {row.get('actual_result', '')} {row.get('finding', '')}".lower()
        if "license" not in text and "licensing" not in text and "eligible" not in text:
            continue
        for name in ["Business Basic", "Business Premium", "Unlicensed", "Exchange Online (Plan 2)", "E3", "E5"]:
            pattern = rf"{re.escape(name.lower())}[^0-9]*(\d+)"
            match = re.search(pattern, text)
            if match:
                counts[name] += int(match.group(1))
    if counts:
        return dict(counts)
    licensing_required = len([row for row in rows if _normalized_status(row) == "licensing_required"])
    if licensing_required:
        return {"Licensing Required Controls": licensing_required}
    return {"License evidence unavailable": 1}


def _user_information_chart(rows: list[dict[str, Any]]):
    from reportlab.graphics.shapes import Drawing, Rect, String

    fields = ["First Name", "Last Name", "Job Title", "Department", "Manager", "City", "Country", "Office Location"]
    total = _user_count_hint(rows)
    completeness = _user_field_counts(rows)
    drawing = Drawing(440, 210)
    drawing.add(Rect(0, 0, 440, 210, strokeColor=_black(), fillColor=None, strokeWidth=1))
    drawing.add(String(220, 190, "User Information Details", textAnchor="middle", fontName="Helvetica-Bold", fontSize=12, fillColor=_black()))
    drawing.add(Rect(190, 172, 6, 6, strokeColor=None, fillColor=_color("pass")))
    drawing.add(String(200, 172, "Added", fontSize=6, fillColor=_black()))
    drawing.add(Rect(230, 172, 6, 6, strokeColor=None, fillColor=_color("failed")))
    drawing.add(String(240, 172, "Not Added", fontSize=6, fillColor=_black()))
    chart_x = 30
    chart_y = 35
    bar_w = 19
    gap = 32
    max_h = 120
    if total is None and not completeness:
        drawing.add(String(220, 102, "User profile completeness evidence unavailable", textAnchor="middle", fontName="Helvetica-Bold", fontSize=11, fillColor=_black()))
        return drawing
    total = total or max([sum(pair) for pair in completeness.values()] or [1])
    for idx, field in enumerate(fields):
        x = chart_x + idx * (bar_w + gap)
        add, missing = completeness.get(field, (0, total))
        add_h = (add / total) * max_h if total else 0
        miss_h = (missing / total) * max_h if total else 0
        drawing.add(Rect(x, chart_y, bar_w, add_h, strokeColor=None, fillColor=_color("pass")))
        drawing.add(Rect(x, chart_y + add_h, bar_w, miss_h, strokeColor=None, fillColor=_color("failed")))
        if add:
            drawing.add(String(x + bar_w / 2, chart_y + add_h / 2 - 2, str(add), textAnchor="middle", fontSize=6, fillColor=_white()))
        if missing:
            drawing.add(String(x + bar_w / 2, chart_y + add_h + miss_h / 2 - 2, str(missing), textAnchor="middle", fontSize=6, fillColor=_white()))
        drawing.add(String(x + bar_w / 2, 12, field, textAnchor="middle", fontSize=5, fillColor=_black()))
    return drawing


def _observation_bullets(summary: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    total = int(summary.get("parameter_total") or len(rows) or 0)
    gaps = _total_gap_count(rows)
    maturity = _pillar_maturity(rows)
    eligible = _eligible_users(rows)
    active = _service_activity_summary(rows)
    return [
        f"A total of {gaps} gaps out of {total} parameters were identified, distributed across Security, Governance, and Best Practice categories.",
        "Medium to Critical severity issues make up most of the findings, indicating substantial exposure to operational and compliance risks.",
        f"Gap findings reveal that the percentage of failed parameters is Security ({_gap_percent_for_pillar(rows, 'Security')}%), Governance ({_gap_percent_for_pillar(rows, 'Governance')}%), and Best Practices ({_gap_percent_for_pillar(rows, 'Best Practices')}%) pillars, indicating a critical need for immediate remediation in those areas.",
        f"There are {eligible} user accounts that are eligible for a M365 Copilot license. Copilot requires a base Microsoft 365 subscription, such as Microsoft 365 E3, E5, Business Standard, or Business Premium.",
        _user_info_sentence(rows),
        active,
    ]


def _user_info_sentence(rows: list[dict[str, Any]]) -> str:
    completeness = _user_field_counts(rows)
    total = _user_count_hint(rows)
    if not completeness and total is None:
        return "User information completeness evidence was not available in the assessment results. Manual validation is recommended before Copilot rollout."
    complete_fields = sum(1 for added, missing in completeness.values() if missing == 0 and added > 0)
    field_total = len(completeness) or 8
    total_text = f" across {total} users" if total else ""
    return f"User profile completeness was validated for {complete_fields} of {field_total} tracked fields{total_text}; incomplete fields should be remediated to improve Copilot context quality."


def _service_activity_summary(rows: list[dict[str, Any]]) -> str:
    adoption = _service_adoption(rows)
    return _adoption_sentence(adoption)


def _total_gap_count(rows: list[dict[str, Any]]) -> int:
    return len([row for row in rows if _normalized_status(row) != "pass"])


def _readiness_from_rows(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return round(len([row for row in rows if _normalized_status(row) == "pass"]) / len(rows) * 100, 2)


def _gap_percent_for_pillar(rows: list[dict[str, Any]], pillar: str) -> float:
    subset = [row for row in rows if _pillar_name(row) == pillar]
    if not subset:
        return 0.0
    return round(len([row for row in subset if _normalized_status(row) != "pass"]) / len(subset) * 100, 2)


def _user_count_hint(rows: list[dict[str, Any]]) -> int | None:
    for row in rows:
        text = f"{row.get('title', '')} {row.get('actual_result', '')} {row.get('finding', '')}".lower()
        if "user" in text:
            numbers = [int(item) for item in re.findall(r"\b\d+\b", text)]
            if numbers:
                return max(numbers)
    return None


def _user_added_hint(rows: list[dict[str, Any]]) -> int:
    return min(3, _user_count_hint(rows) or 3)


def _user_field_counts(rows: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    fields = ["First Name", "Last Name", "Job Title", "Department", "Manager", "City", "Country", "Office Location"]
    result: dict[str, tuple[int, int]] = {}
    for row in rows:
        text = f"{row.get('title', '')} {row.get('actual_result', '')} {row.get('finding', '')}".lower()
        if "user information" not in text and "profile" not in text:
            continue
        for field in fields:
            key = field.lower()
            added = re.search(rf"{re.escape(key)}[^0-9]*(?:added|complete)?[^0-9]*(\d+)", text)
            missing = re.search(rf"{re.escape(key)}[^0-9]*(?:missing|not added|incomplete)[^0-9]*(\d+)", text)
            if added or missing:
                added_value = int(added.group(1)) if added else 0
                missing_value = int(missing.group(1)) if missing else max(0, (_user_count_hint(rows) or 0) - added_value)
                result[field] = (added_value, missing_value)
    return result


def _finding_outcome(row: dict[str, Any]) -> str:
    return "Pass" if _normalized_status(row) == "pass" else "Fail"


def _severity_label(value: Any) -> str:
    severity = str(value or "informational").strip().lower()
    if severity in {"info", "informational"}:
        return "Informational"
    if severity in {"critical", "high", "medium", "low"}:
        return severity.title()
    return "Informational"


def _callout(title: str, body: str, styles, *, color_key: str):
    from reportlab.platypus import Paragraph, Table, TableStyle

    table = Table([[Paragraph(title, styles["Heading3"])], [Paragraph(body, styles["BodyText"])]], colWidths=[520])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _color("paper")),
        ("BOX", (0, 0), (-1, -1), 0.7, _color("border")),
        ("LINEBEFORE", (0, 0), (0, -1), 5, _color(color_key)),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _two_column_lists(left_title: str, left_items: list[str], right_title: str, right_items: list[str], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    def block(title: str, items: list[str]):
        text = "<br/>".join(f"{idx}. {_escape(item)}" for idx, item in enumerate(items or ["No records available"], start=1))
        return [Paragraph(title, styles["Heading3"]), Paragraph(text, styles["BodyText"])]

    table = Table([[block(left_title, left_items), block(right_title, right_items)]], colWidths=[255, 255])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, _color("border")),
        ("BACKGROUND", (0, 0), (-1, -1), _color("paper")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _readiness_gauge(score: float):
    from reportlab.graphics.shapes import Circle, Drawing, Line, String, Wedge

    score = max(0, min(100, score))
    drawing = Drawing(170, 150)
    zones = [
        (180, 225, "critical"),
        (225, 270, "high"),
        (270, 315, "medium"),
        (315, 360, "pass"),
    ]
    for start, end, key in zones:
        drawing.add(Wedge(85, 74, 58, start, end, fillColor=_color(key), strokeColor=None))
    drawing.add(Circle(85, 74, 39, fillColor=_color("paper"), strokeColor=None))
    angle = math.radians(180 + (score / 100) * 180)
    drawing.add(Line(85, 74, 85 + math.cos(angle) * 48, 74 + math.sin(angle) * 48, strokeColor=_color("navy"), strokeWidth=2.4))
    drawing.add(Circle(85, 74, 4, fillColor=_color("navy"), strokeColor=None))
    drawing.add(String(85, 112, "Readiness Gauge", textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=_color("navy")))
    drawing.add(String(85, 52, f"{score:g}%", textAnchor="middle", fontName="Helvetica-Bold", fontSize=18, fillColor=_color("navy")))
    drawing.add(String(24, 35, "0", fontSize=7, fillColor=_color("muted")))
    drawing.add(String(143, 35, "100", fontSize=7, fillColor=_color("muted")))
    return drawing


def _donut_chart(title: str, values: dict[str, Any]):
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Circle, Drawing, String

    cleaned = {str(key): float(value or 0) for key, value in values.items() if float(value or 0) >= 0}
    if not cleaned or sum(cleaned.values()) == 0:
        cleaned = {"No data": 1}
    total = sum(cleaned.values())
    drawing = Drawing(170, 150)
    pie = Pie()
    pie.x = 34
    pie.y = 28
    pie.width = 98
    pie.height = 98
    pie.data = list(cleaned.values())
    pie.labels = ["" for _ in cleaned]
    for idx, key in enumerate(cleaned.keys()):
        pie.slices[idx].fillColor = _slice_color(key)
        pie.slices[idx].strokeWidth = 0.5
    drawing.add(pie)
    drawing.add(Circle(83, 77, 25, fillColor=_color("paper"), strokeColor=None))
    largest = max(cleaned.values())
    drawing.add(String(83, 82, f"{round((largest / total) * 100)}%", textAnchor="middle", fontName="Helvetica-Bold", fontSize=13, fillColor=_color("navy")))
    drawing.add(String(83, 67, "largest", textAnchor="middle", fontSize=6.5, fillColor=_color("muted")))
    drawing.add(String(83, 135, title, textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=_color("navy")))
    y = 15
    for key, value in list(cleaned.items())[:3]:
        drawing.add(String(18, y, f"{key}: {value:g}", fontSize=6.2, fillColor=_color("muted")))
        y -= 8
    return drawing


def _risk_heatmap(rows: list[dict[str, Any]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    severities = ["Critical", "High", "Medium", "Low"]
    table_rows = [[Paragraph("Service", styles["Small"]), *[Paragraph(sev, styles["Small"]) for sev in severities]]]
    counts: dict[str, Counter[str]] = {service: Counter() for service in SERVICE_NAMES}
    for row in rows:
        if _normalized_status(row) not in {"fail", "failed"}:
            continue
        service = _canonical_service(row.get("service"))
        severity = str(row.get("severity") or "low").title()
        counts.setdefault(service, Counter())[severity] += 1
    for service in SERVICE_NAMES:
        table_rows.append([Paragraph(service, styles["Small"]), *[str(counts.get(service, Counter()).get(sev, 0)) for sev in severities]])
    table = Table(table_rows, colWidths=[150, 95, 95, 95, 95], rowHeights=36)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _color("navy")),
        ("TEXTCOLOR", (0, 0), (-1, 0), _white()),
        ("GRID", (0, 0), (-1, -1), 0.5, _color("border")),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]
    for row_idx, service in enumerate(SERVICE_NAMES, start=1):
        for col_idx, severity in enumerate(severities, start=1):
            value = counts.get(service, Counter()).get(severity, 0)
            style.append(("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx), _heat_color(severity, value)))
            style.append(("TEXTCOLOR", (col_idx, row_idx), (col_idx, row_idx), _white() if value >= 3 else _color("navy")))
    table.setStyle(TableStyle(style))
    return table


def _maturity_bars(maturity: dict[str, float], styles):
    rows = [["Pillar", "Current Score", "Target", "Gap", "Maturity"]]
    for pillar, score in maturity.items():
        gap = max(0, 80 - score)
        rows.append([pillar, f"{score}%", "80%", f"{gap}%", _bar_text(score)])
    return _styled_table(rows, widths=[120, 80, 70, 60, 260], styles=styles)


def _service_readiness_bars(service_summary: list[dict[str, Any]], styles):
    rows = [["Service", "Readiness", "Pass", "Fail", "Score Bar"]]
    for item in service_summary:
        rows.append([item["service"], f"{item['readiness']}%", item["pass"], item["fail"], _bar_text(item["readiness"])])
    return _styled_table(rows, widths=[135, 70, 45, 45, 260], styles=styles)


def _finding_card(row: dict[str, Any], styles):
    from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

    severity = str(row.get("severity") or "info").lower()
    header = Table([[
        Paragraph(_badge(str(row.get("severity", "-")).title(), severity), styles["Small"]),
        Paragraph(_canonical_service(row.get("service")), styles["Small"]),
        Paragraph(_clean(row.get("title") or "Finding"), styles["Heading3"]),
    ]], colWidths=[75, 105, 330])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _color("paper")),
        ("GRID", (0, 0), (-1, -1), 0.25, _color("border")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    body_rows = [
        ["Why it Matters", row.get("description") or "This control was assessed for Copilot readiness."],
        ["Current State", row.get("actual_result") or row.get("finding") or "-"],
        ["Target State", row.get("expected_result") or row.get("pass_criteria") or "-"],
        ["Business Impact", _business_risk(row)],
        ["Recommendation", row.get("recommendation") or "-"],
        ["Microsoft Reference", _microsoft_reference(row)],
    ]
    body = _label_value_table(body_rows, widths=[115, 395], styles=styles)
    return KeepTogether([header, body, Spacer(1, 10)])


def _compact_list_table(rows: list[list[Any]], styles):
    table_rows = [["Parameter", "Actual Result"], *rows]
    return _styled_table(table_rows, widths=[250, 270], styles=styles)


def _license_gap_table(rows: list[dict[str, Any]], styles):
    licensing = [row for row in rows if _normalized_status(row) == "licensing_required"]
    table_rows = [["Licensing Gap", "Recommendation"]]
    if not licensing:
        table_rows.append(["No licensing-required controls", "Continue monitoring Copilot prerequisite licensing."])
    else:
        for row in licensing[:8]:
            table_rows.append([row.get("title", "-"), row.get("recommendation", "-")])
    return _styled_table(table_rows, widths=[150, 150], styles=styles)


def _recommendation_table(rows: list[dict[str, Any]], severity: str, styles):
    table_rows = [["Issue", "Recommendation", "Business Impact", "Priority"]]
    for row in rows:
        table_rows.append([row.get("title", "-"), row.get("recommendation", "-"), _business_risk(row), _priority(severity)])
    return _styled_table(table_rows, widths=[130, 180, 160, 60], styles=styles)


def _timeline(phases: list[tuple[str, str, str, int, str]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    cells = []
    for phase, focus, days, count, outcome in phases:
        cells.append([
            Paragraph(phase, styles["Heading3"]),
            Paragraph(focus, styles["BodyText"]),
            Paragraph(days, styles["Small"]),
            Paragraph(f"{count} control(s)", styles["Small"]),
            Paragraph(outcome, styles["Small"]),
        ])
    table = Table([cells], colWidths=[130, 130, 130, 130])
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, _color("border")),
        ("BACKGROUND", (0, 0), (-1, -1), _color("paper")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]
    for col, phase in enumerate(phases):
        style.append(("LINEABOVE", (col, 0), (col, 0), 5, _slice_color(phase[1])))
    table.setStyle(TableStyle(style))
    return table


def _parameter_matrix(rows: list[dict[str, Any]], styles):
    from reportlab.platypus import LongTable, Paragraph, TableStyle

    table_rows = [["#", "Parameter", "Service", "Status", "Severity", "Actual Result", "Expected Result", "Recommendation"]]
    for index, row in enumerate(rows, start=1):
        table_rows.append([
            str(index),
            Paragraph(_clean(row.get("title")), styles["Fine"]),
            Paragraph(_canonical_service(row.get("service")), styles["Fine"]),
            Paragraph(_status_label(row), styles["Fine"]),
            Paragraph(str(row.get("severity", "-")).title(), styles["Fine"]),
            Paragraph(_clean(row.get("actual_result") or row.get("finding") or "-"), styles["Fine"]),
            Paragraph(_clean(row.get("expected_result") or row.get("pass_criteria") or "-"), styles["Fine"]),
            Paragraph(_clean(row.get("recommendation") or "-"), styles["Fine"]),
        ])
    table = LongTable(table_rows, repeatRows=1, colWidths=[24, 125, 72, 68, 50, 145, 145, 170])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _color("navy")),
        ("TEXTCOLOR", (0, 0), (-1, 0), _white()),
        ("GRID", (0, 0), (-1, -1), 0.25, _color("border")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _label_value_table(rows: list[list[Any]], *, widths: list[int], styles=None):
    from reportlab.platypus import Paragraph, Table, TableStyle

    if styles:
        rendered = [[Paragraph(_clean(left), styles["Small"]), Paragraph(_clean(right), styles["Small"])] for left, right in rows]
    else:
        rendered = rows
    table = Table(rendered, colWidths=widths)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, _color("border")),
        ("BACKGROUND", (0, 0), (0, -1), _color("light_blue")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _styled_table(rows: list[list[Any]], *, widths: list[int], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    rendered = []
    for row_index, row in enumerate(rows):
        rendered.append([
            Paragraph(_clean(value), styles["Small"] if row_index else styles["CardLabel"])
            for value in row
        ])
    table = Table(rendered, repeatRows=1, colWidths=widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _color("navy")),
        ("TEXTCOLOR", (0, 0), (-1, 0), _white()),
        ("GRID", (0, 0), (-1, -1), 0.35, _color("border")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _business_risk(row: dict[str, Any]) -> str:
    status = _normalized_status(row)
    if status == "licensing_required":
        return "Copilot eligibility or required Microsoft 365 service capability cannot be confirmed until licensing is remediated."
    if status == "manual_validation_required":
        return "This control requires administrative confirmation before readiness can be certified."
    if status in {"not_collected", "failed"}:
        return "Evidence was unavailable, preventing a readiness conclusion for this control."
    if str(row.get("severity", "")).lower() in {"critical", "high"}:
        return "This issue may materially increase data exposure, governance, or deployment risk for Microsoft 365 Copilot."
    return "This issue should be reviewed as part of readiness improvement planning."


def _conclusion(summary: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    customer = _customer_label(summary)
    score = summary.get("overall_readiness", 0)
    total = int(summary.get("parameter_total") or len(rows) or 0)
    gaps = _total_gap_count(rows)
    level = _readiness_level(summary, rows)
    risk_counts = _risk_counts(rows)
    critical_high = risk_counts.get("Critical", 0) + risk_counts.get("High", 0)
    themes = _conclusion_gap_themes(rows)
    deployment = summary.get("deployment_recommendation") or "Postpone broad production deployment until critical and high-priority gaps are remediated and the assessment is re-run."
    posture = {
        "Ready": "is prepared for a controlled Microsoft 365 Copilot deployment, subject to continued governance and monitoring",
        "Partially Ready": "is partially prepared for Microsoft 365 Copilot deployment, with remediation required before broad production rollout",
        "Not Ready": "is not yet prepared for secure and compliant deployment of Microsoft 365 Copilot",
    }.get(level, "requires further validation before Microsoft 365 Copilot deployment")
    return [
        (
            f"The Copilot Readiness Assessment for {customer} reveals that the current Microsoft 365 environment {posture}. "
            f"With a readiness score of {score}%, {gaps} out of {total} parameters require remediation or validation, "
            f"including {critical_high} critical or high-risk findings."
        ),
        (
            f"Key gaps were identified across the foundational pillars of Security, Governance, and Best Practices. {themes} "
            "These gaps may affect identity protection, collaboration governance, information protection, auditability, and "
            "the quality of content available to Copilot."
        ),
        (
            f"To mitigate these risks and support a successful Copilot rollout, {customer} should follow a phased remediation "
            "strategy. Critical and high-severity issues should be addressed first, followed by medium and low-risk items. "
            f"{deployment}"
        ),
        (
            f"By aligning with the recommendations outlined in this report, {customer} can enhance its security posture, improve "
            "regulatory readiness, and more safely leverage the transformative potential of Microsoft 365 Copilot."
        ),
    ]


def _conclusion_gap_themes(rows: list[dict[str, Any]]) -> str:
    gap_rows = [row for row in rows if _normalized_status(row) != "pass"]
    if not gap_rows:
        return "No material control gaps were identified in the assessed parameters."

    theme_matchers = [
        ("identity and administrative access controls", ("mfa", "authentication", "conditional access", "administrator", "admin", "guest invite")),
        ("external sharing and guest access governance", ("sharing", "guest", "external", "anyone link", "invitation")),
        ("sensitivity labels, DLP, and information protection", ("sensitivity", "label", "dlp", "information protection", "compliance")),
        ("audit, retention, and monitoring controls", ("audit", "retention", "recording", "logs")),
        ("user profile completeness and lifecycle governance", ("user information", "profile", "inactive", "owner", "enabled account")),
    ]
    found: list[str] = []
    for label, needles in theme_matchers:
        if any(any(needle in str(row.get("title", "")).lower() for needle in needles) for row in gap_rows):
            found.append(label)
    if not found:
        found = [_clean(row.get("title") or "assessed control") for row in gap_rows[:3]]

    if len(found) == 1:
        theme_text = found[0]
    else:
        theme_text = ", ".join(found[:-1]) + f", and {found[-1]}"
    return f"Notable remediation themes include {theme_text}."


def _service_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    service_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        service_rows[_canonical_service(row.get("service"))].append(row)
    result = []
    for service in SERVICE_NAMES:
        items = service_rows.get(service, [])
        if not items:
            result.append({"service": service, "pass": 0, "fail": 0, "risk": "Not assessed", "readiness": 0})
            continue
        passed = len([row for row in items if _normalized_status(row) == "pass"])
        failed = len([row for row in items if _normalized_status(row) in {"fail", "failed"}])
        readiness = round(passed / len(items) * 100, 2)
        result.append({"service": service, "pass": passed, "fail": failed, "risk": _risk_rating(readiness), "readiness": readiness})
    return result


def _executive_summary(summary: dict[str, Any], narrative: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    services = ", ".join(sorted({_canonical_service(row.get("service")) for row in rows if row.get("service")})) or "Microsoft 365 services"
    top_risks = _top_items(rows, passing=False)
    top_text = "No critical or high-risk failed controls were identified." if not top_risks else "Top risks include " + ", ".join(top_risks[:5]) + "."
    return [
        (
            f"This assessment evaluated {summary.get('parameter_total', len(rows))} Copilot readiness controls across "
            f"{services}. The current readiness score is {summary.get('overall_readiness', 0)}%, with "
            f"{summary.get('collected_total', 0)} controls supported by collected evidence."
        ),
        (
            "The business impact of the current posture is concentrated in identity governance, collaboration exposure, "
            f"information protection, and operational readiness. {top_text}"
        ),
        (
            f"Executive recommendation: {summary.get('deployment_recommendation') or narrative.get('conclusion') or 'Prioritize remediation and reassess before broad Copilot deployment.'}"
        ),
    ]


def _top_items(rows: list[dict[str, Any]], *, passing: bool) -> list[str]:
    if passing:
        return [_clean(row.get("title")) for row in rows if _normalized_status(row) == "pass"][:5]
    failed = [row for row in rows if _normalized_status(row) in {"fail", "failed"}]
    failed.sort(key=lambda row: SEVERITY_RANK.get(str(row.get("severity", "info")).lower(), 1), reverse=True)
    return [_clean(row.get("title")) for row in failed[:5]]


def _readiness_level(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    critical = _risk_counts(rows).get("Critical", 0)
    fail_pct = _fail_percent(rows)
    if critical == 0 and fail_pct <= 10:
        return "Ready"
    if critical <= 3 and fail_pct <= 35:
        return "Partially Ready"
    return "Not Ready"


def _readiness_color(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    level = _readiness_level(summary, rows)
    return "pass" if level == "Ready" else "high" if level == "Partially Ready" else "critical"


def _risk_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for row in rows:
        if _normalized_status(row) not in {"fail", "failed"}:
            continue
        severity = str(row.get("severity") or "low").lower().title()
        if severity in counts:
            counts[severity] += 1
    return counts


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(_status_label(row) for row in rows)
    return dict(counts)


def _pillar_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(_pillar_name(row) for row in rows)
    return dict(counts)


def _pillar_maturity(rows: list[dict[str, Any]]) -> dict[str, float]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_pillar_name(row)].append(row)
    default = {"Security": 0.0, "Governance": 0.0, "Best Practices": 0.0}
    for pillar, items in groups.items():
        passed = len([row for row in items if _normalized_status(row) == "pass"])
        default[pillar] = round(passed / len(items) * 100, 2) if items else 0.0
    return default


def _pillar_readiness(rows: list[dict[str, Any]]) -> dict[str, float]:
    return _pillar_maturity(rows)


def _licensing_status(rows: list[dict[str, Any]]) -> dict[str, int]:
    licensing = [row for row in rows if "license" in str(row.get("title", "")).lower() or _normalized_status(row) == "licensing_required"]
    if not licensing:
        return {"No Licensing Gap": 1}
    return dict(Counter(_status_label(row) for row in licensing))


def _eligible_users(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        text = f"{row.get('title', '')} {row.get('actual_result', '')} {row.get('finding', '')}".lower()
        if "eligible" in text and "user" in text:
            match = re.search(r"\b\d+\b", text)
            if match:
                return match.group(0)
    return "Evidence based"


def _short_recommendation(summary: dict[str, Any]) -> str:
    text = str(summary.get("deployment_recommendation") or "Remediate and reassess")
    if len(text) <= 28:
        return text
    return text[:25].rstrip() + "..."


def _coverage_percent(summary: dict[str, Any]) -> str:
    total = float(summary.get("parameter_total") or 0)
    collected = float(summary.get("collected_total") or 0)
    return f"{round(collected / total * 100, 2) if total else 0}%"


def _fail_percent(rows: list[dict[str, Any]]) -> float:
    assessed = [row for row in rows if _normalized_status(row) in {"pass", "warning", "fail", "failed"}]
    if not assessed:
        return 0.0
    failed = len([row for row in assessed if _normalized_status(row) in {"fail", "failed"}])
    return round(failed / len(assessed) * 100, 2)


def _risk_rating(readiness: float) -> str:
    if readiness >= 80:
        return "Low"
    if readiness >= 60:
        return "Medium"
    if readiness >= 40:
        return "High"
    return "Critical"


def _priority(severity: str) -> str:
    return {"critical": "Immediate", "high": "High", "medium": "Medium", "low": "Low"}.get(severity, "Medium")


def _normalized_status(row: dict[str, Any]) -> str:
    return str(row.get("status") or "not_collected").lower()


def _status_label(row: dict[str, Any]) -> str:
    return _normalized_status(row).replace("_", " ").title()


def _canonical_service(value: Any) -> str:
    text = str(value or "").lower()
    if "entra" in text or "identity" in text:
        return "Entra ID"
    if "exchange" in text:
        return "Exchange Online"
    if "team" in text:
        return "Microsoft Teams"
    if "sharepoint" in text:
        return "SharePoint Online"
    if "onedrive" in text:
        return "OneDrive"
    if "purview" in text or "compliance" in text:
        return "Microsoft Purview"
    return str(value or "Microsoft 365")


def _pillar_name(row: dict[str, Any]) -> str:
    text = f"{row.get('pillar', '')} {row.get('category', '')} {row.get('title', '')}".lower()
    if any(token in text for token in ["security", "identity", "mfa", "conditional", "admin", "risk"]):
        return "Security"
    if any(token in text for token in ["governance", "sharing", "guest", "lifecycle", "external"]):
        return "Governance"
    return "Best Practices"


def _microsoft_reference(row: dict[str, Any]) -> str:
    existing = row.get("documentation_link")
    if existing and str(existing).startswith("https://learn.microsoft.com"):
        return str(existing)
    text = f"{row.get('parameter_key', '')} {row.get('title', '')} {row.get('service', '')}".lower()
    references = [
        (["mfa", "multi-factor", "authentication"], "https://learn.microsoft.com/entra/identity/authentication/"),
        (["conditional access"], "https://learn.microsoft.com/entra/identity/conditional-access/"),
        (["privileged", "admin", "global administrator"], "https://learn.microsoft.com/entra/identity/role-based-access-control/privileged-roles-permissions"),
        (["guest", "external identity"], "https://learn.microsoft.com/entra/external-id/"),
        (["sensitivity", "label"], "https://learn.microsoft.com/purview/sensitivity-labels"),
        (["audit"], "https://learn.microsoft.com/purview/audit-search"),
        (["retention"], "https://learn.microsoft.com/purview/retention"),
        (["dlp", "data loss"], "https://learn.microsoft.com/purview/dlp-learn-about-dlp"),
        (["lockbox"], "https://learn.microsoft.com/purview/customer-lockbox"),
        (["exchange", "owa", "mailbox"], "https://learn.microsoft.com/exchange/exchange-online"),
        (["sharing", "sharepoint"], "https://learn.microsoft.com/sharepoint/turn-external-sharing-on-or-off"),
        (["onedrive"], "https://learn.microsoft.com/sharepoint/onedrive-overview"),
        (["teams"], "https://learn.microsoft.com/microsoftteams/teams-overview"),
        (["copilot", "license"], "https://learn.microsoft.com/copilot/microsoft-365/microsoft-365-copilot-licensing"),
    ]
    for tokens, url in references:
        if any(token in text for token in tokens):
            return url
    return "https://learn.microsoft.com/copilot/microsoft-365/"


def _customer_label(summary: dict[str, Any]) -> str:
    value = str(summary.get("customer_name") or summary.get("tenant_name") or "").strip()
    if not value or _looks_like_guid(value):
        return "Assessment Tenant"
    return value


def _tenant_label(summary: dict[str, Any], fallback: str) -> str:
    value = str(summary.get("tenant_name") or "").strip()
    if not value or value.lower() in {"unknown", "n/a", "none"} or _looks_like_guid(value):
        return fallback or "Assessment Tenant"
    return value


def _looks_like_guid(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value))


def _info_count(rows: list[dict[str, Any]]) -> int:
    return len([row for row in rows if str(row.get("severity") or "").lower() in {"info", "informational"}])


def _icon_label(label: str) -> str:
    return {"Security": "SEC", "Governance": "GOV", "Best Practices": "BP"}.get(label, label[:3].upper())


def _service_short(service: str) -> str:
    return {
        "Entra ID": "ID",
        "Exchange Online": "EX",
        "Microsoft Teams": "TM",
        "SharePoint Online": "SP",
        "OneDrive": "OD",
        "Microsoft Purview": "PV",
    }.get(service, service[:2].upper())


def _consulting_observations(summary: dict[str, Any], rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    maturity = _pillar_maturity(rows)
    risks = _risk_counts(rows)
    observations = [
        (
            "Identity governance controls require executive attention.",
            "Critical or high identity-related gaps can increase the likelihood that Copilot exposes information through compromised or over-privileged accounts.",
            "critical" if risks.get("Critical", 0) else "high",
        ),
        (
            "Information protection maturity should be improved before broad deployment.",
            "Sensitivity labels, retention, audit, and DLP controls form the compliance foundation for trustworthy Copilot adoption.",
            "high",
        ),
        (
            "Governance readiness is uneven across collaboration workloads.",
            f"The Governance pillar is currently assessed at {maturity.get('Governance', 0)}%, indicating remediation is required before unrestricted rollout.",
            "high" if maturity.get("Governance", 0) < 80 else "pass",
        ),
        (
            "Copilot deployment should follow a staged readiness model.",
            f"The environment is currently assessed as {_readiness_level(summary, rows)}. A controlled pilot is recommended until critical and high risks are resolved.",
            _readiness_color(summary, rows),
        ),
    ]
    if summary.get("licensing_required_total", 0):
        observations.append((
            "Licensing validation remains a deployment dependency.",
            "Copilot eligibility cannot be fully certified until licensing-dependent controls are validated and required subscriptions are confirmed.",
            "licensing_required",
        ))
    return observations


def _icon_callout_grid(items: list[tuple[str, str, str]], styles):
    from reportlab.platypus import Paragraph, Table, TableStyle

    cells = []
    for title, body, color_key in items:
        cells.append([
            Paragraph(_service_short(title), styles["CardValue"]),
            Paragraph(title, styles["Heading3"]),
            Paragraph(body, styles["Small"]),
        ])
    rows = [cells[:2], cells[2:4], cells[4:]]
    for row in rows:
        while len(row) < 2:
            row.append("")
    table = Table(rows, colWidths=[255, 255], rowHeights=[115, 115, 115])
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, _color("border")),
        ("BACKGROUND", (0, 0), (-1, -1), _color("paper")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]
    index = 0
    for row_idx in range(3):
        for col_idx in range(2):
            if index < len(items):
                style.append(("LINEABOVE", (col_idx, row_idx), (col_idx, row_idx), 4, _color(items[index][2])))
            index += 1
    table.setStyle(TableStyle(style))
    return table


def _service_overview_text(service: str, readiness: float) -> str:
    posture = "strong" if readiness >= 80 else "developing" if readiness >= 50 else "immature"
    return (
        f"{service} readiness is assessed as {posture} at {readiness}%. This service section summarizes the control posture, "
        "risk concentration, and remediation themes that influence Microsoft 365 Copilot deployment readiness."
    )


def _executive_result(row: dict[str, Any]) -> str:
    status = _normalized_status(row)
    raw = str(row.get("actual_result") or row.get("finding") or "").strip()
    if _contains_technical_noise(raw):
        if status == "failed":
            return "Assessment data could not be validated due to insufficient permissions or service connectivity. Manual review is recommended."
        return "Assessment evidence requires administrative validation before a readiness conclusion can be certified."
    if not raw or raw.lower() in {"not collected", "not_collected", "none", "n/a", "unknown"}:
        if status == "not_collected":
            return "Assessment evidence was not available for this control. Manual review is recommended."
        return "No executive-readable result was recorded for this control."
    return raw


def _evidence_summary(row: dict[str, Any]) -> str:
    status = _normalized_status(row)
    if status == "pass":
        return "Assessment evidence indicates the control is aligned with the expected readiness baseline."
    if status == "licensing_required":
        return "Evidence validation depends on Microsoft 365 licensing or service entitlement confirmation."
    if status == "manual_validation_required":
        return "Evidence should be confirmed by an administrator because automated validation is not sufficient for this control."
    if status in {"failed", "not_collected"}:
        return "Assessment evidence was unavailable or incomplete. The control should be reviewed manually before Copilot rollout."
    return _executive_result(row)


def _copilot_impact(row: dict[str, Any]) -> str:
    text = f"{row.get('title', '')} {row.get('service', '')} {row.get('pillar', '')}".lower()
    if any(token in text for token in ["mfa", "conditional", "admin", "identity", "guest"]):
        return "Weak identity controls can allow unauthorized users or over-privileged accounts to access information surfaced by Copilot."
    if any(token in text for token in ["label", "dlp", "retention", "audit", "purview", "lockbox"]):
        return "Compliance and information protection gaps may reduce confidence that Copilot interactions respect regulatory and data governance expectations."
    if any(token in text for token in ["sharing", "sharepoint", "onedrive", "external"]):
        return "Collaboration and sharing gaps can increase the likelihood that Copilot surfaces content to unintended audiences."
    if "teams" in text:
        return "Teams governance gaps can affect meeting, chat, guest, and app data that Copilot may summarize or reason over."
    return "This control affects the overall trust, governance, and operational readiness baseline required for responsible Copilot adoption."


def _remediation_guidance(row: dict[str, Any]) -> str:
    recommendation = str(row.get("recommendation") or "").strip()
    if recommendation and not _contains_technical_noise(recommendation):
        return recommendation
    status = _normalized_status(row)
    if status == "licensing_required":
        return "Validate Microsoft 365 licensing prerequisites, confirm eligible users, and reassess this control after licensing gaps are remediated."
    if status == "manual_validation_required":
        return "Assign an administrator to validate the control configuration, document the outcome, and update the readiness baseline."
    return "Review the Microsoft-recommended configuration, remediate the control gap, and rerun the assessment to confirm readiness."


def _contains_technical_noise(value: str) -> bool:
    text = value.lower()
    return any(token in text for token in [
        "collector execution failed",
        "graph api",
        "raw json",
        "stack trace",
        "traceback",
        "exception",
        "aadsts",
        "powershell",
        "connect-",
        "get-",
        "{",
        "}",
    ])


def _bar_text(score: float) -> str:
    score = max(0, min(100, float(score or 0)))
    filled = int(round(score / 5))
    return "[" + "#" * filled + "." * (20 - filled) + f"] {score:g}%"


def _badge(text: str, color_key: str) -> str:
    return f'<font color="{PALETTE.get(color_key, PALETTE["muted"])}"><b>{_escape(text)}</b></font>'


def _clean(value: Any) -> str:
    return _escape(" ".join(str(value if value is not None else "-").split())[:1200])


def _escape(value: Any) -> str:
    text = str(value if value is not None else "-")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _color(key: str):
    from reportlab.lib import colors

    return colors.HexColor(PALETTE.get(key, PALETTE["muted"]))


def _white():
    from reportlab.lib import colors

    return colors.white


def _black():
    from reportlab.lib import colors

    return colors.black


def _very_light(color_key: str):
    from reportlab.lib import colors

    mapping = {
        "critical": "#fde2e2",
        "failed": "#fee2e2",
        "high": "#ffedd5",
        "medium": "#fef9c3",
        "low": "#dbeafe",
        "pass": "#ecfdf5",
    }
    return colors.HexColor(mapping.get(color_key, "#f8fafc"))


def _slice_color(key: str):
    key_lower = str(key).lower().replace(" ", "_")
    if "critical" in key_lower:
        return _color("critical")
    if "high" in key_lower:
        return _color("high")
    if "medium" in key_lower:
        return _color("medium")
    if "low" in key_lower:
        return _color("low")
    if "pass" in key_lower or "ready" in key_lower:
        return _color("pass")
    if "license" in key_lower:
        return _color("licensing_required")
    if "manual" in key_lower:
        return _color("manual_validation_required")
    if "not" in key_lower:
        return _color("not_collected")
    if "fail" in key_lower:
        return _color("failed")
    if "security" in key_lower:
        return _color("critical")
    if "governance" in key_lower:
        return _color("high")
    if "best" in key_lower:
        return _color("blue")
    return _color("blue")


def _heat_color(severity: str, value: int):
    if value <= 0:
        return _color("paper")
    key = severity.lower()
    if value == 1:
        return _color("medium" if key == "critical" else "light_blue")
    return _color(key if key in PALETTE else "low")


def _licensing_table(rows: list[dict[str, Any]]):
    licensing = [row for row in rows if "license" in str(row.get("title", "")).lower() or _normalized_status(row) == "licensing_required"]
    missing = len([row for row in licensing if _normalized_status(row) == "licensing_required"])
    return [
        ["Metric", "Value"],
        ["Eligible Users", "Derived from assessment evidence where available"],
        ["Required Licenses", "Microsoft 365 Copilot and prerequisite Microsoft 365 service plans"],
        ["Missing Licenses", missing],
        ["Copilot Eligibility", "Eligible" if missing == 0 else "Licensing remediation required"],
    ]
