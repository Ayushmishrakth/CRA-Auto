# Report Generation Test Plan

## Problem
Users could not open generated DOCX reports - Microsoft Word reported them as corrupted.

## Root Causes Identified & Fixed

### 1. **ZIP Metadata Loss During Chart Update** (CRITICAL)
   - **File:** `word_report_generator.py:697`
   - **Issue:** `zipfile.writestr(item, data)` didn't preserve `compress_type` from original
   - **Impact:** CRC32 mismatches → ZIP validation failures → "corrupted file" error
   - **Fix:** Added `compress_type=item.compress_type` parameter

### 2. **Chart Updates Failure Propagation** (IMPORTANT)
   - **File:** `word_report_generator.py:155-158`
   - **Issue:** If chart update failed, entire report generation failed
   - **Impact:** Even if charts weren't needed, one failure blocked the whole DOCX
   - **Fix:** Wrapped in try-except; logs warning but continues with valid DOCX

### 3. **Missing Charts Not Detected** (SAFETY)
   - **File:** `word_report_generator.py:690-693`
   - **Issue:** If template had no charts, chart update code still tried to repack ZIP
   - **Impact:** Unnecessary operations, potential corruption source
   - **Fix:** Check if charts exist in DOCX before attempting updates

### 4. **Individual Chart Failures Cascading** (ROBUSTNESS)
   - **File:** `word_report_generator.py:714-720`
   - **Issue:** If one chart's XML update failed, ZIP repack was partially done
   - **Impact:** Corrupted ZIP archive
   - **Fix:** Catch per-chart errors and skip that chart only

### 5. **Unstructured Error on PDF Conversion** (UX)
   - **File:** `cra_report_service.py:81-96`
   - **Issue:** If PDF conversion failed, entire endpoint returned 500
   - **Impact:** User sees "Network Error", unclear what went wrong
   - **Fix:** Catch PDF errors, return DOCX anyway with `status: "partial"`

## Test Scenarios

### ✅ Scenario 1: DOCX-Only Generation (RECOMMENDED)
```
Steps:
1. Start assessment → Complete assessment
2. Click "Customize & Generate"
3. Select "Word DOCX - recommended"
4. Click "Generate Report"

Expected:
- Report generates successfully
- Download DOCX button appears
- File is < 2MB and valid ZIP
- Microsoft Word opens it without errors
- All placeholders replaced (client name, date)
- Template content is present
```

### ✅ Scenario 2: DOCX Generation Without Charts
```
Steps:
1. Same as Scenario 1
2. Check generated DOCX

Expected:
- If template has no charts, chart update is skipped (no errors logged)
- DOCX is still valid and readable
- No corruption errors
```

### ⚠️ Scenario 3: DOCX + PDF (Graceful Failure)
```
Steps:
1. Start assessment → Complete assessment
2. Click "Customize & Generate"
3. Select "Word DOCX and PDF"
4. Click "Generate Report"

Expected (if PDF converter unavailable):
- Toast warning: "DOCX is ready. PDF conversion failed."
- DOCX download button available
- Report marked as "partial" status
- No 500 error from backend
- User can still download DOCX
```

## Validation Commands

### Test DOCX Generation Locally
```bash
cd CRA-Auto/CRA-Tool

# Generate a test report
python3 -c "
from app.services.reporting.word_report_generator import render_word_report
from pathlib import Path

# Mock data
mock_data = {
    'assessment': type('Assessment', (), {'id': '123', 'tenant_id': 'test'}),
    'summary': {
        'customer_name': 'Test Org',
        'tenant_name': 'test.onmicrosoft.com',
    },
    'parameter_rows': [],
    'metadata': {}
}

# Generate
output = Path('test_output.docx')
result = render_word_report(output, mock_data)
print(f'✓ Generated: {result}')
print(f'  Size: {output.stat().st_size} bytes')
"

# Validate ZIP structure
python3 -c "
import zipfile
with zipfile.ZipFile('test_output.docx') as z:
    print(f'✓ Valid ZIP with {len(z.namelist())} entries')
    for required in ('word/document.xml', '[Content_Types].xml'):
        assert required in z.namelist(), f'Missing {required}'
    print('✓ All required parts present')
"

# Try to open in Word (Windows)
python3 -c "
from pathlib import Path
import os
if os.name == 'nt':
    os.system('start test_output.docx')
    print('✓ Opened in Word')
"
```

### Test Via API
```bash
# Generate report
curl -X POST http://localhost:8000/api/v1/assessments/{assessment_id}/generate-report \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  ?report_type=docx

# Expected response
# {
#   "status": "success",
#   "data": {
#     "status": "generated",
#     "artifacts": [
#       {
#         "report_type": "docx",
#         "report_status": "generated",
#         "storage_path": "..."
#       }
#     ]
#   }
# }

# Download report
curl http://localhost:8000/api/v1/assessments/{assessment_id}/report/download \
  -H "Authorization: Bearer $TOKEN" \
  ?report_type=docx \
  --output report.docx

# Verify it can be opened
file report.docx  # Should be: MS Word 2007+
```

## Success Criteria

- [ ] DOCX files generate without errors
- [ ] Generated DOCX opens in Microsoft Word
- [ ] No "corrupted file" error from Word
- [ ] All text placeholders are replaced correctly
- [ ] Report contains expected sections
- [ ] File size is reasonable (> 100KB, < 5MB)
- [ ] If PDF conversion fails, DOCX still downloads
- [ ] Error messages are clear to users
- [ ] No unhandled 500 errors on report generation

## Regression Testing

Verify these still work:
- [ ] PDF generation (if converter available)
- [ ] Logo upload and customization
- [ ] Report download to browser
- [ ] Multi-tenant isolation (users see their own reports only)
- [ ] Historical reports still accessible

## Debug Commands

If reports still fail to open:

```bash
# Check file is valid ZIP
unzip -t report.docx  # Should list all files without errors

# Validate XML
python3 -c "
import zipfile
from xml.etree import ElementTree as ET
with zipfile.ZipFile('report.docx') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            try:
                ET.fromstring(z.read(name))
                print(f'✓ {name}')
            except ET.ParseError as e:
                print(f'✗ {name}: {e}')
"

# Check template location
python3 -c "
from pathlib import Path
from app.services.reporting.word_report_generator import _resolve_template_path
print('Template:', _resolve_template_path(None))
"
```

## Post-Fix Expectations

**Before Fix:**
- DOCX generated → User downloads → Word says "corrupted"
- PDF-only selection → Fails when PDF converter unavailable

**After Fix:**
- DOCX generated → User downloads → Word opens successfully
- "DOCX and PDF" selected → If PDF fails, DOCX still works
- Error messages guide users to working format

