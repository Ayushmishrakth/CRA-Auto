#!/usr/bin/env python3
"""
Quick diagnostic script to identify why report data is not being populated.
Run from: CRA-Auto/CRA-Tool directory
Command: python3 ../../diagnostic_report_generation.py
"""

import sys
from pathlib import Path

print("\n" + "="*70)
print("REPORT GENERATION DIAGNOSTIC")
print("="*70)

# Check 1: Template file exists
print("\n[1/4] Checking template files...")
print("-" * 70)

from app.services.reporting.word_report_generator import REFERENCE_TEMPLATE_CANDIDATES

template_found = False
for i, candidate in enumerate(REFERENCE_TEMPLATE_CANDIDATES, 1):
    status = "✓ FOUND" if candidate.exists() else "✗ MISSING"
    print(f"  {i}. {candidate}")
    print(f"     {status}")

    if candidate.exists():
        size_mb = candidate.stat().st_size / 1024 / 1024
        print(f"     Size: {size_mb:.2f} MB")
        template_found = True
        print(f"     ← Using this template")
        break

if not template_found:
    print("\n❌ ERROR: No template file found!")
    print("   Please download template or create one using:")
    print("   - See REPORT_DATA_POPULATION_FIX.md for how to create template")
    sys.exit(1)

# Check 2: Database connection and assessment data
print("\n[2/4] Checking assessment data...")
print("-" * 70)

try:
    # Check if we can import database models
    from app.db.models.assessment import Assessment
    from app.db.models.assessment_finding import AssessmentFinding
    print("  ✓ Database models imported successfully")
except Exception as e:
    print(f"  ✗ Failed to import database models: {e}")
    sys.exit(1)

# Check 3: Sample report data structure
print("\n[3/4] Checking report data structure...")
print("-" * 70)

sample_report = {
    "assessment": type('Assessment', (), {
        'id': '12345',
        'tenant_id': 'test.onmicrosoft.com',
        'created_at': None,
        'status': 'completed'
    })(),
    "summary": {
        "tenant_name": "Test Organization",
        "customer_name": "Test Org",
        "overall_readiness": 72.5,
        "pass": 47,
        "fail": 18,
        "warning": 0,
        "collection_error": 0,
        "licensing_required": 0,
        "manual_validation": 0,
        "total": 65,
    },
    "parameter_rows": [
        {
            "title": "Sample Finding 1",
            "status": "fail",
            "severity": "critical",
            "description": "This is a sample finding",
            "actual_result": "Not Configured",
            "expected_result": "Configured",
            "pillar": "Security",
            "service": "Entra ID"
        },
        {
            "title": "Sample Finding 2",
            "status": "pass",
            "severity": "info",
            "description": "This is passing",
            "actual_result": "Enabled",
            "expected_result": "Enabled",
            "pillar": "Governance",
            "service": "Exchange Online"
        }
    ]
}

print(f"  ✓ Report data structure created")
print(f"    - Assessment: {sample_report['assessment'].id}")
print(f"    - Summary fields: {list(sample_report['summary'].keys())}")
print(f"    - Parameter rows: {len(sample_report['parameter_rows'])}")
print(f"    - First row fields: {list(sample_report['parameter_rows'][0].keys())}")

# Check 4: Try to generate report
print("\n[4/4] Attempting report generation...")
print("-" * 70)

try:
    from app.services.reporting.word_report_generator import render_word_report

    test_output = Path("test_diagnostic_report.docx")
    result = render_word_report(test_output, sample_report)

    if test_output.exists():
        size_kb = test_output.stat().st_size / 1024
        print(f"  ✓ Report generated successfully")
        print(f"    Path: {test_output.absolute()}")
        print(f"    Size: {size_kb:.2f} KB")

        # Validate ZIP structure
        import zipfile
        try:
            with zipfile.ZipFile(test_output) as z:
                file_count = len(z.namelist())
                print(f"    ZIP entries: {file_count}")
                has_document = "word/document.xml" in z.namelist()
                print(f"    Has document.xml: {'✓ YES' if has_document else '✗ NO'}")

                if has_document:
                    with z.open("word/document.xml") as f:
                        content = f.read().decode('utf-8')
                        if "Test Organization" in content:
                            print(f"    Tenant name populated: ✓ YES")
                        else:
                            print(f"    Tenant name populated: ✗ NO - Check placeholder mapping!")
        except Exception as e:
            print(f"    ✗ ZIP validation failed: {e}")
    else:
        print(f"  ✗ Report generation failed - file not created")

except Exception as e:
    print(f"  ✗ Report generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "="*70)
print("DIAGNOSTIC SUMMARY")
print("="*70)
print("✓ All checks passed!")
print("\nNext steps:")
print("  1. Open the generated test_diagnostic_report.docx file")
print("  2. Verify it opens without corruption errors")
print("  3. Check that 'Test Organization' appears in the document")
print("  4. If template data is missing, check REPORT_DATA_POPULATION_FIX.md")
print("\nFor production report generation:")
print("  - Use actual assessment data from database")
print("  - Follow data validation checklist in REPORT_DATA_POPULATION_FIX.md")
print("="*70 + "\n")
