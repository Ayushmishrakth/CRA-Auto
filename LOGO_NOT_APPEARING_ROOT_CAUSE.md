# Logo Not Appearing in DOCX - Root Cause Analysis & Fix

## 🔍 DIAGNOSIS

###Issue 1: Relative Path Problem (PRIMARY BUG)

**Location**: `CRA-Tool/app/api/v1/reports.py`, lines 132-140 and 198

The logo is saved with a **relative path**:
```python
logo_dir = Path("storage/logos")  # Relative path
logo_path = logo_dir / logo_filename  # Still relative
```

Then passed to EnhancedReportGenerator:
```python
gen = EnhancedReportGenerator(assessment_data, logo_path=str(logo_path) if logo_path else None)
# Passes: "storage/logos/user_id_uuid.png" (RELATIVE)
```

**Why This Breaks**:
- Logo is saved to `storage/logos/filename.png` relative to CRA-Tool working directory
- When async report generation runs in a thread, working directory might be different
- `add_picture()` in python-docx tries to find file at relative path, fails silently
- Logo never gets injected into document

**Solution**: Convert to absolute path before passing to EnhancedReportGenerator

### Issue 2: Missing Error Handling in logo_path Conversion

**Location**: `CRA-Tool/app/services/reporting/enhanced_report_generator.py`, line 260

```python
run.add_picture(logo_path_str, width=Inches(1.5))
```

If file doesn't exist, this silently fails without raising an exception. The code just logs and continues.

**Why This Is Bad**:
- User sees report generated successfully
- But logo is missing - confusing UX
- No error message to indicate what went wrong

**Solution**: Add try/except to validate file exists before attempting to add picture

---

## ✅ COMPLETE FIXES

### FIX 1: Convert Logo Path to Absolute

**File**: `CRA-Tool/app/api/v1/reports.py`, lines 178-199

**BEFORE (BROKEN)**:
```python
if logo_path:
    logo_path_str = str(logo_path)
    logger.info(f"[REPORT] Setting logo path: {logo_path_str}")
    logger.info(f"[REPORT] Logo file exists: {logo_path.exists()}")
    logger.info(f"[REPORT] Logo file size: {logo_path.stat().st_size if logo_path.exists() else 'N/A'}")
    assessment_data['logo_path'] = logo_path_str
else:
    logger.info(f"[REPORT] No logo provided (logo_path is None)")
    assessment_data['logo_path'] = None

# ... later at line 198 ...

def gen_report():
    gen = EnhancedReportGenerator(assessment_data, logo_path=str(logo_path) if logo_path else None)
    return gen.generate()
```

**AFTER (FIXED)**:
```python
if logo_path:
    # ✅ Convert to absolute path so it works regardless of working directory
    logo_path_absolute = logo_path.resolve()
    logo_path_str = str(logo_path_absolute)
    logger.info(f"[REPORT] Setting logo path: {logo_path_str}")
    logger.info(f"[REPORT] Logo file exists: {logo_path_absolute.exists()}")
    logger.info(f"[REPORT] Logo file size: {logo_path_absolute.stat().st_size if logo_path_absolute.exists() else 'N/A'}")
    assessment_data['logo_path'] = logo_path_str
    # ✅ Also set company details
    assessment_data['company_name'] = company_name or assessment_data.get('tenant_name')
    assessment_data['company_address'] = company_address
else:
    logger.info(f"[REPORT] No logo provided (logo_path is None)")
    assessment_data['logo_path'] = None

# ... later at line 198 ...

def gen_report():
    # ✅ Pass absolute path
    gen = EnhancedReportGenerator(
        assessment_data,
        logo_path=str(logo_path.resolve()) if logo_path else None
    )
    return gen.generate()
```

**Key Changes**:
- Line: `logo_path_absolute = logo_path.resolve()` - converts to absolute path
- Line: `str(logo_path_absolute)` - ensures absolute path is passed
- Added explicit setting of company details in assessment_data

---

### FIX 2: Add File Validation in Enhanced Report Generator

**File**: `CRA-Tool/app/services/reporting/enhanced_report_generator.py`, lines 256-265

**BEFORE (BROKEN)**:
```python
try:
    logger.info(f"[LOGO] Creating run and adding picture...")
    run = logo_para.add_run()
    run.add_picture(logo_path_str, width=Inches(1.5))
    logger.info(f"[LOGO] ✅ Logo added successfully!")
    self.doc.add_paragraph()  # Spacing after logo
except Exception as pic_err:
    logger.error(f"[LOGO] ❌ Picture insertion failed: {pic_err}", exc_info=True)
    # Don't add fallback text - just log and continue
```

**AFTER (FIXED)**:
```python
try:
    logger.info(f"[LOGO] Creating run and adding picture...")
    
    # ✅ Verify file exists before attempting to add
    if not os.path.exists(logo_path_str):
        logger.error(f"[LOGO] ❌ Logo file does not exist at: {logo_path_str}")
        logger.error(f"[LOGO] Absolute path resolved to: {os.path.abspath(logo_path_str)}")
    else:
        file_size = os.path.getsize(logo_path_str)
        logger.info(f"[LOGO] File verified: {file_size} bytes")
        
        run = logo_para.add_run()
        run.add_picture(logo_path_str, width=Inches(1.5))
        logger.info(f"[LOGO] ✅ Logo added successfully!")
        self.doc.add_paragraph()  # Spacing after logo
except Exception as pic_err:
    logger.error(f"[LOGO] ❌ Picture insertion failed: {pic_err}", exc_info=True)
    logger.error(f"[LOGO] Attempted path: {logo_path_str}")
    logger.error(f"[LOGO] Current working directory: {os.getcwd()}")
    # Don't add fallback text - just log and continue
```

**Key Changes**:
- Added file existence check before add_picture()
- More detailed error logging with working directory info
- Helps diagnose path issues

---

## 📊 WHY COMPANY NAME/ADDRESS ALSO MISSING

Looking at the code, company_name and company_address ARE being set in assessment_data (lines 166-176 in reports.py), and EnhancedReportGenerator reads them correctly:

```python
org_name = self.assessment.get('tenant_name', 'Organization')  # Line 291
company_address = self.assessment.get('company_address')  # Line 306
```

The issue is likely the same: if assessment_data isn't properly populated, these fields are missing.

**Double-Check**: Verify that company_name and company_address parameters are actually being passed from the frontend to the backend endpoint.

---

##🧪 TESTING THE FIXES

### Test 1: Logo Appears
1. Generate customized report with logo
2. Check DOCX - logo should appear on cover page
3. Check backend logs for: "[LOGO] ✅ Logo added successfully!"

### Test 2: Company Name Appears
1. Generate customized report with company name "Test Corp"
2. Check DOCX - "Test Corp" should appear on cover page with bold 20pt font
3. Check backend logs for: "[REPORT] Applying company name: Test Corp"

### Test 3: Company Address Appears
1. Generate customized report with address "123 Main St"
2. Check DOCX - address should appear on cover page centered below company name
3. Check backend logs for: "[REPORT] Applying address: 123 Main St"

### Test 4: Debug Path Issues (if tests fail)
1. Check backend logs for working directory and absolute paths
2. Look for: "[LOGO] File verified:" or "[LOGO] ❌ Logo file does not exist"
3. If path issue, verify storage/logos directory exists and has the file

---

## 🚀 DEPLOYMENT STEPS

1. **Apply Fix 1** in reports.py (lines 178-199)
   - Change relative path to absolute path
   - Ensure company details are in assessment_data

2. **Apply Fix 2** in enhanced_report_generator.py (lines 256-265)
   - Add file existence check
   - Better error logging

3. **Rebuild and test**
   ```bash
   cd CRA-Tool
   python -m uvicorn app.main:app --reload
   ```

4. **Generate report with logo** and verify it appears in DOCX

---

## ✅ SUMMARY

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Logo not appearing | Relative path breaks in async context | Convert to absolute path |
| No error feedback | Silent failure in add_picture() | Add file validation + better logging |
| Company details missing | May not be properly passed through | Ensure proper assignment in assessment_data |

