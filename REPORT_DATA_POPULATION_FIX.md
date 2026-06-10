# Report Data Population Issue - Complete Fix Guide

## 🔍 Problem Summary
Report generates but shows **empty/placeholder data** instead of real assessment results:
- Blank tables
- Generic/sample text
- No actual parameter data
- No findings or recommendations

---

## 🎯 Root Cause Analysis

The report generation has **3 potential failure points**:

### 1. **Template Loading Fails (Silent)**
- Template file not found → Empty Document created
- Document is valid but has no structure
- All updates fail silently
- Result: Blank DOCX

### 2. **Data Structure Mismatch**
- Expected: `parameter_rows` with fields like `title`, `status`, `severity`
- Actual: Missing fields or wrong format
- Functions can't find the data
- Result: Placeholders not replaced, tables stay empty

### 3. **Placeholder Text Doesn't Match**
- Template has "CUSTOMER_NAME" but code looks for "XYZ"
- Template has "Organization" but code looks for "Client"
- Placeholder replacement silently skips non-matching text
- Result: Tenant name stays as original placeholder

---

## ✅ Solution: 3-Step Fix

### STEP 1: Verify Template File Exists

**Problem Diagnosis:** Template file is missing or at wrong path

**Solution:**
Create a test script to check template location:

```bash
# Navigate to project
cd CRA-Auto/CRA-Tool

# Run Python to check template paths
python3 << 'EOF'
from pathlib import Path
from app.services.reporting.word_report_generator import REFERENCE_TEMPLATE_CANDIDATES

print("Checking template candidates:")
for i, candidate in enumerate(REFERENCE_TEMPLATE_CANDIDATES, 1):
    exists = candidate.exists()
    print(f"  {i}. {candidate}")
    print(f"     Status: {'✓ FOUND' if exists else '✗ MISSING'}")
    if exists:
        size = candidate.stat().st_size / 1024 / 1024
        print(f"     Size: {size:.2f} MB")
        break
EOF
```

**Expected Output:**
```
  1. out/sample.docx
     Status: ✓ FOUND
     Size: 2.45 MB
```

If **ALL say MISSING**:
- Download template from shared location
- Or use first available template as default
- See "SETUP: Create Minimal Template" below

---

### STEP 2: Verify Data Structure

**Problem Diagnosis:** Assessment data not being passed correctly

**Solution:**
Add validation to render_word_report:

```python
# In word_report_generator.py, after line 120

# Validate report data structure
if not rows:
    logger.warning(f"⚠️  No parameter rows found! This will produce empty tables.")
    logger.warning(f"    Sample row structure expected:")
    logger.warning(f"    {{'title': str, 'status': str, 'severity': str, 'description': str}}")
    
for i, row in enumerate(rows[:3]):  # Check first 3 rows
    logger.info(f"Sample row {i}: {list(row.keys())}")
```

**What to Look For in Logs:**
```
✓ GOOD:
  Sample row 0: ['title', 'status', 'severity', 'description', 'actual_result', 'expected_result']
  Parameters found: 65

✗ BAD:
  ⚠️  No parameter rows found!
  Parameters found: 0
```

**If You See ZERO parameters:**
1. Check that assessment has completed successfully
2. Verify findings were collected in database
3. Run: `SELECT COUNT(*) FROM assessment_finding WHERE assessment_id = '{id}'`

---

### STEP 3: Ensure Placeholders Match Template

**Problem Diagnosis:** Template text doesn't match hardcoded placeholder strings

**Solution:**
Edit `word_report_generator.py` line 130-145 to match YOUR template:

```python
# BEFORE (current hardcoded placeholders)
_replace_template_placeholders(
    doc,
    {
        "XYZ.": f"{tenant_name}.",
        "XYZ ": f"{tenant_name} ",
        ...
    },
)

# AFTER (check what's ACTUALLY in your template first)
# Step 1: Download your template DOCX
# Step 2: Open in Word, find placeholder text you want to replace
# Step 3: Add mappings for those exact strings

_replace_template_placeholders(
    doc,
    {
        # Match EXACTLY what's in your template
        "[COMPANY_NAME]": tenant_name,  # If template says [COMPANY_NAME]
        "[ASSESSMENT_DATE]": assessment_date,  # If template says [ASSESSMENT_DATE]
        "Customer Name Here": tenant_name,  # If template says "Customer Name Here"
        "XYZ": tenant_name,  # Original sample placeholder
        ...
    },
)
```

---

## 🔧 SETUP: Create Minimal Template (If Missing)

If you don't have a template file, here's how to create one:

```python
# File: scripts/create_minimal_template.py
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor

# Create new document
doc = Document()

# Add cover page
title = doc.add_heading('Copilot Readiness Assessment Report', level=0)
doc.add_paragraph()

# Add company name field
doc.add_heading('Customer Name', level=2)
doc.add_paragraph()

# Add date
doc.add_heading('Assessment Date: DD-MM-YYYY', level=2)
doc.add_paragraph()

# Add readiness section
doc.add_heading('Readiness Level: Not Ready', level=1)
doc.add_paragraph('Based on the findings, the Client\'s current readiness level for Copilot integration is assessed as:')
doc.add_paragraph()

# Add findings intro
doc.add_heading('Executive Summary', level=1)
doc.add_paragraph('The Copilot Readiness Assessment uncovered several configuration gaps and policy deficiencies that could impact the secure and compliant adoption of Microsoft Copilot. Each finding has been categorized by severity and mapped to specific areas of risk within the')
doc.add_paragraph()

# Add service tables (one per service)
for service in ['Entra ID', 'Exchange Online', 'Microsoft Purview', 'Microsoft Teams', 'OneDrive for Business', 'SharePoint Online']:
    doc.add_heading(f'{service} Findings', level=2)
    
    # Create table
    table = doc.add_table(rows=2, cols=5)
    table.style = 'Light Grid Accent 1'
    
    # Header
    headers = ['S. No', 'Parameter', 'CRA Pillar', 'Finding', 'Severity']
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
    
    # Sample data row
    for i, cell in enumerate(table.rows[1].cells):
        cell.text = f'Sample {i}'
    
    doc.add_paragraph()

# Add conclusion
doc.add_heading('Recommendations', level=1)
doc.add_paragraph('Significant remediation is required prior to enabling Copilot in the production environment.')

# Save
output_path = Path('app/services/reporting/templates/sample.docx')
output_path.parent.mkdir(parents=True, exist_ok=True)
doc.save(output_path)

print(f'✓ Template created: {output_path}')
```

**Run it:**
```bash
cd CRA-Auto/CRA-Tool
python3 ../../scripts/create_minimal_template.py
```

---

## 📊 Complete Data Validation Checklist

After making changes, verify with this test:

```python
# File: scripts/test_report_generation.py
import asyncio
from pathlib import Path
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup database
DATABASE_URL = "sqlite+aiosqlite:///app.db"  # or your actual URL
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_report_generation():
    async with async_session() as db:
        # Get latest completed assessment
        from sqlalchemy import select
        from app.db.models.assessment import Assessment
        
        result = await db.execute(
            select(Assessment)
            .where(Assessment.status == "completed")
            .order_by(Assessment.created_at.desc())
            .limit(1)
        )
        assessment = result.scalars().first()
        
        if not assessment:
            print("❌ No completed assessment found")
            return
        
        print(f"✓ Found assessment: {assessment.id}")
        
        # Build report data
        from app.services.reporting.cra_report_service import build_report_data
        from app.db.models.user import User
        
        # Get a user (adjust query as needed)
        user_result = await db.execute(select(User).limit(1))
        user = user_result.scalars().first()
        
        if not user:
            print("❌ No user found")
            return
        
        report_data = await build_report_data(db, current_user=user, assessment_id=assessment.id)
        
        # Check report data
        print(f"\n📊 Report Data Summary:")
        print(f"  Assessment: {report_data['assessment'].id}")
        print(f"  Tenant: {report_data['summary'].get('tenant_name', 'N/A')}")
        print(f"  Parameters: {len(report_data['parameter_rows'])}")
        print(f"  Summary:")
        for key in ['pass', 'fail', 'collection_error', 'licensing_required']:
            print(f"    - {key}: {report_data['summary'].get(key, 0)}")
        
        # Generate report
        from app.services.reporting.word_report_generator import render_word_report
        
        output_path = Path(f"test_output_{assessment.id}.docx")
        result = render_word_report(output_path, report_data)
        
        print(f"\n✓ Report generated: {output_path}")
        print(f"  Size: {output_path.stat().st_size / 1024:.2f} KB")

# Run
asyncio.run(test_report_generation())
```

---

## 📋 After Fixes: Testing Checklist

- [ ] Template file found (check logs)
- [ ] Parameter rows have data (check logs)
- [ ] All 3 placeholders from template are in code
- [ ] Report generates without errors
- [ ] Report file size > 100 KB (not empty)
- [ ] Open DOCX in Word - no corruption error
- [ ] Check: Tenant name replaced (not "XYZ")
- [ ] Check: Assessment date shown
- [ ] Check: Tables have data rows (not empty)
- [ ] Check: Charts show values
- [ ] Check: Findings section populated
- [ ] Check: Recommendations included

---

## 🚨 Common Issues & Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Blank tables, no data | Template not found OR rows empty | Step 1 or Step 2 |
| Tenant name shows "XYZ" or blank | Placeholder mismatch | Step 3 |
| Date shows "April 20, 2026" | Placeholder not in template | Step 3 |
| Tables have headers only | Data structure wrong | Step 2 |
| File size 0 bytes or < 50KB | Document creation failed | Check logs for errors |
| "File appears corrupted" | ZIP metadata issue | Use previous fix (CRITICAL) |

---

## 🔎 Debug: Read Logs

After implementing logging fix, check logs for:

```bash
# Good logs should show:
INFO: Generating report for assessment 123...
INFO:   Tenant: Contoso Inc
INFO:   Date: 2026-06-10
INFO:   Parameters found: 65
INFO:   Readiness: 72.3% (READY)
INFO: Placeholders replaced
INFO: Summary section updated
INFO: Service tables updated
INFO: Detailed blocks updated

# Bad logs show:
INFO:   Parameters found: 0        ← NO DATA!
WARNING: Chart cache update failed   ← Chart issue (OK, not critical)
ERROR: ...                          ← Real error
```

---

## Next Steps

1. **Verify template exists** - Run template check script
2. **Check logs** - Generate report and review logging output  
3. **Fix placeholders** - Add mappings for YOUR template's text
4. **Test generation** - Run test script to validate
5. **Open in Word** - Download and verify visually

Reply with:
1. Template check results (found or not?)
2. Log output showing parameters count
3. What happens when you open the generated DOCX?

