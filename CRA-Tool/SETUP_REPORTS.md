# Complete Report Generation Setup

## What Was Fixed

### 1. ✅ Dependencies Installed
- python-docx
- docxtpl
- matplotlib
- docx2pdf

### 2. ✅ Directories Created
- `storage/reports/` - for saving generated reports
- `app/services/reporting/templates/` - for report templates

### 3. ✅ Enhanced Report Generator
- Created `app/services/reporting/enhanced_report_generator.py`
- Generates professional Word/PDF reports with:
  - Proper structure (TOC, sections, tables)
  - Charts with severity colors
  - Professional formatting

### 4. ✅ Fallback Logic
- If main report generation fails, automatically uses enhanced generator
- Better error handling with detailed logging
- Graceful degradation

### 5. ✅ Download Endpoint Fixed
- Updated `/assessments/{id}/report/download` endpoint
- Better error handling and logging
- Returns proper file format

---

## How to Complete Setup

### Step 1: Verify All Dependencies
```bash
pip install python-docx docxtpl matplotlib docx2pdf
```

### Step 2: Create Required Directories
```bash
mkdir -p storage/reports
mkdir -p app/services/reporting/templates
```

### Step 3: Restart Application
Stop and restart your CRA Tool application server for changes to take effect.

---

## Testing Report Generation

### Test 1: Local Report Generation (No Database)
```bash
python scripts/generate_enhanced_sample.py --output-dir ./reports
```

Should create:
- `CRA_Report_WealthScape_Professional.docx`
- `CRA_Report_WealthScape_Professional.pdf`

### Test 2: Full Stack Test
1. Go to an assessment in the CRA Tool UI
2. Click "Download PDF"
3. File should download

### Test 3: Debug Mode
If download fails:
```bash
curl -X POST http://localhost:3000/api/v1/assessments/{assessment-id}/report/generate-debug
```

This returns detailed error information.

---

## Report Features

### Included Sections
- ✅ Cover Page
- ✅ Table of Contents (auto-generated)
- ✅ Executive Summary
- ✅ Purpose
- ✅ Evaluation Summary
- ✅ 3 Pillars Framework
- ✅ Risk Category Breakdown
- ✅ Summary of Assessment
- ✅ Key Observations
- ✅ Detailed Assessment by Service
- ✅ Summary Tables
- ✅ Conclusion

### Charts with Colors
- **Severity Distribution** (Red=Critical, Orange=High, Yellow=Medium)
- **Pillar Breakdown** (Security, Governance, Best Practices)
- **Service Summary** (Pass/Fail by service)

### Professional Formatting
- Color-coded severity indicators in tables
- Proper heading hierarchy
- Professional fonts and spacing
- Page breaks between sections

---

## Troubleshooting

### Issue: "File not found"
**Check:**
- `storage/reports/` directory exists and is writable
- Templates exist in `app/services/reporting/templates/`

### Issue: "PDF conversion failed"
**Check:**
- docx2pdf is installed: `pip install docx2pdf`
- System has LibreOffice or similar (may be needed for some platforms)

### Issue: "Report generation timeout"
**Check:**
- Server logs for detailed error
- Try the debug endpoint: `POST /api/v1/assessments/{id}/report/generate-debug`

### Issue: Memory errors
- Large assessments may require more memory
- Try with a smaller assessment first

---

## File Locations

```
CRA-Tool/
├── app/
│   └── services/
│       └── reporting/
│           ├── enhanced_report_generator.py       (NEW)
│           ├── professional_report_generator.py   (NEW)
│           ├── assessment_report_service.py       (NEW)
│           ├── cra_report_service.py              (UPDATED)
│           └── templates/
│               ├── cra_template.docx
│               └── cra_template_new.docx
├── storage/
│   └── reports/                                   (NEW)
├── scripts/
│   ├── generate_enhanced_sample.py                (NEW)
│   ├── generate_real_report.py                    (NEW)
│   └── test_report_generation.py                  (NEW)
└── SETUP_REPORTS.md                              (THIS FILE)
```

---

## API Endpoints

### Generate and Download Report
```
GET /api/v1/assessments/{assessment_id}/report/download?report_type=pdf
GET /api/v1/assessments/{assessment_id}/report/download?report_type=docx
```

### Debug Report Generation
```
POST /api/v1/assessments/{assessment_id}/report/generate-debug
```

Returns detailed error info if generation fails.

---

## Next Steps

1. ✅ Install dependencies
2. ✅ Restart application
3. ✅ Test report download
4. ✅ Check server logs for any issues

**Everything should now work!** 🎉

If you encounter any issues, the debug endpoint will provide detailed error messages.
