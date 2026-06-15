# White-Label Feature - REAL ROOT CAUSE & COMPLETE FIX

## 🔴 THE REAL BUG

**Location**: `CRA-frontend/src/api/assessmentApi.js`, lines 131-149

**The `customizeAssessmentReport` function has the BROKEN Content-Type header**

```javascript
// ❌ BROKEN FUNCTION - Line 131-149
export async function customizeAssessmentReport(assessmentId, { logoFile, address, companyName, outputFormat = "docx" }) {
  const formData = new FormData();
  if (logoFile) {
    formData.append("logo", logoFile);
  }
  if (address) {
    formData.append("address", address);
  }
  if (companyName) {
    formData.append("company_name", companyName);
  }
  formData.append("output_format", outputFormat);
  const response = await api.post(`/reports/assessments/${assessmentId}/customize`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",  // ❌ THIS IS THE BUG!
    },
  });
  return unwrapApiData(response);
}
```

---

## 🔍 WHY THIS IS BEING CALLED

Two different code paths exist:

### Path 1: ReportDownloadPanel (NEWER - Uses Fixed Code) ✅
- File: `CRA-frontend/src/components/report/ReportDownloadPanel.jsx`
- Uses: `generateCustomizedReport()` from `reportApi.js`
- Endpoint: POST `/reports/assessments/{id}/generate`
- Behavior: One-step flow - customize + generate + download in single call
- Status: ✅ WORKING (Content-Type header removed)

### Path 2: AssessmentReportPage & ResultsPage (OLDER - Uses Broken Code) ❌
- Files: 
  - `CRA-frontend/src/pages/AssessmentReportPage.jsx` (line 157)
  - `CRA-frontend/src/pages/ResultsPage.jsx`
- Uses: `customizeAssessmentReport()` from `assessmentApi.js`
- Endpoint: POST `/reports/assessments/{id}/customize`
- Behavior: Two-step flow - customize (step 1), then generate separately (step 2)
- Status: ❌ BROKEN (Content-Type header still has the bug!)

---

## 📊 THE TWO WORKFLOWS

### Workflow A: ReportDownloadPanel (Modern, Working)
```
User clicks "Customize & Download"
    ↓
Modal opens with logo/company fields
    ↓
User clicks "Generate & Download"
    ↓
Calls: generateCustomizedReport() from reportApi.js
    ↓
POST /api/v1/reports/assessments/{id}/generate
    ↓
Backend generates + returns blob file
    ↓
File downloads ✅
```

### Workflow B: AssessmentReportPage (Older, Broken)
```
User clicks "✓ Apply Customization"
    ↓
Calls: customizeAssessmentReport() from assessmentApi.js
    ↓
POST /api/v1/reports/assessments/{id}/customize
    (with broken Content-Type header ❌)
    ↓
Backend can't parse multipart data (422 error)
    ↓
"Network Error" toast appears ❌
    
User never gets to click "📄 Generate Report"
```

---

## ✅ THE COMPLETE FIX

### FIX 1: Update `customizeAssessmentReport` in assessmentApi.js

**File**: `CRA-frontend/src/api/assessmentApi.js` (line 131-149)

**BROKEN CODE**:
```javascript
export async function customizeAssessmentReport(assessmentId, { logoFile, address, companyName, outputFormat = "docx" }) {
  const formData = new FormData();
  if (logoFile) {
    formData.append("logo", logoFile);
  }
  if (address) {
    formData.append("address", address);
  }
  if (companyName) {
    formData.append("company_name", companyName);
  }
  formData.append("output_format", outputFormat);
  const response = await api.post(`/reports/assessments/${assessmentId}/customize`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",  // ❌ REMOVE THIS!
    },
  });
  return unwrapApiData(response);
}
```

**FIXED CODE**:
```javascript
export async function customizeAssessmentReport(assessmentId, { logoFile, address, companyName, outputFormat = "docx" }) {
  const formData = new FormData();
  if (logoFile) {
    formData.append("logo", logoFile);
  }
  if (address) {
    formData.append("address", address);
  }
  if (companyName) {
    formData.append("company_name", companyName);
  }
  formData.append("output_format", outputFormat);
  
  try {
    // ✅ FIX: Do NOT manually set Content-Type header
    // Axios will automatically set: "multipart/form-data; boundary=..."
    const response = await api.post(
      `/reports/assessments/${assessmentId}/customize`,
      formData
      // Remove the headers object entirely!
    );
    return unwrapApiData(response);
  } catch (error) {
    console.error("[CUSTOMIZE API] customizeAssessmentReport failed", {
      assessmentId,
      hasLogo: !!logoFile,
      errorMessage: error.message,
      errorStatus: error.response?.status,
      errorData: error.response?.data,
    });
    throw error;
  }
}
```

**Changes**:
- ✅ Removed the `headers` object with broken Content-Type
- ✅ Added try/catch with error logging
- ✅ Let Axios handle Content-Type automatically

---

## 🧪 HOW TO TEST THE FIX

### Test the Broken Workflow (Before Fix)
1. Go to AssessmentReportPage
2. Upload logo
3. Enter company name
4. Click "✓ Apply Customization"
5. Result: "Network Error" ❌

### Test the Fixed Workflow (After Fix)
1. Go to AssessmentReportPage
2. Upload logo
3. Enter company name
4. Click "✓ Apply Customization"
5. Result: "✓ Report customization saved! Ready to generate." ✅
6. Click "📄 Generate Report"
7. Result: Report downloads with custom logo ✅

---

## 📁 ALL FILES WITH ISSUES IDENTIFIED

### Affected Files:

1. **CRA-frontend/src/api/assessmentApi.js** - ❌ HAS BUG
   - Function: `customizeAssessmentReport()` at line 131-149
   - Issue: Broken Content-Type header
   - Impact: Can't customize reports from AssessmentReportPage
   - Fix: Remove header, add error logging

2. **CRA-frontend/src/api/reportApi.js** - ✅ ALREADY FIXED
   - Function: `generateCustomizedReport()` at line 7-75
   - Status: Working correctly
   - No action needed

3. **CRA-frontend/src/components/report/ReportDownloadPanel.jsx** - ✅ ALREADY FIXED
   - Uses: `generateCustomizedReport()` from reportApi.js
   - Status: Working correctly
   - No action needed

4. **CRA-frontend/src/pages/AssessmentReportPage.jsx** - ❌ USES BROKEN FUNCTION
   - Line 157: Calls `customizeAssessmentReport()`
   - Fix: Contained in assessmentApi.js fix above
   - No changes needed to this file

5. **CRA-frontend/src/pages/ResultsPage.jsx** - ❌ USES BROKEN FUNCTION
   - Uses: `customizeAssessmentReport()`
   - Fix: Contained in assessmentApi.js fix above
   - No changes needed to this file

6. **CRA-Tool/app/api/v1/reports.py** - ✅ WORKING CORRECTLY
   - Both endpoints exist and work:
     - POST `/assessments/{id}/customize` (stores customization)
     - POST `/assessments/{id}/generate` (generates + returns file)
   - No changes needed

---

## 🎯 SUMMARY

### Root Cause
The `customizeAssessmentReport()` function in `assessmentApi.js` still has the old broken Content-Type header that was supposed to be removed in the previous fix. This affects two legacy pages: AssessmentReportPage and ResultsPage.

### Solution
Fix ONE function in ONE file: Remove the broken header from `customizeAssessmentReport()` in `CRA-frontend/src/api/assessmentApi.js`

### Impact
- ✅ AssessmentReportPage customization will work
- ✅ ResultsPage customization will work
- ✅ ReportDownloadPanel already works
- ✅ All three customization flows will function

### Files to Fix
- **CRA-frontend/src/api/assessmentApi.js** (lines 131-149)

### Deployment Steps
1. Fix `customizeAssessmentReport()` - remove the `headers` object
2. Rebuild: `npm run build`
3. Deploy frontend
4. Test both customization flows

---

## ✅ NEXT: Apply the Fix

See the exact code changes needed in the sections above.
The fix is simple: remove 4 lines (the headers object).
