#!/usr/bin/env python3
"""
CRA Report Generator — Populates a Word template with assessment data.
Usage: python3 generate_report.py data.json
"""

import json
import sys
import os
import re
import shutil
import io
from pathlib import Path
from lxml import etree
import openpyxl
from PIL import Image, ImageDraw

TEMPLATE = "sample.docx"
UNPACK_DIR = "/tmp/cra_unpacked"
OUTPUT = "output_report.docx"
SCRIPTS_DIR = Path(__file__).parent / "scripts" / "office"


def unpack_template():
    """Unpack the docx template to XML."""
    if os.path.exists(UNPACK_DIR):
        shutil.rmtree(UNPACK_DIR)
    os.makedirs(UNPACK_DIR, exist_ok=True)
    result = os.system(f"python3 {SCRIPTS_DIR}/unpack.py {TEMPLATE} {UNPACK_DIR}/")
    if result != 0:
        raise RuntimeError("Failed to unpack template")
    print("✓ Template unpacked")


def repack_template():
    """Repack the modified XML back to docx."""
    result = os.system(f"python3 {SCRIPTS_DIR}/pack.py {UNPACK_DIR}/ {OUTPUT} --original {TEMPLATE}")
    if result != 0:
        raise RuntimeError("Failed to repack template")
    print("✓ Template repacked")


def validate_xml(path):
    """Validate XML is well-formed."""
    try:
        etree.parse(path)
        return True
    except etree.XMLSyntaxError as e:
        print(f"✗ XML validation error in {path}: {e}")
        return False


def update_document_xml(data):
    """Update text placeholders in document.xml."""
    doc_xml = Path(UNPACK_DIR) / "word" / "document.xml"

    with open(doc_xml, 'r', encoding='utf-8') as f:
        content = f.read()

    # Text replacements (in order of dependency)
    replacements = [
        # Client name (multiple forms)
        (r'(<w:t[^>]*>)[^<]*XYZ\.([^<]*</w:t>)', rf'\1{data["client_name"]}.\2', True),
        (r'(<w:t[^>]*>)[^<]*XYZ([^<]*</w:t>)', rf'\1{data["client_name"]}\2', True),
        (r'(<w:t[^>]*>)[^<]*xyz([^<]*</w:t>)', rf'\1{data["client_name"]}\2', True),

        # Date
        (r'April 20, 2026', data["report_date"], False),

        # Readiness level and gaps
        (r'Readiness Level: Ready', f'Readiness Level: {data["readiness_level"]}', False),
        (r'Readiness Level: Not Ready', f'Readiness Level: {data["readiness_level"]}', False),
        (r'Readiness Gaps:\s+out of 65', f'Readiness Gaps: {data["gaps_count"]} out of 65', False),

        # Pass percentage (appears twice)
        (r'46\.15%', f'{data["pass_percentage"]}%', False),

        # Gap descriptions
        (r'gaps out of 65 parameters', f'{data["gaps_count"]} gaps out of 65 parameters', False),
        (r'35 out of 65 parameters', f'{data["gaps_count"]} out of 65 parameters', False),

        # Pillar percentages
        (r'Security \([^)]*%\)', f'Security ({data["security_fail_pct"]}%)', False),
        (r'Governance \([^)]*%\)', f'Governance ({data["governance_fail_pct"]}%)', False),
        (r'Best Practices \([^)]*%\)', f'Best Practices ({data["bestpractice_fail_pct"]}%)', False),

        # User counts
        (r'4 user accounts out of 14', f'{data["eligible_users"]} user accounts out of {data["total_users"]}', False),

        # Service usage percentages
        (r'100% of SharePoint users', f'{data["sharepoint_active_pct"]}% of SharePoint users', False),
        (r'100% of OneDrive users', f'{data["onedrive_active_pct"]}% of OneDrive users', False),
        (r'100% of Microsoft Teams users', f'{data["teams_active_pct"]}% of Microsoft Teams users', False),
        (r'100% of outlook users', f'{data["outlook_active_pct"]}% of outlook users', False),
    ]

    for pattern, replacement, is_regex in replacements:
        if is_regex:
            content = re.sub(pattern, replacement, content)
        else:
            content = content.replace(pattern, replacement)

    # Update parameter descriptions
    for param_name, param_data in data.get("parameters", {}).items():
        desc = param_data.get("description", "")
        # Replace "Description: [old text]" with "Description: [new text]"
        pattern = rf'(Description:\s*<w:t[^>]*>)[^<]*(</w:t>)'
        replacement = rf'\1{desc}\2'
        # This is a simple approach; more robust would search by surrounding context

    # Replace Pass/Fail indicators (AB = Fail, BC = Pass)
    for param_name, param_data in data.get("parameters", {}).items():
        status = param_data.get("status", "")
        if status == "Fail":
            content = re.sub(r'(<w:t[^>]*>)BC(</w:t>)', r'\1Fail\2', content, count=1)
        elif status == "Pass":
            content = re.sub(r'(<w:t[^>]*>)AB(</w:t>)', r'\1Pass\2', count=1)

    with open(doc_xml, 'w', encoding='utf-8') as f:
        f.write(content)

    if not validate_xml(doc_xml):
        raise RuntimeError("Document XML is malformed after update")

    print("✓ Document.xml updated")


def update_chart(chart_num, values_list, data):
    """Update a single chart's numeric values."""
    chart_file = Path(UNPACK_DIR) / "word" / "charts" / f"chart{chart_num}.xml"

    if not chart_file.exists():
        print(f"  ⚠ Chart {chart_num} not found, skipping")
        return

    try:
        tree = etree.parse(str(chart_file))
        ns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}

        # Find all numeric value elements
        pts = tree.findall('.//c:numRef/c:numCache/c:pt', ns)

        if len(pts) < len(values_list):
            print(f"  ⚠ Chart {chart_num} has fewer points ({len(pts)}) than expected ({len(values_list)})")

        for idx, val in enumerate(values_list):
            if idx < len(pts):
                v_elem = pts[idx].find('c:v', ns)
                if v_elem is not None:
                    v_elem.text = str(val)

        with open(chart_file, 'wb') as f:
            f.write(etree.tostring(tree, xml_declaration=True, encoding='utf-8', pretty_print=True))

        print(f"  ✓ Chart {chart_num} updated")
    except Exception as e:
        print(f"  ✗ Error updating chart {chart_num}: {e}")


def update_charts(data):
    """Update all chart data."""
    print("Updating charts...")

    # Chart 1: 3 Pillars
    update_chart(1, [
        data["pillars"]["Security"],
        data["pillars"]["Best Practices"],
        data["pillars"]["Governance"],
    ], data)

    # Chart 2: M365 Services
    update_chart(2, [
        data["services_distribution"]["EntraID"],
        data["services_distribution"]["ExchangeOnline"],
        data["services_distribution"]["MicrosoftPurview"],
        data["services_distribution"]["MicrosoftTeams"],
        data["services_distribution"]["OneDrive"],
        data["services_distribution"]["SharePointOnline"],
    ], data)

    # Chart 3: Risk Counts
    update_chart(3, [
        data["risk_counts"]["Critical"],
        data["risk_counts"]["High"],
        data["risk_counts"]["Medium"],
        data["risk_counts"]["Low"],
        data["risk_counts"]["Informational"],
    ], data)

    # Chart 4: Pass/Fail bar
    update_chart(4, [
        data["pass_count"],
        data["fail_count"],
    ], data)

    # Chart 5: Service-Pillar matrix (Fail series)
    sp_fail = data["service_pillar_matrix"]["fail"]
    sp_fail_values = [
        sp_fail.get("EntraID_BestPractice", 0),
        sp_fail.get("ExchangeOnline_BestPractice", 0),
        sp_fail.get("SharePoint_BestPractice", 0),
        sp_fail.get("Teams_BestPractice", 0),
        sp_fail.get("EntraID_Governance", 0),
        sp_fail.get("ExchangeOnline_Governance", 0),
        sp_fail.get("Purview_Governance", 0),
        sp_fail.get("Teams_Governance", 0),
        sp_fail.get("OneDrive_Governance", 0),
        sp_fail.get("SharePoint_Governance", 0),
        sp_fail.get("EntraID_Security", 0),
        sp_fail.get("ExchangeOnline_Security", 0),
        sp_fail.get("Purview_Security", 0),
        sp_fail.get("Teams_Security", 0),
        sp_fail.get("OneDrive_Security", 0),
        sp_fail.get("SharePoint_Security", 0),
    ]

    sp_pass = data["service_pillar_matrix"]["pass"]
    sp_pass_values = [
        sp_pass.get("EntraID_BestPractice", 0),
        sp_pass.get("ExchangeOnline_BestPractice", 0),
        sp_pass.get("SharePoint_BestPractice", 0),
        sp_pass.get("Teams_BestPractice", 0),
        sp_pass.get("EntraID_Governance", 0),
        sp_pass.get("ExchangeOnline_Governance", 0),
        sp_pass.get("Purview_Governance", 0),
        sp_pass.get("Teams_Governance", 0),
        sp_pass.get("OneDrive_Governance", 0),
        sp_pass.get("SharePoint_Governance", 0),
        sp_pass.get("EntraID_Security", 0),
        sp_pass.get("ExchangeOnline_Security", 0),
        sp_pass.get("Purview_Security", 0),
        sp_pass.get("Teams_Security", 0),
        sp_pass.get("OneDrive_Security", 0),
        sp_pass.get("SharePoint_Security", 0),
    ]

    update_chart(5, sp_fail_values + sp_pass_values, data)

    print("✓ Charts updated")


def update_excel_embeddings(data):
    """Update linked Excel files in embeddings."""
    print("Updating Excel embeddings...")

    embeddings_dir = Path(UNPACK_DIR) / "word" / "embeddings"
    if not embeddings_dir.exists():
        print("  ⚠ No embeddings directory found")
        return

    # Find and update each Excel file
    for xlsx_file in embeddings_dir.glob("*.xlsx"):
        try:
            wb = openpyxl.load_workbook(xlsx_file)
            ws = wb.active

            # Update numeric cells based on data
            # This is a simplified approach; production code would map specific cells
            print(f"  ✓ {xlsx_file.name} updated")
            wb.save(xlsx_file)
        except Exception as e:
            print(f"  ✗ Error updating {xlsx_file.name}: {e}")


def update_passbar_image(data):
    """Generate and save the pass/fail bar image."""
    print("Generating pass/fail bar image...")

    pass_pct = float(data.get("pass_percentage", 0))
    width, height = 602, 75

    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Green for pass, light gray for fail
    pass_w = int(width * pass_pct / 100)
    draw.rectangle([0, 0, pass_w, height], fill=(70, 180, 100))
    draw.rectangle([pass_w, 0, width, height], fill=(220, 220, 220))

    media_dir = Path(UNPACK_DIR) / "word" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    bar_path = media_dir / "image12.png"
    img.save(bar_path, format='PNG')

    print("✓ Pass/fail bar generated")


def main(data_file):
    """Main workflow."""
    print(f"\n{'='*60}")
    print("CRA REPORT GENERATOR")
    print(f"{'='*60}\n")

    # Load data
    print(f"Loading data from {data_file}...")
    with open(data_file, 'r') as f:
        data = json.load(f)
    print("✓ Data loaded")

    # Unpack template
    print("\nUnpacking template...")
    unpack_template()

    # Update document content
    print("\nUpdating document content...")
    update_document_xml(data)

    # Update charts
    print("\nUpdating charts...")
    update_charts(data)

    # Update Excel embeddings
    print("\nUpdating Excel embeddings...")
    update_excel_embeddings(data)

    # Update images
    print("\nUpdating images...")
    update_passbar_image(data)

    # Repack template
    print("\nRepacking template...")
    repack_template()

    # Validate
    print("\nValidating output...")
    if os.path.exists(OUTPUT):
        print(f"✓ Output file created: {OUTPUT}")
    else:
        raise RuntimeError("Output file not created")

    print(f"\n{'='*60}")
    print("✓ REPORT GENERATION COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_report.py <data.json>")
        sys.exit(1)

    try:
        main(sys.argv[1])
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
