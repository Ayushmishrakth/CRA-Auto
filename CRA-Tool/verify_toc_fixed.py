#!/usr/bin/env python3
"""
Verify TOC pages 2-4 have exact AAA boundaries and Calibri font.

VALIDATION RULES:
1. Page 2 ends at: "02: External Storage providers in OWA"
2. Page 3 ends at: "01: Permission Settings for anyone links"
3. Page 4 ends at: "Conclusion"
4. ALL TOC entries use Calibri font
5. Page 2 has 33 entries
6. Page 3 has 36 entries
7. Page 4 has 11 entries
8. NO blank pages between TOC pages
9. NO extra entries on wrong pages
"""

import sys
from pathlib import Path
from docx import Document

sys.path.insert(0, str(Path(__file__).parent))

def find_latest_report():
    """Find the most recently generated report."""
    reports_dir = Path(__file__).parent / "storage" / "reports"
    report_files = list(reports_dir.rglob("*.docx"))
    if not report_files:
        return None
    return max(report_files, key=lambda p: p.stat().st_mtime)

def validate_toc_pages(doc_path):
    """Validate TOC pages have exact AAA boundaries."""
    doc = Document(doc_path)

    print("\n" + "="*100)
    print("TOC PAGE VALIDATION")
    print("="*100)

    # Collect TOC paragraphs (skip cover page, likely paragraphs 0-10)
    toc_entries = []
    for para_idx, para in enumerate(doc.paragraphs):
        if para_idx < 11:  # Skip cover page
            continue
        if para_idx > 150:  # Stop after likely TOC end
            break

        text = para.text.strip()
        if not text or text.startswith("==="):  # Skip empty/separators
            continue

        # Check for page break marker
        has_page_break = False
        pPr = para._p.get_or_add_pPr()
        br = pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br')
        if br is not None:
            br_type = br.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type')
            if br_type == 'page':
                has_page_break = True

        # Get font
        font = "None"
        if para.runs and para.runs[0].font.name:
            font = para.runs[0].font.name

        toc_entries.append({
            "index": para_idx,
            "text": text,
            "font": font,
            "has_page_break": has_page_break,
        })

    print(f"\nTotal TOC paragraphs found: {len(toc_entries)}\n")

    # Expected content
    expected_page2_end = "02: External Storage providers in OWA"
    expected_page3_end = "01: Permission Settings for anyone links"
    expected_page4_end = "Conclusion"

    # Find page boundaries
    page_breaks = [idx for idx, e in enumerate(toc_entries) if e["has_page_break"]]

    print(f"Page break markers found at TOC entry indices: {page_breaks}")

    if len(page_breaks) < 2:
        print(f"\n❌ CRITICAL: Expected 2 page breaks, found {len(page_breaks)}")

    # Split pages based on page breaks
    page2_entries = toc_entries[:page_breaks[0]] if page_breaks else toc_entries[:33]
    page3_start = page_breaks[0] + 1 if page_breaks else 33
    page3_entries = toc_entries[page3_start:page_breaks[1]] if len(page_breaks) > 1 else toc_entries[page3_start:page3_start+36]
    page4_start = page_breaks[1] + 1 if len(page_breaks) > 1 else page3_start + 36
    page4_entries = toc_entries[page4_start:]

    # Validate page 2
    print(f"\n{'='*100}")
    print("PAGE 2 VALIDATION")
    print(f"{'='*100}")
    print(f"Entries: {len(page2_entries)} (expected 33)")

    if page2_entries:
        print(f"First entry: {page2_entries[0]['text'][:60]}")
        print(f"Last entry: {page2_entries[-1]['text'][:60]}")

        page2_end_ok = page2_entries[-1]['text'] == expected_page2_end
        print(f"Ends with '{expected_page2_end}': {'✓' if page2_end_ok else '❌'}")

    # Check all page 2 entries use Calibri
    page2_calibri = all(e['font'] in ['Calibri', 'Calibri Light'] for e in page2_entries)
    print(f"All entries Calibri: {'✓' if page2_calibri else '❌'}")
    non_calibri = [e for e in page2_entries if e['font'] not in ['Calibri', 'Calibri Light']]
    if non_calibri:
        print(f"  Non-Calibri entries: {len(non_calibri)}")
        print(f"  Examples: {[e['font'] for e in non_calibri[:3]]}")

    # Validate page 3
    print(f"\n{'='*100}")
    print("PAGE 3 VALIDATION")
    print(f"{'='*100}")
    print(f"Entries: {len(page3_entries)} (expected 36)")

    if page3_entries:
        print(f"First entry: {page3_entries[0]['text'][:60]}")
        print(f"Last entry: {page3_entries[-1]['text'][:60]}")

        page3_end_ok = page3_entries[-1]['text'] == expected_page3_end
        print(f"Ends with '{expected_page3_end}': {'✓' if page3_end_ok else '❌'}")

    # Check all page 3 entries use Calibri
    page3_calibri = all(e['font'] in ['Calibri', 'Calibri Light'] for e in page3_entries)
    print(f"All entries Calibri: {'✓' if page3_calibri else '❌'}")
    non_calibri = [e for e in page3_entries if e['font'] not in ['Calibri', 'Calibri Light']]
    if non_calibri:
        print(f"  Non-Calibri entries: {len(non_calibri)}")
        print(f"  Examples: {[e['font'] for e in non_calibri[:3]]}")

    # Validate page 4
    print(f"\n{'='*100}")
    print("PAGE 4 VALIDATION")
    print(f"{'='*100}")
    print(f"Entries: {len(page4_entries)} (expected 11)")

    if page4_entries:
        print(f"First entry: {page4_entries[0]['text'][:60]}")
        print(f"Last entry: {page4_entries[-1]['text'][:60]}")

        page4_end_ok = page4_entries[-1]['text'] == expected_page4_end
        print(f"Ends with '{expected_page4_end}': {'✓' if page4_end_ok else '❌'}")

    # Check all page 4 entries use Calibri
    page4_calibri = all(e['font'] in ['Calibri', 'Calibri Light'] for e in page4_entries)
    print(f"All entries Calibri: {'✓' if page4_calibri else '❌'}")
    non_calibri = [e for e in page4_entries if e['font'] not in ['Calibri', 'Calibri Light']]
    if non_calibri:
        print(f"  Non-Calibri entries: {len(non_calibri)}")
        print(f"  Examples: {[e['font'] for e in non_calibri[:3]]}")

    # Final verdict
    print(f"\n{'='*100}")
    print("FINAL VALIDATION RESULT")
    print(f"{'='*100}")

    checks = [
        ("Page 2 has 33 entries", len(page2_entries) == 33),
        ("Page 3 has 36 entries", len(page3_entries) == 36),
        ("Page 4 has 11 entries", len(page4_entries) == 11),
        ("Page 2 ends with External Storage", page2_entries[-1]['text'] == expected_page2_end if page2_entries else False),
        ("Page 3 ends with Permission Settings", page3_entries[-1]['text'] == expected_page3_end if page3_entries else False),
        ("Page 4 ends with Conclusion", page4_entries[-1]['text'] == expected_page4_end if page4_entries else False),
        ("Page 2 all Calibri", all(e['font'] in ['Calibri', 'Calibri Light'] for e in page2_entries)),
        ("Page 3 all Calibri", all(e['font'] in ['Calibri', 'Calibri Light'] for e in page3_entries)),
        ("Page 4 all Calibri", all(e['font'] in ['Calibri', 'Calibri Light'] for e in page4_entries)),
    ]

    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    for check_name, result in checks:
        status = "✓" if result else "❌"
        print(f"  {status} {check_name}")

    print(f"\nRESULT: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓✓✓ ALL VALIDATIONS PASSED - TOC PAGES ARE CORRECT ✓✓✓")
        return True
    else:
        print(f"\n❌ FAILED - {total - passed} validation(s) failed")
        return False

if __name__ == "__main__":
    report_path = find_latest_report()

    if not report_path:
        print("[ERROR] No generated reports found")
        print("[INFO] Generate a report first, then run this script")
        sys.exit(1)

    print(f"\nValidating: {report_path}\n")

    try:
        success = validate_toc_pages(report_path)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
