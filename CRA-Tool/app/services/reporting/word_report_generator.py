from __future__ import annotations

import re
import struct
import zipfile
import zlib
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.assessment import Assessment
from app.db.models.tenant import ConnectedTenant
from app.db.models.user import User


# XML 1.0 illegal control characters (everything except \x09, \x0A, \x0D, \x20+)
_XML_ILLEGAL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def _sanitize(text: Any) -> str:
    """Strip XML-illegal characters so python-docx never writes corrupt XML."""
    if text is None:
        return ""
    s = str(text)
    s = _XML_ILLEGAL.sub("", s)
    # Remove Unicode surrogates that survive str() conversion
    s = s.encode("utf-8", errors="ignore").decode("utf-8")
    return s


def _validate_docx(path: Path) -> None:
    """Raise ValueError if the DOCX is a bad ZIP or contains invalid XML."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for required in ("word/document.xml", "[Content_Types].xml", "_rels/.rels"):
                if required not in names:
                    raise ValueError(f"DOCX missing required part: {required}")
            for name in names:
                if not (name.endswith(".xml") or name.endswith(".rels")):
                    continue
                with z.open(name) as f:
                    data = f.read()
                try:
                    ET.fromstring(data)
                except ET.ParseError as exc:
                    raise ValueError(f"Corrupt XML in {name}: {exc}") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Generated DOCX is not a valid ZIP archive: {exc}") from exc


REFERENCE_TEMPLATE_CANDIDATES = [
    Path("out/sample.docx"),
    Path("app/services/reporting/templates/AAA Legal Process Copilot Readiness Assessment Report.docx"),
    Path(r"C:\Users\Admin\Downloads\AAA Legal Process Copilot Readiness Assessment Report (1).docx"),
    Path(r"C:\Users\Admin\Downloads\AAA Legal Process Copilot Readiness Assessment Report.docx"),
]

STATUS_LABELS = {
    "pass": "PASS",
    "fail": "FAIL",
    "warning": "WARNING",
    "collection_error": "COLLECTION ERROR",
    "failed": "COLLECTION ERROR",
    "failed_collector": "COLLECTION ERROR",
    "licensing_required": "LICENSING REQUIRED",
    "licensing_limitation": "LICENSING REQUIRED",
    "manual_validation_required": "MANUAL VALIDATION",
    "manual_validation": "MANUAL VALIDATION",
    "not_collected": "NOT COLLECTED",
}

SERVICE_ORDER = [
    "Entra ID",
    "Exchange Online",
    "Microsoft Purview",
    "Microsoft Teams",
    "OneDrive for Business",
    "SharePoint Online",
]

TEMPLATE_SERVICE_OVERRIDES = {
    "teams_channel_email_addresses": "Microsoft Teams",
    "getting_all_sites_with_sensitivity_keywords_on_a_tenant": "SharePoint Online",
    "sharepoint_and_onedrive_guest_access_expiry": "SharePoint Online",
    "customer_lockbox": "Entra ID",
}


def render_word_report(
    path: Path,
    report: dict[str, Any],
    *,
    template_path: Path | str | None = None,
) -> Path:
    """Render a template-aligned CRA DOCX from runtime assessment data."""
    try:
        from docx import Document
        from docx.enum.text import WD_BREAK
        from docx.shared import Inches
    except ModuleNotFoundError as exc:
        raise RuntimeError("python-docx is required for CRA Word reports.") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    template = _resolve_template_path(template_path)
    doc = Document(str(template)) if template else Document()

    assessment = report["assessment"]
    summary = report.get("summary") or {}
    rows = report.get("parameter_rows") or []
    tenant_name = _tenant_name(summary, assessment)
    tenant_id = str(getattr(assessment, "tenant_id", "") or summary.get("tenant_id") or "")
    assessment_date = _assessment_date(summary, assessment)
    summary = _summary_for_rows(summary, rows)
    readiness_score = float(summary.get("overall_readiness") or 0)
    readiness_level = _readiness_level(readiness_score)

    _replace_template_placeholders(
        doc,
        {
            # sample.docx placeholders - must come before substring variants
            "XYZ.": f"{tenant_name}.",
            "XYZ ": f"{tenant_name} ",
            "XYZ": tenant_name,
            "xyz": tenant_name,
            "April 20, 2026": assessment_date,
            "April 20, 202": assessment_date,
            # Legacy AAA-template placeholders
            "Customer Name": f"{tenant_name}\nTenant ID: {tenant_id}",
            "DD-MM-YYYY": assessment_date,
            "__________": tenant_name,
            "________": tenant_name,
            "_______": tenant_name,
            "_____.": f"{tenant_name}.",
            "_____": tenant_name,
        },
    )
    _update_template_summary(doc, rows, tenant_name, summary, readiness_score, readiness_level)
    template_order = _template_parameter_order(doc)
    _update_service_tables(doc, rows, template_order)
    _update_detailed_blocks(doc, rows, template_order)
    _update_template_conclusion(doc, rows, tenant_name, summary, readiness_score, readiness_level)

    _enable_field_update(doc)
    doc.save(path)
    _validate_docx(path)
    return path


async def generate_latest_completed_word_report(
    db: AsyncSession,
    *,
    current_user: User,
    tenant_id: str | None = None,
    output_root: Path | None = None,
    template_path: Path | str | None = None,
) -> Path:
    """Generate the requested tenant-specific DOCX for the latest completed assessment."""
    from app.services.reporting.cra_report_service import build_report_data

    target_tenant = tenant_id or current_user.microsoft_tid
    if current_user.microsoft_tid != target_tenant:
        raise PermissionError("Tenant is not available to the current user")
    result = await db.execute(
        select(Assessment)
        .where(Assessment.tenant_id == target_tenant, Assessment.status == "completed")
        .order_by(Assessment.created_at.desc())
        .limit(1)
    )
    assessment = result.scalars().first()
    if assessment is None:
        raise FileNotFoundError("No completed assessment exists for this tenant")

    report_data = await build_report_data(db, current_user=current_user, assessment_id=assessment.id)
    tenant_name = _tenant_name(report_data.get("summary") or {}, assessment)
    safe_name = _safe_filename(tenant_name)
    root = output_root or Path("storage/reports") / str(assessment.id)
    return render_word_report(
        root / f"Copilot_Readiness_Assessment_{safe_name}.docx",
        report_data,
        template_path=template_path,
    )


async def tenant_display_name(db: AsyncSession, tenant_id: str) -> str:
    result = await db.execute(select(ConnectedTenant).where(ConnectedTenant.tenant_id == tenant_id))
    tenant = result.scalars().first()
    return tenant.tenant_name if tenant and tenant.tenant_name else tenant_id


def _resolve_template_path(template_path: Path | str | None) -> Path | None:
    configured = getattr(settings, "cra_word_template_path", None)
    candidates = [Path(template_path)] if template_path else []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(REFERENCE_TEMPLATE_CANDIDATES)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _replace_template_placeholders(doc, replacements: dict[str, str]) -> None:
    # Sanitize all replacement values upfront
    safe_replacements = {old: _sanitize(new) for old, new in replacements.items()}

    def _apply_to_para(para) -> None:
        # Fast path: none of the old values appear in this paragraph at all
        full_text = para.text
        if not any(old in full_text for old in safe_replacements):
            return
        # Per-node replacement (handles simple cases where placeholder is in one run)
        for node in para._p.xpath(".//w:t"):
            if not node.text:
                continue
            value = node.text
            for old, new in safe_replacements.items():
                value = value.replace(old, new)
            node.text = value

    for para in doc.paragraphs:
        _apply_to_para(para)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _apply_to_para(para)


def _remove_from_heading(doc, heading_text: str) -> None:
    body = doc._body._element
    start = None
    children = list(body)
    for index, child in enumerate(children):
        if _element_text(child).strip() == heading_text:
            start = index
            break
    if start is None:
        return
    for child in children[start:]:
        if child.tag.endswith("}sectPr"):
            continue
        body.remove(child)


def _clone_block(doc, start_heading: str, end_heading: str) -> list[Any]:
    body = doc._body._element
    children = list(body)
    start = None
    end = None
    for index, child in enumerate(children):
        text = _element_text(child).strip()
        if start is None and text == start_heading:
            start = index
        elif start is not None and text == end_heading:
            end = index
            break
    if start is None:
        return []
    return [deepcopy(child) for child in children[start : end or len(children)]]


def _append_cloned_block(doc, elements: list[Any]) -> None:
    body = doc._body._element
    for element in elements:
        body.append(deepcopy(element))


def _element_text(element: Any) -> str:
    return "".join(node.text or "" for node in element.xpath(".//w:t"))


def _heading(doc, text: str, *, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def _update_template_summary(
    doc,
    rows: list[dict[str, Any]],
    tenant_name: str,
    summary: dict[str, Any],
    readiness_score: float,
    readiness_level: str,
) -> None:
    failed = summary["fail"] + summary["collection_error"]
    observations = _key_observations(rows, tenant_name, readiness_score, readiness_level)
    # Exact-match replacements (normalized whitespace)
    replacements = {
        # AAA template variants
        "The Copilot Readiness Assessment uncovered several configuration gaps and policy deficiencies that could impact the secure and compliant adoption of Microsoft Copilot. Each finding has been categorized by severity and mapped to specific areas of risk within the": (
            f"The Copilot Readiness Assessment for {tenant_name} evaluated {summary['total']} approved parameters. "
            f"The assessment identified {failed} gaps that could affect secure and compliant Microsoft 365 Copilot adoption."
        ),
        "Based on the findings, the Client's current readiness level for Copilot integration is assessed as:": (
            f"Based on the runtime findings, {tenant_name}'s current readiness level for Copilot integration is assessed as:"
        ),
        # sample.docx variant
        f"Based on the findings, the Client's current readiness level for Copilot integration is assessed as:": (
            f"Based on the runtime findings, {tenant_name}'s current readiness level for Copilot integration is assessed as:"
        ),
        "Readiness Level: Not Ready": f"Readiness Level: {readiness_level}",
        "Readiness Level: Ready/Not Ready": f"Readiness Level: {readiness_level}",
        "Readiness Gaps: out of 65": f"Readiness Gaps: {failed} out of {summary['total']}",
        "Significant remediation is required prior to enabling Copilot in the production environment.": (
            _deployment_sentence(readiness_level)
        ),
        "A total of gaps out of 65 parameters were identified, distributed across Security, Governance, and Best Practice categories.": observations[0],
        "Medium to Critical severity issues make up most of the findings, indicating substantial exposure to operational and compliance risks.": observations[1] if len(observations) > 1 else "",
        # AAA-template: "failed" wording
        "Gap findings reveal that the percentage of failed parameters is Security (%), Governance (%), and Best Practices (%) pillars, indicating a critical need for immediate remediation in those areas.": observations[2] if len(observations) > 2 else "",
        "There are user accounts out of that are eligible for a M365 Copilot license. Copilot requires a base Microsoft 365 subscription, such as Microsoft 365 E3, E5, Business Standard, or Business Premium.": (
            f"{summary['licensing_required']} parameters require licensing validation. Copilot requires the appropriate Microsoft 365 base subscription and Copilot entitlement."
        ),
    }
    # Prefix-match replacements - for sample.docx paragraphs that embed dynamic values
    # (e.g., "ABed" instead of "failed", or specific percentage values baked in)
    prefix_replacements = {
        "Gap findings reveal that the percentage of": observations[2] if len(observations) > 2 else "",
        "There are 4 user accounts out of": (
            f"{summary['licensing_required']} parameters require licensing validation. Copilot requires the appropriate Microsoft 365 base subscription and Copilot entitlement."
        ),
        "There are user accounts out of": (
            f"{summary['licensing_required']} parameters require licensing validation. Copilot requires the appropriate Microsoft 365 base subscription and Copilot entitlement."
        ),
        "Overall Readiness:": f"Overall Readiness: {readiness_score:.1f}% - {readiness_level}",
    }
    for para in doc.paragraphs:
        text = " ".join(para.text.split())
        if text in replacements:
            _set_paragraph_text(para, replacements[text])
            continue
        for prefix, new_text in prefix_replacements.items():
            if text.startswith(prefix) and new_text:
                _set_paragraph_text(para, new_text)
                break


def _update_service_tables(doc, rows: list[dict[str, Any]], template_order: dict[str, list[str]]) -> None:
    grouped = _ordered_rows_by_service(rows, template_order)
    for table, service in zip(doc.tables[:6], SERVICE_ORDER):
        service_rows = grouped.get(service, [])
        template_names = template_order.get(service, [])
        _resize_table(table, len(service_rows) + 1)
        headers = ["S. No", "Parameter", "CRA Pillar", "Finding", "Severity"]
        for idx, header in enumerate(headers):
            _write_cell(table.rows[0], idx, header)
        for index, row in enumerate(service_rows, start=1):
            tbl_row = table.rows[index]
            sl = _status_label(row)
            param_name = (
                template_names[index - 1]
                if index - 1 < len(template_names)
                else str(row.get("title") or row.get("parameter_key") or "-")
            )
            sev_key = str(row.get("severity") or "info").lower()
            _write_cell(tbl_row, 0, f"{index:02d}")
            _write_cell(tbl_row, 1, param_name)
            _write_cell(tbl_row, 2, str(row.get("pillar") or row.get("category") or "-"))
            _write_cell(tbl_row, 3, "BC" if sl == "PASS" else "N/A" if sl in ("NOT COLLECTED", "LICENSING REQUIRED", "MANUAL VALIDATION") else "AB")
            _write_cell(tbl_row, 4, sev_key.title())
            # Row background: green for pass, red for fail, light grey otherwise
            row_bg = "E8F5E9" if sl == "PASS" else "FFEBEE" if sl == "FAIL" else "F9F9F9"
            for cell in tbl_row.cells:
                _set_cell_bg(cell, row_bg)
            # Severity column override with severity-specific color
            _set_cell_bg(tbl_row.cells[4], _SEVERITY_COLORS.get(sev_key, "F5F5F5"))


def _update_detailed_blocks(doc, rows: list[dict[str, Any]], template_order: dict[str, list[str]]) -> None:
    ordered = [row for service_rows in _ordered_rows_by_service(rows, template_order).values() for row in service_rows]
    risk_indices = [
        index for index, para in enumerate(doc.paragraphs)
        if " ".join(para.text.split()).startswith("Risk Rating:")
    ]
    for row, index in zip(ordered, risk_indices):
        _set_paragraph_text(
            doc.paragraphs[index],
            f"Risk Rating: {str(row.get('severity') or 'info').title()} - {_status_label(row).title()}",
        )
        description_index = _find_next_paragraph(doc, index + 1, "Description:")
        if description_index is not None and description_index + 1 < len(doc.paragraphs):
            actual = row.get("actual_result") or "-"
            expected = row.get("expected_result") or row.get("expected_output") or "-"
            description = row.get("description") or "Assessment control evaluated for Copilot readiness."
            _set_paragraph_text(
                doc.paragraphs[description_index + 1],
                f"{description}\nActual Value: {actual}\nExpected Value: {expected}",
            )
        risk_index = _find_next_paragraph(doc, index + 1, "Risk:")
        if risk_index is not None and risk_index + 1 < len(doc.paragraphs):
            _set_paragraph_text(doc.paragraphs[risk_index + 1], _risk_text(row))


def _update_template_conclusion(
    doc,
    rows: list[dict[str, Any]],
    tenant_name: str,
    summary: dict[str, Any],
    readiness_score: float,
    readiness_level: str,
) -> None:
    conclusion_index = next(
        (index for index, para in enumerate(doc.paragraphs) if " ".join(para.text.split()) == "Conclusion"),
        None,
    )
    if conclusion_index is None:
        return
    paragraphs = _conclusion(tenant_name, summary, readiness_score, readiness_level, rows)
    target_index = conclusion_index + 1
    for paragraph in paragraphs:
        if target_index >= len(doc.paragraphs):
            doc.add_paragraph(paragraph)
        else:
            _set_paragraph_text(doc.paragraphs[target_index], paragraph)
        target_index += 1


def _ordered_rows_by_service(
    rows: list[dict[str, Any]],
    template_order: dict[str, list[str]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {service: [] for service in SERVICE_ORDER}
    for row in rows:
        service = _service_name(row)
        if service not in grouped:
            service = "Microsoft Purview" if _is_purview_row(row) else service
        grouped.setdefault(service, []).append(row)
    if template_order:
        for service, service_rows in grouped.items():
            grouped[service] = _sort_like_template(service_rows, template_order.get(service, []))
    return {service: grouped.get(service, []) for service in SERVICE_ORDER if grouped.get(service)}


def _template_parameter_order(doc) -> dict[str, list[str]]:
    order: dict[str, list[str]] = {}
    for table, service in zip(doc.tables[:6], SERVICE_ORDER):
        order[service] = [
            row.cells[1].text.strip()
            for row in table.rows[1:]
            if len(row.cells) > 1 and row.cells[1].text.strip()
        ]
    return order


def _sort_like_template(rows: list[dict[str, Any]], template_names: list[str]) -> list[dict[str, Any]]:
    if not template_names:
        return rows
    used: set[int] = set()
    ordered: list[dict[str, Any]] = []
    for name in template_names:
        best_index = None
        best_score = 0.0
        for index, row in enumerate(rows):
            if index in used:
                continue
            score = _name_similarity(name, str(row.get("title") or row.get("parameter_key") or ""))
            if score > best_score:
                best_score = score
                best_index = index
        if best_index is not None and best_score >= 0.68:
            used.add(best_index)
            ordered.append(rows[best_index])
    ordered.extend(row for index, row in enumerate(rows) if index not in used)
    return ordered


def _name_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize_name(left), _normalize_name(right)).ratio()


def _normalize_name(value: str) -> str:
    value = value.lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value.rstrip("s")


def _is_purview_row(row: dict[str, Any]) -> bool:
    text = f"{row.get('parameter_key', '')} {row.get('title', '')} {row.get('service', '')}".lower()
    return any(token in text for token in ["purview", "audit", "dlp", "label", "retention", "compliance", "lockbox"])


def _resize_table(table, target_rows: int) -> None:
    while len(table.rows) < target_rows:
        table.add_row()
    # Collect excess rows first, then remove — never modify while iterating
    excess = list(table.rows[target_rows:])
    for row in excess:
        row._tr.getparent().remove(row._tr)


def _write_cell(row, col_idx: int, text: str) -> None:
    """Write sanitized text to a table cell, preserving existing run formatting."""
    if col_idx >= len(row.cells):
        return
    cell = row.cells[col_idx]
    safe = _sanitize(text)
    # Clear all runs in all paragraphs, write to first paragraph's first run
    for para in cell.paragraphs:
        for run in para.runs:
            run.text = ""
    if cell.paragraphs and cell.paragraphs[0].runs:
        cell.paragraphs[0].runs[0].text = safe
    elif cell.paragraphs:
        cell.paragraphs[0].add_run(safe)
    else:
        # Fallback: use the cell.text setter (clears and rewrites the cell)
        cell.text = safe


_SEVERITY_COLORS = {
    "critical": "FFE6E6",
    "high":     "FFF0E6",
    "medium":   "FFFDE6",
    "low":      "F5F5F5",
    "info":     "E6F0FF",
}


def _set_cell_bg(cell, hex_color: str) -> None:
    """Set table cell background fill using w:shd OOXML element."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for existing in tcPr.findall(qn("w:shd")):
        tcPr.remove(existing)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.upper())
    tcPr.append(shd)


def _find_next_paragraph(doc, start: int, exact_text: str) -> int | None:
    for index in range(start, len(doc.paragraphs)):
        if " ".join(doc.paragraphs[index].text.split()) == exact_text:
            return index
        if " ".join(doc.paragraphs[index].text.split()).startswith("Risk Rating:"):
            return None
    return None


def _set_paragraph_text(paragraph, text: str) -> None:
    from docx.oxml import OxmlElement

    safe = _sanitize(str(text))
    parts = safe.split("\n")

    # Clear all runs first
    for run in paragraph.runs:
        run.text = ""

    if paragraph.runs:
        first_run = paragraph.runs[0]
        first_run.text = parts[0]
        # Insert line-break elements for subsequent parts
        for part in parts[1:]:
            br = OxmlElement("w:br")
            first_run._r.append(br)
            t = OxmlElement("w:t")
            t.text = part
            first_run._r.append(t)
    else:
        run = paragraph.add_run(parts[0])
        for part in parts[1:]:
            from docx.oxml import OxmlElement as _OE
            br = _OE("w:br")
            run._r.append(br)
            t = _OE("w:t")
            t.text = part
            run._r.append(t)


def _deployment_sentence(readiness_level: str) -> str:
    if readiness_level == "Ready":
        return "The environment is broadly ready for Copilot enablement with continued operational monitoring."
    if readiness_level == "Conditionally Ready":
        return "Targeted remediation is recommended before broad Copilot enablement."
    return "Significant remediation is required prior to enabling Copilot in the production environment."


def _summary_table(
    doc,
    summary: dict[str, Any],
    readiness_score: float,
    readiness_level: str,
    tenant_id: str,
    assessment_date: str,
) -> None:
    metrics = [
        ("Tenant ID", tenant_id),
        ("Assessment Date", assessment_date),
        ("Total Parameters", summary["total"]),
        ("Pass", summary["pass"]),
        ("Fail", summary["fail"]),
        ("Collection Error", summary["collection_error"]),
        ("Licensing Required", summary["licensing_required"]),
        ("Manual Validation", summary["manual_validation"]),
        ("Overall Readiness Score", f"{readiness_score:.2f}%"),
        ("Readiness Level", readiness_level),
    ]
    _table(doc, ["Metric", "Value"], metrics)


def _service_summary_tables(doc, rows: list[dict[str, Any]]) -> None:
    summary_rows = []
    for service in SERVICE_ORDER:
        items = [row for row in rows if _service_name(row) == service]
        if not items:
            continue
        counts = _status_counter(items)
        total = len(items)
        passed = counts.get("PASS", 0)
        failed = counts.get("FAIL", 0) + counts.get("COLLECTION ERROR", 0)
        readiness = round((passed / total) * 100, 2) if total else 0
        summary_rows.append((service, total, passed, failed, f"{readiness}%"))
    if summary_rows:
        _heading(doc, "Service Readiness Summary", level=2)
        _table(doc, ["Service", "Total", "Pass", "Fail / Error", "Readiness"], summary_rows)


def _parameter_detail(doc, index: int, row: dict[str, Any]) -> None:
    title = str(row.get("title") or row.get("parameter_key") or f"Parameter {index}")
    _heading(doc, f"{index:02d}: {title}", level=3)
    values = [
        ("Parameter Name", title),
        ("Domain", _service_name(row)),
        ("CRA Pillar", row.get("pillar") or row.get("category") or "-"),
        ("Status", _status_label(row)),
        ("Severity", str(row.get("severity") or "info").title()),
        ("Description", row.get("description") or "Assessment control evaluated for Copilot readiness."),
        ("Risk", _risk_text(row)),
        ("Actual Value", row.get("actual_result") or _value(row.get("evidence"))),
        ("Expected Value", row.get("expected_result") or row.get("expected_output") or row.get("pass_criteria") or "-"),
        ("Evidence", _evidence_text(row)),
        ("Recommendation", row.get("recommendation") or "Review and remediate this control."),
    ]
    _table(doc, ["Field", "Value"], values)


def _table(doc, headers: list[str], rows: list[tuple[Any, ...] | list[Any]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = str(header)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = _value(value)


def _chart_block(doc, title: str, values: dict[str, int], inches_module: Any) -> None:
    _heading(doc, title, level=2)
    filtered = {key: int(value) for key, value in values.items() if int(value) > 0}
    if not filtered:
        doc.add_paragraph("No chartable data is available for this assessment.")
        return
    _table(doc, ["Category", "Count"], list(filtered.items()))
    image = _bar_chart_png(filtered)
    doc.add_picture(image, width=inches_module(5.8))


def _bar_chart_png(values: dict[str, int]) -> BytesIO:
    width, height = 900, 320
    margin_left, margin_top, bar_height, gap = 250, 35, 28, 18
    canvas = bytearray([255, 255, 255] * width * height)
    colors = [
        (46, 125, 50),
        (198, 40, 40),
        (245, 124, 0),
        (21, 101, 192),
        (117, 117, 117),
        (123, 31, 162),
    ]
    max_value = max(values.values()) or 1
    for index, (_, value) in enumerate(values.items()):
        y = margin_top + index * (bar_height + gap)
        if y + bar_height >= height:
            break
        bar_width = int((width - margin_left - 45) * (value / max_value))
        _rect(canvas, width, margin_left, y, max(4, bar_width), bar_height, colors[index % len(colors)])
        _rect(canvas, width, margin_left, y + bar_height + 3, width - margin_left - 45, 2, (230, 230, 230))
    return BytesIO(_png_bytes(width, height, bytes(canvas)))


def _rect(canvas: bytearray, width: int, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
    for yy in range(max(0, y), max(0, y) + max(0, h)):
        offset = (yy * width + x) * 3
        for _ in range(max(0, w)):
            if 0 <= offset <= len(canvas) - 3:
                canvas[offset : offset + 3] = bytes(color)
            offset += 3


def _png_bytes(width: int, height: int, rgb: bytes) -> bytes:
    raw = b"".join(b"\x00" + rgb[row * width * 3 : (row + 1) * width * 3] for row in range(height))
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _summary_for_rows(summary: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = _status_counter(rows)
    total = len(rows)
    passed = counts.get("PASS", 0)
    return {
        **summary,
        "total": total,
        "pass": passed,
        "fail": counts.get("FAIL", 0),
        "collection_error": counts.get("COLLECTION ERROR", 0),
        "licensing_required": counts.get("LICENSING REQUIRED", 0),
        "manual_validation": counts.get("MANUAL VALIDATION", 0),
        "overall_readiness": summary.get("overall_readiness")
        if summary.get("overall_readiness") is not None
        else (round((passed / total) * 100, 2) if total else 0),
    }


def _status_counter(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter[_status_label(row)] += 1
    return dict(counter)


def _severity_counter(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if _status_label(row) == "PASS":
            continue
        counter[str(row.get("severity") or "info").title()] += 1
    return dict(counter)


def _key_observations(rows: list[dict[str, Any]], tenant_name: str, readiness_score: float, readiness_level: str) -> list[str]:
    counts = _status_counter(rows)
    by_service: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        if _status_label(row) != "PASS":
            by_service[_service_name(row)] += 1
    top_services = sorted(by_service.items(), key=lambda item: item[1], reverse=True)[:3]
    observations = [
        f"{tenant_name} achieved an overall readiness score of {readiness_score:.2f}%, classified as {readiness_level}.",
        f"{counts.get('PASS', 0)} of {len(rows)} parameters passed based on collected runtime evidence.",
        f"{counts.get('FAIL', 0)} parameters failed and should be prioritized by severity before broad Copilot rollout.",
    ]
    if counts.get("COLLECTION ERROR", 0):
        observations.append(f"{counts['COLLECTION ERROR']} parameters have collection errors and require evidence collection remediation.")
    if counts.get("LICENSING REQUIRED", 0):
        observations.append(f"{counts['LICENSING REQUIRED']} parameters require licensing validation before final readiness certification.")
    if top_services:
        observations.append("Highest remediation concentration: " + ", ".join(f"{service} ({count})" for service, count in top_services) + ".")
    return observations


def _conclusion(
    tenant_name: str,
    summary: dict[str, Any],
    readiness_score: float,
    readiness_level: str,
    rows: list[dict[str, Any]],
) -> list[str]:
    counts = _status_counter(rows)
    return [
        (
            f"The Copilot Readiness Assessment for {tenant_name} evaluated {len(rows)} approved CRA parameters "
            f"across Microsoft 365 identity, security, compliance, and collaboration workloads."
        ),
        (
            f"The current readiness score is {readiness_score:.2f}% with a readiness level of {readiness_level}. "
            f"The assessment identified {counts.get('FAIL', 0)} failed controls, "
            f"{counts.get('COLLECTION ERROR', 0)} collection errors, "
            f"{counts.get('LICENSING REQUIRED', 0)} licensing-required controls, and "
            f"{counts.get('MANUAL VALIDATION', 0)} manual validations."
        ),
        (
            "Before production Copilot rollout, the organization should remediate failed controls, resolve evidence "
            "collection gaps, confirm licensing prerequisites, and rerun the assessment to validate readiness."
        ),
    ]


def _risk_text(row: dict[str, Any]) -> str:
    explicit = row.get("risk") or row.get("business_impact")
    if explicit:
        return _value(explicit)
    text = f"{row.get('title', '')} {row.get('service', '')} {row.get('pillar', '')}".lower()
    if any(token in text for token in ["mfa", "conditional", "admin", "identity", "guest"]):
        return "Identity control gaps can allow unauthorized or over-privileged access to information surfaced by Copilot."
    if any(token in text for token in ["label", "dlp", "retention", "audit", "purview", "lockbox"]):
        return "Compliance and information protection gaps can reduce confidence that Copilot respects governance expectations."
    if any(token in text for token in ["sharing", "sharepoint", "onedrive", "external"]):
        return "Collaboration and sharing gaps can increase the likelihood that Copilot surfaces content to unintended audiences."
    if "teams" in text:
        return "Teams governance gaps can affect meeting, chat, guest, and app data used by Copilot."
    return "This control affects the trust, governance, and operational readiness baseline required for responsible Copilot adoption."


def _evidence_text(row: dict[str, Any]) -> str:
    evidence = row.get("evidence")
    if isinstance(evidence, dict):
        raw = evidence.get("raw_response") or evidence.get("raw_evidence") or evidence.get("payload") or evidence
        return _value(raw)
    return _value(evidence)


def _value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (str, int, float)):
        return _sanitize(str(value))
    if isinstance(value, list):
        if not value:
            return "[]"
        return f"{len(value)} item(s): " + "; ".join(_value(item)[:120] for item in value[:3])
    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = []
        for key, item in list(value.items())[:8]:
            label = _sanitize(str(key)).replace("_", " ").title()
            parts.append(f"{label}: {_value(item)}")
        return "; ".join(parts)
    return _sanitize(str(value))


def _status_label(row: dict[str, Any]) -> str:
    return STATUS_LABELS.get(str(row.get("status") or "").lower(), str(row.get("status") or "NOT COLLECTED").upper())


def _service_name(row: dict[str, Any]) -> str:
    parameter_key = str(row.get("parameter_key") or "")
    if parameter_key in TEMPLATE_SERVICE_OVERRIDES:
        return TEMPLATE_SERVICE_OVERRIDES[parameter_key]
    raw = str(row.get("service") or row.get("technology") or row.get("category") or "").lower()
    if "entra" in raw or "identity" in raw:
        return "Entra ID"
    if "exchange" in raw:
        return "Exchange Online"
    if "purview" in raw or "compliance" in raw:
        return "Microsoft Purview"
    if "team" in raw:
        return "Microsoft Teams"
    if "onedrive" in raw:
        return "OneDrive for Business"
    if "sharepoint" in raw:
        return "SharePoint Online"
    return row.get("service") or "Microsoft 365"


def _tenant_name(summary: dict[str, Any], assessment: Any) -> str:
    return str(
        summary.get("tenant_name")
        or summary.get("customer_name")
        or getattr(assessment, "tenant_name", None)
        or getattr(assessment, "tenant_id", None)
        or "Tenant"
    )


def _assessment_date(summary: dict[str, Any], assessment: Any) -> str:
    value = summary.get("assessment_date") or getattr(assessment, "created_at", None)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%d-%m-%Y")
    if value:
        return str(value)
    return datetime.now(timezone.utc).strftime("%d-%m-%Y")


def _readiness_level(score: float) -> str:
    if score >= 85:
        return "Ready"
    if score >= 70:
        return "Conditionally Ready"
    if score >= 50:
        return "Needs Remediation"
    return "Not Ready"


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "tenant"


def _enable_field_update(doc) -> None:
    settings_element = doc.settings.element
    if settings_element.xpath("./w:updateFields"):
        return
    from docx.oxml import OxmlElement

    update_fields = OxmlElement("w:updateFields")
    update_fields.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "true")
    settings_element.append(update_fields)
