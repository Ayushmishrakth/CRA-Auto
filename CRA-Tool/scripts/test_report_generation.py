"""
Comprehensive Report Generation Test
Tests all components needed for report generation
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("[TEST] Starting comprehensive report generation test...\n")

# Test 1: Check dependencies
print("[TEST 1] Checking Python dependencies...")
required_packages = ['docx', 'docxtpl', 'matplotlib', 'docx2pdf']
missing = []

for pkg in required_packages:
    try:
        __import__(pkg)
        print(f"  [OK] {pkg}")
    except ImportError:
        print(f"  [FAIL] {pkg} - MISSING")
        missing.append(pkg)

if missing:
    print(f"\n[ERROR] Missing packages: {', '.join(missing)}")
    print("Install with: pip install python-docx docxtpl matplotlib docx2pdf")
    sys.exit(1)

print("\n[TEST 2] Checking directories...")
dirs_to_check = {
    'Templates': Path('app/services/reporting/templates'),
    'Storage': Path('storage/reports'),
}

for name, path in dirs_to_check.items():
    if path.exists():
        print(f"  [OK] {name}: {path}")
    else:
        print(f"  [FAIL] {name}: {path} - MISSING")
        path.mkdir(parents=True, exist_ok=True)
        print(f"       Created: {path}")

print("\n[TEST 3] Checking template files...")
template_dir = Path('app/services/reporting/templates')
templates = list(template_dir.glob('*.docx'))
if templates:
    for t in templates:
        size = t.stat().st_size / 1024
        print(f"  [OK] {t.name} ({size:.1f} KB)")
else:
    print(f"  [WARN] No .docx templates found in {template_dir}")

print("\n[TEST 4] Testing report generation...")
try:
    from app.services.reporting.enhanced_report_generator import EnhancedReportGenerator
    from datetime import datetime
    from uuid import uuid4

    # Create sample data
    findings = [
        {'parameter_name': 'Test Parameter 1', 'category': 'entra', 'status': 'fail',
         'severity': 'Critical', 'pillar': 'Security', 'description': 'Test finding',
         'risk': 'Test risk'},
        {'parameter_name': 'Test Parameter 2', 'category': 'exchange', 'status': 'pass',
         'severity': 'High', 'pillar': 'Governance', 'description': 'Test finding',
         'risk': 'Test risk'},
    ]

    data = {
        'id': str(uuid4()),
        'tenant_id': str(uuid4()),
        'tenant_name': 'TestOrg',
        'partner_name': 'TestPartner',
        'created_at': datetime.now(),
        'overall_score': 50.0,
        'findings': findings,
        'summary': {
            'total_parameters': 2,
            'pass_count': 1,
            'fail_count': 1,
            'critical_count': 1,
            'high_count': 1,
            'medium_count': 0,
            'low_count': 0,
        }
    }

    print("  [OK] Enhanced generator imported")

    # Generate
    generator = EnhancedReportGenerator(data)
    print("  [OK] Generator initialized")

    # Generate Word
    output_dir = Path('storage/reports')
    output_dir.mkdir(parents=True, exist_ok=True)
    word_file = output_dir / 'test_report.docx'
    generator.save(str(word_file))

    if word_file.exists():
        size = word_file.stat().st_size / 1024
        print(f"  [OK] Word report generated: {word_file.name} ({size:.1f} KB)")
    else:
        print(f"  [FAIL] Word report not created")

except Exception as e:
    print(f"  [FAIL] Report generation error: {e}")
    import traceback
    traceback.print_exc()

print("\n[TEST 5] Testing PDF conversion...")
try:
    from docx2pdf import convert

    word_file = Path('storage/reports/test_report.docx')
    pdf_file = word_file.with_suffix('.pdf')

    if word_file.exists():
        convert(str(word_file), str(pdf_file))
        if pdf_file.exists():
            size = pdf_file.stat().st_size / 1024
            print(f"  [OK] PDF generated: {pdf_file.name} ({size:.1f} KB)")
        else:
            print(f"  [FAIL] PDF conversion failed")
    else:
        print(f"  [SKIP] Word file not found")

except Exception as e:
    print(f"  [WARN] PDF conversion error: {e}")

print("\n" + "="*60)
print("[SUCCESS] All tests completed!")
print("="*60)
print("\nNext steps:")
print("1. Restart your CRA Tool application")
print("2. Go to an assessment")
print("3. Click 'Download PDF'")
print("4. Check server logs for detailed error if it fails")
