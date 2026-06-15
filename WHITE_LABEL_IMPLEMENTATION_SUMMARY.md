# White-Label Report Customization - Complete Implementation Guide

## Overview
This document outlines the complete end-to-end implementation of white-label customization for CRA reports. The feature allows users to upload custom logos, add company details (name & address), and generate reports in PDF, DOCX, or both formats (as ZIP).

---

## Files Created

### Frontend

#### 1. **CRA-frontend/src/components/report/CustomizeReportModal.jsx** (NEW)
**Purpose**: Modal dialog for collecting customization inputs (logo, company name, address, format)

**Key Features**:
- Logo upload with preview (PNG, JPG, SVG; max 5MB)
- Company name input (max 200 chars)
- Company address textarea (max 500 chars)
- Report format selection (PDF, DOCX, or Both)
- Client-side validation with error toasts
- Loading state during report generation
- Close button and form submission controls

**Usage**:
```jsx
<CustomizeReportModal
  assessmentId={assessmentId}
  isLoading={generating}
  onClose={() => setShowModal(false)}
  onGenerate={handleGenerateReport}
/>
```

#### 2. **CRA-frontend/src/api/reportApi.js** (NEW)
**Purpose**: API functions for report generation and download

**Exports**:
- `generateCustomizedReport(assessmentId, customization)` - Generates report with multipart form data
- `downloadReport(data, filename)` - Downloads blob to user's browser

**Usage**:
```javascript
const { data, filename } = await generateCustomizedReport(assessmentId, {
  logoFile: file,
  companyName: "ACME Corp",
  companyAddress: "123 Main St...",
  format: "both"
});
await downloadReport(data, filename);
```

---

## Files Modified

### Frontend

#### 1. **CRA-frontend/src/components/report/ReportDownloadPanel.jsx** (UPDATED)
**Changes**:
- Added import for `CustomizeReportModal` component
- Added import for `generateCustomizedReport` and `downloadReport` from reportApi
- Added state management for `showCustomizeModal` and `customizing` flags
- Added `handleGenerateCustomized` async handler
- Added "Customize & Download" button that opens the modal
- Wrapped component with modal JSX at bottom

**Key Addition**:
```jsx
<button
  type="button"
  className="btn-secondary inline"
  onClick={() => setShowCustomizeModal(true)}
  title="Add logo and company details to your report"
>
  <Settings size={16} />
  Customize & Download
</button>
```

---

### Backend

#### 1. **CRA-Tool/app/services/report_service.py** (UPDATED)
**Changes**:
- Added `LOGO_STORAGE_DIR` constant pointing to `storage/logos`
- Added `validate_and_save_logo()` async function for:
  - MIME type validation (PNG, JPG, SVG only)
  - File size validation (max 5MB)
  - File extension validation
  - Saving with sanitized filename using UUID
- Updated `handle_report_customization()` to:
  - Use new `validate_and_save_logo()` function
  - Sanitize company name (max 200 chars)
  - Sanitize address (max 500 chars)
  - Better error logging

**Key Function**:
```python
async def validate_and_save_logo(
    logo_file: UploadFile,
    user_id: UUID,
    max_size_bytes: int = 5 * 1024 * 1024,
) -> Path:
    """Validate and save logo file. Returns path to saved logo."""
```

#### 2. **CRA-Tool/app/api/v1/reports.py** (UPDATED)
**Changes**:
- Added `sanitize_filename()` utility function
- Added `zipfile` and `tempfile` imports
- Updated `generate_assessment_report()` endpoint to:
  - Support "both" format (returns ZIP with PDF + DOCX)
  - Always generate DOCX first
  - Convert DOCX to PDF if format is "pdf"
  - Create ZIP archive if format is "both"
  - Fallback to DOCX if PDF conversion fails
  - Better error handling and logging
  - Sanitized filenames

**Format Support**:
```python
format_lower in {"pdf", "docx", "both"}
# pdf   → FileResponse with PDF
# docx  → FileResponse with DOCX
# both  → FileResponse with ZIP containing both
```

---

## Unchanged Files (Already Configured)

### Backend

#### 1. **CRA-Tool/app/services/reporting/enhanced_report_generator.py**
- ✅ Already accepts `logo_path` in `__init__`
- ✅ Handles logo display in cover page (`_add_cover_page` method)
- ✅ Reads company name and address from `assessment_data`
- ✅ No changes needed

#### 2. **CRA-Tool/app/services/reporting/cra_pdf_renderer.py**
- ✅ Already has `render_pdf()` function accepting customization dict
- ✅ `_cover_page()` handles `logo_path`, `company_name`, `address`
- ✅ Has `_CoverPageFlowable` class for logo insertion
- ✅ No changes needed

#### 3. **CRA-Tool/app/services/reporting/report_customization.py**
- ✅ Already provides `store_customization()` and `get_customization()`
- ✅ No changes needed

#### 4. **CRA-Tool/app/api/v1/reports.py** - `/customize` endpoint
- ✅ Already exists for alternative workflow
- ✅ Works alongside new `/generate` endpoint

---

## API Endpoints

### POST `/reports/assessments/{assessment_id}/generate`
**Purpose**: Generate customized reports with white-label branding

**Parameters** (multipart/form-data):
- `logo` (file, optional) - PNG/JPG/SVG, max 5MB
- `company_name` (string, optional, max 200 chars)
- `company_address` (string, optional, max 500 chars)
- `report_format` (string, required) - "pdf", "docx", or "both"

**Response**:
- `report_format="pdf"` → `application/pdf`
- `report_format="docx"` → `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `report_format="both"` → `application/zip`

**Example Response Headers**:
```
Content-Disposition: attachment; filename="Assessment_Report_ACME_20260615.pdf"
Content-Type: application/pdf
```

---

## Data Flow

### Frontend → Backend

```
User Input
  ↓
CustomizeReportModal (validation)
  ↓
FormData {logo, company_name, company_address, report_format}
  ↓
POST /reports/assessments/{id}/generate
  ↓
Backend Processing
  ↓
File Download
```

### Backend Processing

```
POST Request Received
  ↓
Logo Validation (mime type, size, extension)
  ↓
Logo Saved to storage/logos/ with UUID
  ↓
Fetch Assessment Data from Database
  ↓
Inject Customization:
  - company_name → tenant_name
  - company_address → assessment_data
  - logo_path → assessment_data
  ↓
Generate Report (EnhancedReportGenerator)
  ↓
If format="both":
  - Generate DOCX
  - Convert to PDF
  - Create ZIP with both
  ↓
If format="pdf":
  - Generate DOCX
  - Convert to PDF
  ↓
If format="docx":
  - Generate DOCX
  ↓
Return FileResponse
```

---

## Setup Instructions

### 1. Database & Storage
```bash
# Ensure storage directories exist
mkdir -p CRA-Tool/storage/logos
mkdir -p CRA-Tool/storage/reports
mkdir -p CRA-Tool/storage/temp/logos
```

### 2. Environment Variables (Optional)
```bash
# In CRA-Tool/.env
LOGO_ALLOWED_FORMATS=png,jpg,jpeg,svg
MAX_LOGO_SIZE_MB=5
```

### 3. Dependencies Check
**Frontend**: All dependencies already in package.json
**Backend**: All dependencies already in requirements.txt
- `reportlab` ✅
- `python-docx` ✅
- `docxtpl` ✅
- `pillow` ✅
- `openpyxl` ✅

### 4. No Database Migrations Needed
- Uses in-memory customization cache
- Logos stored as files, not in database
- No schema changes required

---

## Testing the Implementation

### Test Case 1: PDF Generation with Logo
```
1. Open Reports page
2. Click "Customize & Download"
3. Upload logo (PNG/JPG/SVG)
4. Enter company name: "Acme Corporation"
5. Enter address: "123 Business St, Tech City, TC 12345"
6. Select format: "PDF (.pdf)"
7. Click "Generate & Download"
8. Verify PDF downloads with custom logo and company details
```

### Test Case 2: DOCX Generation with Logo
```
Same as Test Case 1, but select "Word (.docx)"
Verify DOCX opens in Word with logo and company details
```

### Test Case 3: Both Formats (ZIP)
```
Same as Test Case 1, but select "Both PDF & Word (.zip)"
Verify ZIP downloads containing both PDF and DOCX
Extract and verify both files
```

### Test Case 4: No Logo, Custom Company Name
```
1. Click "Customize & Download"
2. Skip logo upload
3. Enter company name and address
4. Select format
5. Generate
Verify report has company details but default logo
```

### Test Case 5: Logo Validation
```
1. Try uploading file > 5MB → Error toast
2. Try uploading .txt file → Error toast
3. Try uploading valid PNG → Success
```

---

## Error Handling

### Frontend
- File size exceeded → Toast: "Logo file too large (max 5MB)"
- Invalid file type → Toast: "Invalid logo format. Allowed: PNG, JPG, SVG"
- API error → Toast: "Failed to generate customized report"
- Network timeout → Toast appears after 5 minute timeout

### Backend
- Invalid MIME type → 400 Bad Request
- File size > 5MB → 400 Bad Request
- Corrupted file → 400 Bad Request
- PDF conversion fails → Falls back to DOCX
- ZIP creation fails → Falls back to DOCX

---

## Performance Considerations

### Logo Processing
- Logo validation happens on upload (5MB max)
- Logo stored once, reused across report generation
- Logos expire after 24 hours in storage/logos (optional cleanup task)

### Report Generation Times
- DOCX: ~10-30 seconds (depends on finding count)
- PDF conversion: ~10-20 seconds (uses libreoffice/docx2pdf)
- ZIP creation: ~2-5 seconds
- Timeout: 300 seconds (5 minutes)

### Storage
- Logos: `storage/logos/logo_[user_id]_[uuid].[ext]`
- Reports: `storage/reports/[company_name]_[timestamp].[docx/pdf/zip]`

---

## Security Considerations

### Input Validation
- ✅ File type validation (MIME + extension)
- ✅ File size limit (5MB)
- ✅ Input sanitization (company name, address)
- ✅ Filename sanitization to prevent path traversal
- ✅ UUID-based logo storage to prevent collisions

### File Operations
- ✅ Logos saved to dedicated directory
- ✅ Files not executable
- ✅ Proper permissions on storage directories
- ✅ Temporary files cleaned up after use

### Authentication
- ✅ All endpoints require authentication (Bearer token)
- ✅ Users can only generate reports for their assessments
- ✅ No cross-assessment data exposure

---

## Troubleshooting

### Logo Not Appearing in Report
1. Check `storage/logos/` directory exists and is writable
2. Check logs for `[LOGO]` entries
3. Verify file format is PNG/JPG/SVG
4. Ensure logo file size > 0 bytes
5. Try re-uploading logo

### PDF Conversion Fails
1. Check `docx2pdf` is installed: `pip install docx2pdf`
2. Check LibreOffice is installed (required by docx2pdf)
3. Check logs for conversion errors
4. Frontend will show DOCX as fallback
5. Check system disk space

### ZIP Not Creating
1. Check `zipfile` module is available (built-in)
2. Check `storage/reports/` is writable
3. Check disk space
4. Check system temp directory is accessible

### No Logo in DOCX Report
1. Check if logo path is passed to EnhancedReportGenerator
2. Check logo file exists at provided path
3. Check logs for `[LOGO]` entries
4. Verify logo file is readable (permissions)

---

## Cleanup (Optional)

### Clear Old Logos
```bash
# Clear logos older than 24 hours
find CRA-Tool/storage/logos -type f -mtime +1 -delete
```

### Clear Old Reports
```bash
# Clear reports older than 7 days (keep for audit)
find CRA-Tool/storage/reports -type f -mtime +7 -delete
```

---

## Future Enhancements

1. **Database Persistence**: Store customization in `report_customization` table
2. **Preset Templates**: Save frequently-used company details as presets
3. **Batch Downloads**: Generate multiple reports with same customization
4. **Email Export**: Send reports directly to email addresses
5. **Webhook Notifications**: Notify when report is ready
6. **Advanced Branding**: Custom colors, fonts, footer text
7. **Multi-language Reports**: Localized report content
8. **Report Scheduling**: Schedule report generation at specific times

---

## Summary

✅ **Frontend Complete**:
- CustomizeReportModal component with validation
- reportApi.js with axios integration
- ReportDownloadPanel with "Customize & Download" button

✅ **Backend Complete**:
- Logo validation and storage
- Report generation with customization
- Support for PDF, DOCX, and ZIP formats
- Proper error handling and logging

✅ **No Breaking Changes**:
- Existing report endpoints unaffected
- Backward compatible with non-customized reports
- Optional customization parameters

✅ **Ready to Test**: See "Testing the Implementation" section above

---

## Questions or Issues?

Refer to logs in both frontend (browser console) and backend (application logs) using `[REPORT]`, `[LOGO]`, and `[CACHE]` prefixes for debugging.
