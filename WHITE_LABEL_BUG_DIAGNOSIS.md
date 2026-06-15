# White-Label Customization - Bug Diagnosis & Fix

## 🔴 CRITICAL BUG IDENTIFIED

### Problem Summary
The frontend is getting "Network Error x15" when trying to generate customized reports because of a **multipart/form-data header issue in Axios**.

---

## 🔍 Root Cause Analysis

### The Bug: Incorrect Content-Type Header Handling

**Location**: `CRA-frontend/src/api/reportApi.js`, function `generateCustomizedReport()`

**The Problem**:
```javascript
// ❌ WRONG - This breaks Axios's automatic boundary handling
headers: {
  "Content-Type": "multipart/form-data",
},
```

**Why This Fails**:
1. When you manually set `Content-Type: multipart/form-data`, Axios doesn't add the **boundary marker** needed to separate form fields
2. Without the boundary, the backend's multipart parser can't understand the request
3. FastAPI `Form()` and `File()` parameters fail to parse the request body
4. Backend returns a 400/422 error, which Axios treats as a "Network Error"
5. Frontend retries 15 times (default retry logic), filling logs with network errors

**How It Should Work**:
```javascript
// ✅ CORRECT - Let Axios set Content-Type automatically
// When Axios detects FormData, it automatically sets:
// Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
// WITHOUT manually setting the header
```

---

## 📋 Files with Bugs

### 1. **CRA-frontend/src/api/reportApi.js** ❌ PRIMARY BUG
   - **Issue**: Manual `Content-Type: multipart/form-data` header
   - **Fix**: Remove the header - let Axios handle it
   - **Status**: NEEDS FIX

### 2. **CRA-frontend/src/api/reportApi.js** ❌ SECONDARY BUG
   - **Issue**: No error logging in catch block
   - **Fix**: Add console.error and structured error response
   - **Status**: NEEDS FIX

### 3. **CRA-Tool/app/api/v1/reports.py** ❌ LOGGING BUG
   - **Issue**: No try/except in endpoint to catch parse errors
   - **Fix**: Add try/except with detailed error logging
   - **Status**: NEEDS FIX

---

## ✅ THE FIX

### File 1: CRA-frontend/src/api/reportApi.js

**Current (Broken)**:
```javascript
export async function generateCustomizedReport(assessmentId, {
  logoFile,
  companyName = "",
  companyAddress = "",
  format = "pdf",
}) {
  const formData = new FormData();

  if (logoFile) {
    formData.append("logo", logoFile);
  }

  formData.append("company_name", companyName);
  formData.append("company_address", companyAddress);
  formData.append("report_format", format);

  const response = await api.post(
    `/reports/assessments/${assessmentId}/generate`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",  // ❌ THIS BREAKS IT
      },
      responseType: "blob",
      timeout: 300000,
    }
  );

  // ... rest of code
}
```

**Fixed**:
```javascript
export async function generateCustomizedReport(assessmentId, {
  logoFile,
  companyName = "",
  companyAddress = "",
  format = "pdf",
}) {
  const formData = new FormData();

  if (logoFile) {
    formData.append("logo", logoFile);
  }

  formData.append("company_name", companyName);
  formData.append("company_address", companyAddress);
  formData.append("report_format", format);

  try {
    const response = await api.post(
      `/reports/assessments/${assessmentId}/generate`,
      formData,
      {
        // ✅ DO NOT manually set Content-Type
        // Axios will automatically set:
        // "Content-Type": "multipart/form-data; boundary=..."
        responseType: "blob",
        timeout: 300000,
      }
    );

    // Extract filename from Content-Disposition header
    const disposition = response.headers?.["content-disposition"] || "";
    const match = disposition.match(/filename="?([^";\n]+)"?/i);

    let filename;
    const timestamp = new Date().toISOString().slice(0, 10);
    const safeName = (companyName || "assessment").replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_-]/g, "");

    if (format === "both") {
      filename = match?.[1] ?? `CRA_Report_${safeName}_${timestamp}.zip`;
    } else if (format === "pdf") {
      filename = match?.[1] ?? `CRA_Report_${safeName}_${timestamp}.pdf`;
    } else {
      filename = match?.[1] ?? `CRA_Report_${safeName}_${timestamp}.docx`;
    }

    return {
      data: new Blob([response.data], { type: response.headers["content-type"] || "application/octet-stream" }),
      filename,
    };
  } catch (error) {
    console.error("[REPORT API] generateCustomizedReport failed", {
      assessmentId,
      format,
      errorMessage: error.message,
      errorStatus: error.response?.status,
      errorData: error.response?.data,
      fullError: error,
    });
    throw new Error(
      error.response?.data?.detail ||
      error.message ||
      "Failed to generate customized report"
    );
  }
}

/**
 * Download a generated report file
 */
export async function downloadReport(data, filename) {
  if (typeof window === "undefined" || typeof document === "undefined") return;

  const url = URL.createObjectURL(data);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
```

---

### File 2: CRA-Tool/app/api/v1/reports.py

**Current** (line 63):
```python
async def generate_assessment_report(
    assessment_id: UUID,
    company_name: str = Form(default=""),
    company_address: str = Form(default=""),
    report_format: str = Form(default="pdf"),
    logo: UploadFile = File(default=None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Complete report generation with white-label customization.
    ...
    """
    try:
        # ... existing code ...
```

**Issues**: The endpoint doesn't have enough error handling and logging for multipart parse errors.

**Fixed** - Add enhanced error handling at the beginning:

```python
async def generate_assessment_report(
    assessment_id: UUID,
    company_name: str = Form(default=""),
    company_address: str = Form(default=""),
    report_format: str = Form(default="pdf"),
    logo: UploadFile = File(default=None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Complete report generation with white-label customization.

    Steps:
    1. Upload logo (optional)
    2. Enter company name and address
    3. Select report format (pdf, docx, or both)
    4. Generate and download
    """
    logger.info(
        "[REPORT] Starting generation for assessment %s, format=%s, company=%s",
        assessment_id,
        report_format,
        company_name or "(none)",
    )

    try:
        # Validate request parameters
        if not company_name and not company_address and not logo:
            logger.info("[REPORT] Request has no customization data")
        
        logger.info(
            "[REPORT] Parameters received: company_name=%s, company_address=%s, logo=%s",
            bool(company_name),
            bool(company_address),
            logo.filename if logo else "(none)",
        )

        # ... rest of existing try block ...

    except ValueError as e:
        logger.error("[REPORT] Validation error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[REPORT] Unexpected error during generation: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(exc)}"
        )
```

---

## 🔧 Implementation Steps

### Step 1: Fix reportApi.js
```bash
# Edit the file
nano CRA-frontend/src/api/reportApi.js
# Remove the line: "Content-Type": "multipart/form-data",
# Add error logging in catch block
```

### Step 2: Test the Fix
```bash
cd CRA-frontend
npm run build
# Restart frontend server
```

### Step 3: Verify Backend Logging
```bash
# Start backend with logging
python -m uvicorn app.main:app --reload
# Look for [REPORT] tagged logs when testing
```

---

## 🧪 How to Test the Fix

### Test 1: Logo Upload
1. Open Reports page
2. Click "Customize & Download"
3. Upload PNG/JPG/SVG logo (valid file)
4. Enter company name: "Test Corp"
5. Select "PDF (.pdf)"
6. Click "Generate & Download"
7. **Expected**: PDF downloads with custom logo, no Network Error

### Test 2: Check Browser Console
1. Open Developer Tools (F12)
2. Click "Customize & Download"
3. Generate report
4. **Expected**: 
   - No errors in console
   - Success logs visible
   - File downloads automatically

### Test 3: Check Backend Logs
1. Run backend with logging: `python -m uvicorn app.main:app --reload`
2. Generate customized report from frontend
3. **Expected in logs**:
   ```
   [REPORT] Starting generation for assessment {id}, format=pdf, company=Test Corp
   [REPORT] Parameters received: company_name=True, company_address=False, logo=True
   [REPORT] Logo saved: storage/logos/... ({size} bytes)
   [REPORT] Report generated: {size} bytes
   ```

### Test 4: Check Network Tab
1. Open Developer Tools → Network tab
2. Click "Customize & Download" and generate
3. **Expected**:
   - POST request to `/reports/assessments/{id}/generate` returns 200
   - Request shows `Content-Type: multipart/form-data; boundary=...`
   - Response has blob data
   - No retries (x1 request, not x15)

---

## 📊 Before vs After

### Before (Broken)
```
Frontend: POST /reports/assessments/{id}/generate
         Headers: Content-Type: multipart/form-data (no boundary)
         Body: [raw data without boundary markers]
         
Backend: FastAPI fails to parse Form/File fields
         Returns: 422 Unprocessable Entity or 400 Bad Request
         
Frontend: Gets error, retries 15 times
         Shows: "Network Error x15"
         
User: Report never generates, frustrated
```

### After (Fixed)
```
Frontend: POST /reports/assessments/{id}/generate
         Headers: Content-Type: multipart/form-data; boundary=----WebKit...
         Body: [proper multipart with boundaries]
         
Backend: FastAPI parses Form/File fields correctly
         Generates report
         Returns: 200 with PDF/DOCX/ZIP blob
         
Frontend: Downloads file successfully
         Shows: Success toast
         
User: Report downloads, happy!
```

---

## 🔐 Verification Checklist

- [ ] Removed manual `"Content-Type": "multipart/form-data"` header from reportApi.js
- [ ] Added try/catch with error logging in reportApi.js
- [ ] Frontend builds without errors
- [ ] Backend starts without errors
- [ ] Can upload logo without Network Error
- [ ] Report generates and downloads
- [ ] Browser console shows no errors
- [ ] Backend logs show [REPORT] tags
- [ ] File has correct company name and logo
- [ ] Works for PDF, DOCX, and ZIP formats

---

## 📝 Summary

**Root Cause**: Manual Content-Type header breaks Axios's multipart/form-data boundary generation

**Solution**: Remove the manual header, let Axios handle it automatically

**Files to Fix**: 
1. `CRA-frontend/src/api/reportApi.js` - Remove header + add logging
2. `CRA-Tool/app/api/v1/reports.py` - Add error logging (optional but helpful)

**Expected Result**: Reports generate and download successfully without Network Errors

**Time to Fix**: ~5 minutes

