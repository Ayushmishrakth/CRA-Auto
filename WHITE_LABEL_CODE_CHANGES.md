# White-Label Implementation - Detailed Code Changes

## File-by-File Changes

---

## 1. NEW: CRA-frontend/src/components/report/CustomizeReportModal.jsx

**Lines of Code**: 263 lines

**Functionality**:
- Modal dialog component for report customization
- Logo upload with preview
- Company name and address input fields
- Report format selection (PDF/DOCX/Both)
- Client-side validation
- Error handling with toast messages

**Key Implementation**:
```jsx
const [formState, setFormState] = useState({
  logoFile: null,
  logoPreview: null,
  companyName: "",
  companyAddress: "",
  format: "pdf",
});

// Handle logo change with validation
const handleLogoChange = (e) => {
  const file = e.target.files?.[0];
  // Validate size and type
  // Create preview with FileReader
  setFormState(prev => ({...prev, logoFile, logoPreview}))
}

// Generate report on submit
const handleGenerate = async () => {
  await onGenerate({
    logoFile: formState.logoFile,
    companyName: formState.companyName.trim(),
    companyAddress: formState.companyAddress.trim(),
    format: formState.format,
  });
}
```

---

## 2. NEW: CRA-frontend/src/api/reportApi.js

**Lines of Code**: 70 lines

**Functionality**:
- API wrapper for report generation
- File download utility
- Multipart form data handling

**Key Implementation**:
```javascript
export async function generateCustomizedReport(assessmentId, {
  logoFile,
  companyName = "",
  companyAddress = "",
  format = "pdf",
}) {
  const formData = new FormData();
  if (logoFile) formData.append("logo", logoFile);
  formData.append("company_name", companyName);
  formData.append("company_address", companyAddress);
  formData.append("report_format", format);

  const response = await api.post(
    `/reports/assessments/${assessmentId}/generate`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
      responseType: "blob",
      timeout: 300000, // 5 minutes
    }
  );
  
  // Extract filename and return
  return { data: new Blob([response.data]), filename };
}

export async function downloadReport(data, filename) {
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
```

---

## 3. MODIFIED: CRA-frontend/src/components/report/ReportDownloadPanel.jsx

**Changes Summary**: Added customization support

**Changes**:
```diff
+ import { Settings } from "lucide-react";
+ import CustomizeReportModal from "./CustomizeReportModal";
+ import { generateCustomizedReport, downloadReport } from "../../api/reportApi";
+ import { useToast } from "../../context/ToastContext";

export default function ReportDownloadPanel({ assessmentId, report = {} }) {
+  const toast = useToast();
+  const [showCustomizeModal, setShowCustomizeModal] = useState(false);
+  const [customizing, setCustomizing] = useState(false);

+  const handleGenerateCustomized = async (customization) => {
+    setCustomizing(true);
+    try {
+      toast.info("Generating customized report...");
+      const { data, filename } = await generateCustomizedReport(assessmentId, customization);
+      await downloadReport(data, filename);
+      toast.success("Report generated and downloaded successfully");
+      setShowCustomizeModal(false);
+    } catch (error) {
+      toast.error(error.message || "Failed to generate customized report");
+    } finally {
+      setCustomizing(false);
+    }
+  };

   return (
     <>
       <section className="panel">
         ...existing code...
+        <button
+          type="button"
+          className="btn-secondary inline"
+          onClick={() => setShowCustomizeModal(true)}
+          title="Add logo and company details to your report"
+        >
+          <Settings size={16} />
+          Customize & Download
+        </button>
       </section>

+      {showCustomizeModal && (
+        <CustomizeReportModal
+          assessmentId={assessmentId}
+          isLoading={customizing}
+          onClose={() => setShowCustomizeModal(false)}
+          onGenerate={handleGenerateCustomized}
+        />
+      )}
     </>
   );
}
```

**Lines Added**: ~30 lines

---

## 4. MODIFIED: CRA-Tool/app/services/report_service.py

**Changes Summary**: Logo validation and storage

**New Constant**:
```python
LOGO_STORAGE_DIR = Path("storage/logos")
```

**New Function**:
```python
async def validate_and_save_logo(
    logo_file: UploadFile,
    user_id: UUID,
    max_size_bytes: int = 5 * 1024 * 1024,
) -> Path:
    """
    Validate and save logo file. Returns path to saved logo.
    
    Validates:
    - MIME type (PNG, JPG, SVG only)
    - File size (max 5MB)
    - File extension
    
    Saves with sanitized filename using UUID
    """
    if not logo_file or not logo_file.filename:
        return None

    # Validate file type
    allowed_mime_types = {"image/png", "image/jpeg", "image/svg+xml"}
    if logo_file.content_type not in allowed_mime_types:
        raise ValueError(f"Invalid logo format. Allowed: PNG, JPG, SVG")

    # Read and validate file size
    content = await logo_file.read()
    if len(content) > max_size_bytes:
        raise ValueError(f"Logo file too large")

    if len(content) == 0:
        raise ValueError("Logo file is empty")

    # Validate file extension
    allowed_extensions = {".png", ".jpg", ".jpeg", ".svg"}
    file_ext = Path(logo_file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise ValueError(f"Invalid file extension")

    # Save logo with sanitized filename
    LOGO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    import uuid as uuid_module
    safe_filename = f"logo_{user_id}_{uuid_module.uuid4()}{file_ext}"
    logo_path = LOGO_STORAGE_DIR / safe_filename

    with open(logo_path, "wb") as f:
        f.write(content)

    logger.info(f"Logo saved for user {user_id}: {logo_path} ({len(content)} bytes)")
    return logo_path
```

**Updated Function**:
```python
async def handle_report_customization(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: UUID,
    logo_file: UploadFile = None,
    address: str = None,
    company_name: str = None,
    output_format: str = "docx",
) -> dict:
    await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
    output_format = (output_format or "docx").strip().lower()
    if output_format not in {"docx", "pdf", "both"}:
        raise ValueError("Invalid report output format. Allowed: docx, pdf, both")

    logo_path = None
    try:
        if logo_file:
            logo_path = await validate_and_save_logo(logo_file, current_user.id)
    except ValueError as e:
        logger.error(f"Logo validation failed: {e}")
        raise

    # Sanitize company name and address
    company_name = (company_name or "").strip()[:200] if company_name else None
    address = (address or "").strip()[:500] if address else None

    # Store in-memory for use during report generation
    store_customization(assessment_id, str(logo_path) if logo_path else None, address, company_name, output_format)

    return {
        "assessment_id": str(assessment_id),
        "logo_path": str(logo_path) if logo_path else None,
        "address": address,
        "company_name": company_name,
        "output_format": output_format,
        "message": "Report customization saved successfully",
    }
```

**Lines Added**: ~45 lines

---

## 5. MODIFIED: CRA-Tool/app/api/v1/reports.py

**Changes Summary**: ZIP support, format handling, improved error handling

**New Imports**:
```python
import zipfile
import tempfile
```

**New Utility Function**:
```python
def sanitize_filename(name: str) -> str:
    """Sanitize filename by removing special characters."""
    import re
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', name)[:255]
```

**Updated Endpoint** - Key changes:
```python
@router.post("/assessments/{assessment_id}/generate")
async def generate_assessment_report(...):
    # ... existing logo validation ...

    # Step 5: Save and return - UPDATED
    Path("storage/reports").mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_company_name = sanitize_filename(company_name or "Assessment")

    format_lower = (report_format or "pdf").lower().strip()
    if format_lower not in {"pdf", "docx", "both"}:
        format_lower = "pdf"

    # Always generate DOCX first
    word_path = Path(f"storage/reports/{safe_company_name}_{timestamp}.docx")
    with open(word_path, "wb") as f:
        f.write(report_bytes.getvalue())

    if format_lower == "docx":
        return FileResponse(path=str(word_path), ...)

    elif format_lower == "pdf":
        # Convert DOCX to PDF
        pdf_path = Path(f"storage/reports/{safe_company_name}_{timestamp}.pdf")
        def convert_pdf():
            from docx2pdf import convert
            convert(str(word_path), str(pdf_path))
            return pdf_path
        
        try:
            pdf_file = await asyncio.to_thread(convert_pdf)
            return FileResponse(path=str(pdf_file), ...)
        except Exception as e:
            # Fallback to DOCX
            return FileResponse(path=str(word_path), ...)

    elif format_lower == "both":
        # Generate PDF and create ZIP
        pdf_path = Path(f"storage/reports/{safe_company_name}_{timestamp}.pdf")
        
        def convert_and_zip():
            try:
                from docx2pdf import convert
                convert(str(word_path), str(pdf_path))
            except Exception as e:
                logger.error(f"PDF conversion failed, ZIP will contain DOCX only: {e}")
                pdf_path = None

            # Create ZIP with both files
            zip_path = Path(f"storage/reports/{safe_company_name}_{timestamp}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(word_path, arcname=word_path.name)
                if pdf_path and pdf_path.exists():
                    zf.write(pdf_path, arcname=pdf_path.name)

            return zip_path

        try:
            zip_file = await asyncio.to_thread(convert_and_zip)
            return FileResponse(path=str(zip_file), media_type="application/zip")
        except Exception as e:
            # Fallback to DOCX
            return FileResponse(path=str(word_path), ...)
```

**Lines Added**: ~80 lines

---

## Summary of Changes

| File | Type | Lines Added | Status |
|------|------|------------|--------|
| CustomizeReportModal.jsx | NEW | 263 | ✅ Created |
| reportApi.js | NEW | 70 | ✅ Created |
| ReportDownloadPanel.jsx | MODIFIED | +30 | ✅ Updated |
| report_service.py | MODIFIED | +45 | ✅ Updated |
| reports.py | MODIFIED | +80 | ✅ Updated |
| **Total** | | **~160** | ✅ Complete |

**Unchanged Files** (already have required functionality):
- enhanced_report_generator.py ✅
- cra_pdf_renderer.py ✅
- report_customization.py ✅
- cra_docx_renderer.py ✅

---

## Key Features Implemented

### Frontend
1. ✅ Logo upload with preview
2. ✅ Company name and address input
3. ✅ Format selection (PDF/DOCX/Both)
4. ✅ Client-side validation
5. ✅ Error handling with toasts
6. ✅ Loading state during generation
7. ✅ File download trigger

### Backend
1. ✅ Logo validation (MIME, size, extension)
2. ✅ Logo storage with UUID naming
3. ✅ Input sanitization
4. ✅ DOCX generation with customization
5. ✅ PDF conversion from DOCX
6. ✅ ZIP creation for "both" format
7. ✅ Comprehensive error handling
8. ✅ Detailed logging with [REPORT] prefix

### Data Flow
1. ✅ FormData multipart submission
2. ✅ Logo validation on upload
3. ✅ Logo saved to storage/logos/
4. ✅ Customization injected into report data
5. ✅ Report generation with custom logo
6. ✅ Company details in cover page
7. ✅ File generation and download

---

## Testing Validation

### Frontend Tests
- [ ] Modal opens and closes correctly
- [ ] Logo preview works after upload
- [ ] Form validation shows error toasts
- [ ] File size validation works
- [ ] File type validation works
- [ ] Form submission calls API
- [ ] Loading state displays during generation
- [ ] File downloads automatically
- [ ] Success toast appears after download

### Backend Tests
- [ ] Logo MIME type validation works
- [ ] Logo file size validation works
- [ ] Logo saved with correct filename
- [ ] Company name sanitization works
- [ ] Address sanitization works
- [ ] DOCX generation includes logo
- [ ] DOCX generation includes company details
- [ ] PDF conversion works
- [ ] ZIP creation works with both files
- [ ] Fallback to DOCX if PDF conversion fails
- [ ] Error responses are meaningful

### Integration Tests
- [ ] End-to-end: Upload logo → Generate PDF
- [ ] End-to-end: Upload logo → Generate DOCX
- [ ] End-to-end: Upload logo → Generate ZIP
- [ ] End-to-end: No logo → Use defaults
- [ ] End-to-end: Large file → Get error
- [ ] End-to-end: Invalid type → Get error

---

## Deployment Checklist

- [ ] Frontend code compiles without errors
- [ ] Backend code passes linting
- [ ] All imports are correct
- [ ] Storage directories are created
- [ ] Dependencies are installed
- [ ] Environment variables are set (if needed)
- [ ] Database migrations are run (none needed)
- [ ] Application starts without errors
- [ ] Test Case 1-5 pass (see implementation guide)
- [ ] Logs show expected [REPORT] tags
- [ ] Files are downloadable and correct

---

## Rollback Instructions

If issues occur during deployment:

1. Revert frontend files:
   ```bash
   git checkout CRA-frontend/src/components/report/ReportDownloadPanel.jsx
   rm CRA-frontend/src/components/report/CustomizeReportModal.jsx
   rm CRA-frontend/src/api/reportApi.js
   npm run build
   ```

2. Revert backend files:
   ```bash
   git checkout CRA-Tool/app/services/report_service.py
   git checkout CRA-Tool/app/api/v1/reports.py
   ```

3. Restart application and test existing functionality

All changes are additive and backward compatible - rollback is safe.
