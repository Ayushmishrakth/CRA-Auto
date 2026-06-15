# Debugging: Logo Not Appearing in Report

**Issue:** Logo is NOT appearing on the cover page, even though company name IS appearing.

**Status:** ✅ Enhanced debugging added - Follow steps below to diagnose

---

## What Changed

### Enhanced Logging Added
I've added **much more detailed logging** to track exactly where the logo is getting lost:

**File:** `app/services/reporting/enhanced_report_generator.py`
- Constructor now logs: logo_path received, assessment data keys, company name, address
- _add_cover_page now logs: 
  - Whether logo_path is None
  - Whether logo_path is empty
  - File exists check
  - File size
  - Picture insertion attempts

**File:** `app/api/v1/reports.py`
- Logs logo file save with verification
- Logs logo_path being set in assessment_data
- Logs whether assessment_data contains logo_path

### New Diagnostic Script
**File:** `diagnose_report.py`

This script tests the entire process with a minimal test logo to isolate the issue.

---

## How to Debug (Step-by-Step)

### Option 1: Run Diagnostic Script (Recommended)

**Step 1: Restart Application**
```bash
Ctrl+C  # Stop current instance
python main.py  # Restart with enhanced logging
```

**Step 2: Run Diagnostic in Another Terminal**
```bash
cd "C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool"
python diagnose_report.py
```

This will:
- Create a minimal test PNG logo
- Generate a report with it
- Save the diagnostic report
- Show all [LOGO] messages in console
- Save detailed log to `report_diagnosis.log`

**Step 3: Check Output**
```
Look for these messages in console:

[INIT] EnhancedReportGenerator initialized
[INIT] logo_path received: storage/logos/test_logo_....png
[INIT] Assessment data keys: [... 'logo_path' ...]

[LOGO] _add_cover_page called with logo_path: storage/logos/...
[LOGO] Processing logo from: storage/logos/...
[LOGO] ✅ Logo added successfully!
```

**Step 4: Open Generated Report**
```
Location: C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool\storage\reports\diagnostic_report_*.docx

Check:
✅ Logo appears on cover page?
✅ Company name "TEST_COMPANY_NAME" appears?
✅ Address appears?
```

---

### Option 2: Monitor Live Report Generation

**Step 1: Start Application with Output**
```bash
cd "C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool"
python main.py 2>&1 | tee app.log
```

This saves all output to `app.log` while you see it on screen.

**Step 2: Open test_report_generation.html**
```
Open: C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool\test_report_generation.html
```

**Step 3: Generate a Report**
1. Select assessment
2. Upload logo
3. Enter company name
4. Click "Generate"

**Step 4: Watch Console**
Look for these messages:

```
[REPORT] Logo file exists: True
[REPORT] Logo file size: 12345 bytes
[REPORT] Logo file verification - exists: True, size: 12345

[INIT] logo_path received: storage/logos/user-id_uuid.png

[LOGO] _add_cover_page called with logo_path: storage/logos/...
[LOGO] Absolute path: C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool\storage\logos\...
[LOGO] Exists: True
[LOGO] File size: 12345 bytes
[LOGO] ✅ Logo added successfully!
```

**Step 5: If You See ❌ Errors**
```
[LOGO] ❌ File does not exist: ...
[LOGO] ❌ Picture insertion failed: ...
[LOGO] ❌ Unexpected error: ...
```

Then follow the troubleshooting section below.

---

## Troubleshooting

### Problem 1: Logo File Not Saved
**Log shows:**
```
[REPORT] Logo file verification - exists: False, size: 0
```

**Solution:**
1. Check permissions on storage/logos/ directory
2. Verify disk space available
3. Try uploading a different file
4. Check the file upload worked (check size in form)

### Problem 2: Logo_path is None
**Log shows:**
```
[INIT] logo_path received: None
[LOGO] logo_path is None: True
```

**Solution:**
1. Logo was uploaded but not passed to generator
2. Check form is actually uploading file
3. Check `[REPORT] Logo saved:` message appears
4. Verify `assessment_data['logo_path']` is being set

### Problem 3: File Exists But Can't Insert
**Log shows:**
```
[LOGO] Exists: True
[LOGO] File size: 12345 bytes
[LOGO] ❌ Picture insertion failed: ...
```

**Solution:**
1. File may be corrupted - try different logo
2. Try PNG format specifically
3. Try smaller file (100-200 KB)
4. Check error message - may give clue about format issue

### Problem 4: Path Issues
**Log shows:**
```
[LOGO] Absolute path: C:\Users\Admin\Desktop\...
[LOGO] Exists: False
```

**Solution:**
1. Check file actually exists in storage/logos/
2. Try absolute path vs relative path
3. Check Windows path vs forward slash issues
4. Try listing storage/logs/ contents

---

## What to Check in App Logs

When you generate a report, search the logs for these patterns:

### ✅ Everything Working
```
[REPORT] Logo file exists: True
[REPORT] Logo file size: [positive number]
[INIT] logo_path received: storage/logos/...
[LOGO] Processing logo from: storage/logos/...
[LOGO] ✅ Logo added successfully!
```

### ❌ Logo Not Received
```
[INIT] logo_path received: None
```
**Fix:** Check upload form, verify file was selected

### ❌ Logo File Doesn't Exist
```
[LOGO] Exists: False
[LOGO] ❌ File does not exist: storage/logos/...
```
**Fix:** Check storage/logos/ directory, verify file permissions

### ❌ Picture Insertion Fails
```
[LOGO] ❌ Picture insertion failed: [error message]
```
**Fix:** Try different logo file format, check file isn't corrupted

---

## File Locations to Check

After generating a report with logo:

```bash
# Check if logo was saved
ls -la storage/logos/

# Output should show:
# user-id_uuid.png (size: 100-500KB)
# user-id_uuid.jpg
# etc

# Check if report was generated
ls -la storage/reports/

# Output should show:
# report_*.docx (size: 2-3MB)
```

---

## Next Steps

1. **Run diagnostic script** first - it will show if the core logic works
2. **If diagnostic works but test form doesn't:** Issue is in form/API integration
3. **If diagnostic fails:** Issue is in report generator itself
4. **Check app logs** for [LOGO] messages - they'll tell you exactly what went wrong

---

## Quick Test Command (cURL)

If you want to test the API directly without the form:

```bash
# Replace with real values
ASSESSMENT_ID="your-assessment-uuid"
TOKEN="your-auth-token"
LOGO_FILE="path/to/logo.png"

curl -X POST "http://localhost:3000/api/v1/reports/assessments/$ASSESSMENT_ID/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -F "company_name=TEST_COMPANY" \
  -F "company_address=123 TEST ST" \
  -F "logo=@$LOGO_FILE" \
  -F "report_format=pdf" \
  -o report.pdf

# Then check app logs for [LOGO] messages
```

---

## Summary

**The logging I added will help us identify exactly where the logo gets lost:**

- ✅ Is it not being uploaded?
- ✅ Is it uploaded but path not passed?
- ✅ Is path passed but file doesn't exist?
- ✅ Does file exist but insertion fails?

Run the diagnostic script and share what you see in the [LOGO] messages!
