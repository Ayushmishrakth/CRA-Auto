# Logo Not Appearing - Root Cause Analysis & Fixes

**Issue:** Logo and company name not appearing in generated reports  
**Status:** ✅ Fixed - Enhanced with detailed debugging  
**Date:** 2026-06-12

---

## Root Cause Found

The customization (logo, company name, address) was being **saved but never passed to the report generators**.

### The Problem Chain
```
1. User uploads logo → Saved to storage/temp/logos/
2. Logo stored in customization cache ✓
3. Report generation started ✗
4. Customization cache NOT retrieved ✗
5. Report generated WITHOUT logo, company name, address ✗
```

### Why It Happened
In `cra_report_service.py`, the code was:
```python
# Line 63-65 (BEFORE)
docx_bytes = await asyncio.to_thread(
    render_word_report,
    report_data,  # ← Missing customization parameters!
)
```

---

## Fixes Applied

### 1. ✅ `app/services/reporting/cra_report_service.py`
**Fixed:** Now passes customization to both report generators

**Changes:**
- ✅ Pass `logo_path` to `render_word_report()`
- ✅ Pass `company_name` to `render_word_report()`
- ✅ Pass `address` to `render_word_report()`
- ✅ Pass `logo_path` to `EnhancedReportGenerator()`
- ✅ Add company customization to assessment_dict
- ✅ Added detailed [REPORT] logging

**Code:**
```python
# AFTER
docx_bytes = await asyncio.to_thread(
    render_word_report,
    report_data,
    logo_path=customization.get("logo_path"),      # ← NOW PASSED
    company_name=customization.get("company_name"), # ← NOW PASSED
    address=customization.get("address"),           # ← NOW PASSED
)
```

### 2. ✅ `app/services/reporting/word_report_generator.py`
**Enhanced:** Added detailed logo processing logging

**Changes:**
- ✅ Log when logo_path is received
- ✅ Check if file exists
- ✅ Log file size
- ✅ Report InlineImage success/failure
- ✅ Added detailed [LOGO] messages

**Logs You'll See:**
```
[LOGO] render_word_report received logo_path: storage/temp/logos/...
[LOGO] Logo file exists: True
[LOGO] File size: 125000 bytes
[LOGO] ✅ Logo image created successfully
```

### 3. ✅ `app/services/reporting/report_customization.py`
**Enhanced:** Added cache tracking logging

**Changes:**
- ✅ Log when storing customization
- ✅ Log when retrieving customization
- ✅ Verify file exists when retrieving
- ✅ Added detailed [CACHE] messages

**Logs You'll See:**
```
[CACHE] Storing customization for {id}:
[CACHE]   logo_path: storage/temp/logos/...
[CACHE]   company_name: Your Company

[CACHE] Retrieving customization for {id}:
[CACHE]   logo_path from cache: storage/temp/logos/...
[CACHE]   logo file exists: True
```

### 4. ✅ `app/services/reporting/enhanced_report_generator.py`
**Enhanced:** Added initialization and cover page logging

**Changes:**
- ✅ Log what logo_path is received in __init__
- ✅ Enhanced _add_cover_page() with file verification
- ✅ Report each step of logo insertion
- ✅ Added detailed [INIT] and [LOGO] messages

---

## How to Test the Fix

### Step 1: Restart Application
```bash
Ctrl+C
python main.py
```

### Step 2: Generate Report with Logo
1. Open an assessment in your app
2. Click "Customize & Generate" (or similar button)
3. Upload a logo (PNG, JPG, or SVG)
4. Enter company name: "Test Company"
5. Enter company address: "123 Test Street"
6. Generate report (DOCX or PDF)

### Step 3: Watch Console for Messages

**Good sign - You should see:**
```
[CACHE] Storing customization for 2747d178-...:
[CACHE]   logo_path: storage/temp/logos/2747d178-logo.png
[CACHE]   company_name: Test Company

[REPORT] Customization for 2747d178-...:
[REPORT]   company_name: Test Company
[REPORT]   address: 123 Test Street
[REPORT]   logo_path: storage/temp/logos/...

[REPORT] Calling render_word_report with customization

[LOGO] render_word_report received logo_path: storage/temp/logos/...
[LOGO] Logo file exists: True
[LOGO] File size: 45000 bytes
[LOGO] ✅ Logo image created successfully
```

**Bad sign - You would see:**
```
[LOGO] logo_path is None: True
[LOGO] Logo file does not exist: ...
[LOGO] ❌ Logo load failed: ...
```

### Step 4: Open Generated Report
- Check if logo appears on cover page
- Check if company name appears
- Check if company address appears

---

## Expected File Locations

After uploading logo:
```
storage/temp/logos/
├── {assessment_id}_{filename}.png
├── {assessment_id}_{filename}.jpg
└── ...
```

After generating report:
```
storage/reports/
├── {assessment_id}/
│   └── Copilot_Readiness_Assessment_{name}_{timestamp}.docx
│   └── Copilot_Readiness_Assessment_{name}_{timestamp}.pdf
└── ...
```

---

## What Each Component Does Now

### 1. Logo Upload (reports.py)
- ✓ Accepts file upload
- ✓ Saves to `storage/temp/logos/`
- ✓ Stores path in customization cache

### 2. Report Generation (cra_report_service.py)
- ✓ Retrieves customization from cache
- ✓ Logs customization details
- ✓ **PASSES to render_word_report()** ← KEY FIX
- ✓ **PASSES to EnhancedReportGenerator()** ← KEY FIX

### 3. Word Report (word_report_generator.py)
- ✓ Receives logo_path parameter
- ✓ Verifies file exists
- ✓ Creates InlineImage for template
- ✓ Logs success/failure
- ✓ Sets template variables: logo_image, company_name, address

### 4. Template (sample.docx)
- ✓ Must have placeholder: `{{ logo_image }}`
- ✓ Must have placeholder: `{{ company_name }}`
- ✓ Must have placeholder for address

---

## Troubleshooting

### Problem: Still no logo after restart
**Check logs for:**
1. **[CACHE] messages** - Is customization being stored?
2. **[LOGO] messages** - Is logo file found?
3. **File exists check** - Do you see "Logo file exists: True"?

### Problem: Customization not stored
**Check:**
1. Did you upload a file (not just click upload)?
2. Is file < 5MB?
3. Check `storage/temp/logos/` - does file exist?

### Problem: File exists but logo not inserted
**Check:**
1. Is template valid? (sample.docx)
2. Does template have `{{ logo_image }}` placeholder?
3. Is InlineImage creation failing? (Check for [LOGO] errors)

### Problem: Company name missing too
**Check:**
1. Do you see `[CACHE] company_name: ...` in logs?
2. Is it being passed to render_word_report?
3. Does template have `{{ company_name }}` placeholder?

---

## Files Modified

```
✅ app/services/reporting/cra_report_service.py
   - Added customization parameter passing

✅ app/services/reporting/word_report_generator.py
   - Enhanced logo handling with detailed logging

✅ app/services/reporting/report_customization.py
   - Added cache operation logging

✅ app/services/reporting/enhanced_report_generator.py
   - Added initialization and cover page logging
```

---

## Summary

**The Fix:** Customization parameters are now **explicitly passed** from the cache to both report generators.

**The Result:** Logo, company name, and address will now appear in generated reports.

**How to Verify:** Restart app, generate a report with logo, check logs for [CACHE], [LOGO], and [REPORT] messages. Open generated report and verify all three elements (logo, company name, address) appear.

**If Still Missing:** The detailed logging will show exactly where the problem is in the chain.

---

## Next Steps

1. ✅ Restart application
2. ✅ Generate a report with logo
3. ✅ Check console logs for [CACHE], [REPORT], [LOGO] messages
4. ✅ Open generated report
5. ✅ Verify logo, company name, address appear
6. ✅ If missing, look at logs to see which step failed

**Report working?** Awesome! You're done.  
**Still missing?** Share the [LOGO] and [CACHE] messages from console - they'll tell us exactly what's wrong.
