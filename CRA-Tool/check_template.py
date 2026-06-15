#!/usr/bin/env python3
"""
Check if the template has logo placeholder and what variables it expects.
"""

from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

TEMPLATE_PATH = Path("app/services/reporting/templates/sample.docx")

print("=" * 80)
print("TEMPLATE DIAGNOSTIC")
print("=" * 80)

# Check if template exists
print(f"\n1. TEMPLATE FILE")
print(f"   Path: {TEMPLATE_PATH.absolute()}")
print(f"   Exists: {TEMPLATE_PATH.exists()}")

if not TEMPLATE_PATH.exists():
    print(f"\n❌ ERROR: Template not found!")
    print(f"   Looking for: {TEMPLATE_PATH.absolute()}")

    # Try to find it
    print(f"\n   Searching for sample.docx...")
    for docx_file in Path(".").rglob("sample.docx"):
        print(f"   Found: {docx_file}")
    exit(1)

print(f"   Size: {TEMPLATE_PATH.stat().st_size} bytes")

# Extract and check placeholders
print(f"\n2. CHECKING TEMPLATE CONTENT")

try:
    with zipfile.ZipFile(TEMPLATE_PATH, 'r') as zip_ref:
        # Read document.xml
        try:
            doc_xml = zip_ref.read('word/document.xml').decode('utf-8')

            # Find all placeholders
            print(f"\n   Looking for placeholders in template...")

            placeholders = [
                'logo_image',
                'company_name',
                'address',
                'tenant_name',
                'partner_name',
                'assessment_date',
                'readiness_score',
                'fail_count',
                'total_count',
            ]

            found_placeholders = []
            for placeholder in placeholders:
                if placeholder in doc_xml:
                    found_placeholders.append(placeholder)
                    print(f"   ✅ Found: {{{{{placeholder}}}}}")
                else:
                    print(f"   ❌ Missing: {{{{{placeholder}}}}}")

            if not found_placeholders:
                print(f"\n   ⚠️  WARNING: No template placeholders found!")
                print(f"   This template may not be using jinja2/docxtpl format")

            # Show sample of what's in the template
            print(f"\n3. TEMPLATE CONTENT SAMPLE")
            if '{{' in doc_xml:
                print(f"   Template uses {{{{ }}}} format (docxtpl/jinja2)")
            else:
                print(f"   ❌ Template does NOT use {{{{ }}}} format!")

            # Count occurrences
            import re
            vars_pattern = r'\{\{.*?\}\}'
            variables = re.findall(vars_pattern, doc_xml)
            if variables:
                print(f"\n   Variables found in template:")
                unique_vars = set(variables)
                for var in sorted(unique_vars)[:20]:  # Show first 20
                    print(f"      - {var}")

        except KeyError:
            print(f"\n   ❌ No word/document.xml found in template!")
            print(f"   This doesn't look like a valid Word template")

except Exception as e:
    print(f"\n❌ Error reading template: {e}")
    exit(1)

# Check storage directories
print(f"\n4. STORAGE DIRECTORIES")

dirs_to_check = [
    "storage/temp/logos",
    "storage/reports",
    "storage/logos",
]

for dir_path in dirs_to_check:
    path = Path(dir_path)
    if path.exists():
        files = list(path.iterdir())
        print(f"   ✅ {dir_path}/ exists")
        if files:
            print(f"      Files: {len(files)}")
            for f in files[:5]:  # Show first 5
                print(f"        - {f.name} ({f.stat().st_size} bytes)")
            if len(files) > 5:
                print(f"        ... and {len(files) - 5} more")
        else:
            print(f"      (empty)")
    else:
        print(f"   ❌ {dir_path}/ does NOT exist")

print(f"\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
