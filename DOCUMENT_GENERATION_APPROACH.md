# Document Generation Approach - Word & PDF

## 📄 **WORD DOCUMENT GENERATION**

### Library Used
**`python-docx`** (Apache License 2.0)

### Main Function
**`render_word_report()`** — Located in `word_report_generator.py:99`

```python
def render_word_report(
    path: Path,
    assessment_data: dict,
    rows: list[dict],
    summary: dict,
    user: User | None = None,
    tenant: ConnectedTenant | None = None,
    output_root: Path | None = None,
) -> Path
```

### How It Works
1. **Template-based approach:** Loads a pre-existing DOCX template file
2. **Dynamic text replacement:** Fills in placeholders (customer name, dates, data)
3. **XML-level chart updates:** Modifies native Office charts stored in the DOCX ZIP archive
4. **Image insertion:** Uses `doc.add_picture()` to embed PNG/image bytes

### Key python-docx Imports
```python
from docx import Document              # Main Document class
from docx.enum.text import WD_BREAK   # Line breaks, page breaks
from docx.shared import Inches        # Width/height measurements
from docx.oxml.ns import qn           # XML qualified names
from docx.oxml import OxmlElement     # Direct XML manipulation
```

### Template Location
Default candidates (tries in order):
1. `out/sample.docx`
2. `app/services/reporting/templates/AAA Legal Process Copilot Readiness Assessment Report.docx`
3. `C:\Users\Admin\Downloads\AAA Legal Process Copilot Readiness Assessment Report (1).docx`
4. `C:\Users\Admin\Downloads\AAA Legal Process Copilot Readiness Assessment Report.docx`

### Output Format
- **Type:** DOCX (Office Open XML - essentially a ZIP archive)
- **Structure:** Contains:
  - `word/document.xml` — Main document content
  - `word/charts/chart*.xml` — Embedded charts
  - `word/media/image*.png` — Embedded images
  - `[Content_Types].xml` — File metadata
  - `_rels/.rels` — Relationships manifest

---

## 📊 **CHART HANDLING**

### Native Office Charts (Template-based)
**Function:** `_update_native_chart_caches()` — `word_report_generator.py:682`

Charts come from the DOCX template file and are **updated directly via XML manipulation**:
- Reads the DOCX as a ZIP archive
- Extracts `word/charts/chart*.xml` files
- Modifies cached data values (assessment results, counts)
- Re-zips with preserved metadata (compress_type, CRC32)

**Key Fix Applied:** Preserves `compress_type=item.compress_type` when writing back to ZIP

### Generated PNG Charts (Fallback)
**Function:** `_bar_chart_png()` — `word_report_generator.py:*`

Generates bar chart images from data using `matplotlib`/`PIL`:
- Creates PNG bytes from assessment data
- Embeds with `doc.add_picture(image, width=Inches(5.8))`

---

## 📷 **IMAGE/LOGO HANDLING**

### Storage Method
**Session-based temporary storage** in `report_customization.py`

```python
# In-memory cache (cleared after report generation)
_customization_cache: Dict[str, Dict[str, Any]] = {}

def store_customization(
    assessment_id: UUID,
    logo_path: Optional[str] = None,           # Path to uploaded logo file
    address: Optional[str] = None,              # Company address text
    company_name: Optional[str] = None,         # Company name text
    output_format: Optional[str] = None,        # "docx" or "both"
) -> None
```

### Current Logo Insertion Location
**File:** `word_report_generator.py` → Inside `_populate_cover_page()` or similar

**Current approach:** Logo is NOT currently inserted into the DOCX (customization data stored but not used in rendering yet)

**To add logo to document, would use:**
```python
from docx import Document
from pathlib import Path

# Read logo from stored path
logo_path = get_customization(assessment_id).get("logo_path")
if logo_path and Path(logo_path).exists():
    doc.add_picture(logo_path, width=Inches(1.5))  # Add to cover page
```

---

## 📑 **PDF GENERATION**

### Primary Method: Dual-Converter Strategy
**Location:** `cra_report_service.py:750` → `_convert_docx_to_pdf_async()`

**Approach:** **SEQUENTIAL FALLBACK** (tries converters in order)

```python
async def _convert_docx_to_pdf_async(
    docx_path: Path,
    pdf_path: Path,
) -> Path
```

### Converter Priority (Fallback Order)

#### 1️⃣ **`docx2pdf` Python Library** (Recommended, Fastest)
```python
from docx2pdf import convert
convert(str(docx_path), str(pdf_path))  # Runs in thread
```
- Requires: Microsoft Word installed on Windows
- Speed: ~5 seconds per report
- Quality: Native Word conversion (best quality)

#### 2️⃣ **LibreOffice Headless (Fallback)**
```bash
soffice --headless --convert-to pdf --outdir [dir] [docx_file]
```
- Requires: LibreOffice installed (`soffice` command available)
- Speed: ~15-30 seconds per report
- Quality: Good, compatible with all platforms

#### 3️⃣ **No Converter Available (Error)**
```python
raise RuntimeError(
    "PDF generation requires a reliable DOCX-to-PDF converter. "
    "Generate DOCX, or install/configure Microsoft Word docx2pdf or LibreOffice headless."
)
```

**If both fail:** Returns DOCX with `status: "partial"` and `pdf_conversion_error` field

---

## 🔄 **DATA FLOW DIAGRAM**

```
User clicks "Generate Report"
    ↓
API Endpoint: cra_report_service.generate_report_bundle()
    ↓
    ├─ Load assessment data from database
    │
    ├─ Get customization (logo_path, company_name, address)
    │  from session cache
    │
    ├─ DOCX Generation
    │  └─ render_word_report()
    │     ├─ Load template DOCX
    │     ├─ Replace text placeholders
    │     ├─ Insert logo image (if available)
    │     ├─ Add assessment data/tables/charts
    │     ├─ Update native chart caches
    │     └─ Save to storage/reports/{assessment_id}/
    │
    ├─ PDF Generation (Optional)
    │  └─ _convert_docx_to_pdf_async()
    │     ├─ Try: docx2pdf.convert()
    │     ├─ Fallback: libreoffice --headless
    │     └─ Save to storage/reports/{assessment_id}/
    │
    ├─ Save artifacts to database
    │
    └─ Return: {status, artifacts[], pdf_conversion_error}
        ↓
    Frontend displays download buttons
```

---

## 🛠️ **SUMMARY TABLE**

| Component | Technology | Library/Tool | Location |
|-----------|-----------|--------------|----------|
| **DOCX Generation** | Python | `python-docx` | `word_report_generator.py` |
| **DOCX Template** | XML/ZIP | Template file | `templates/*.docx` |
| **Chart Updates** | XML | `xml.etree.ElementTree` | `word_report_generator.py:682` |
| **Chart Images** | PNG | `matplotlib` / PIL | `word_report_generator.py:*` |
| **Logo Storage** | In-Memory Cache | Python dict | `report_customization.py` |
| **Logo Insertion** | Python | `doc.add_picture()` | `word_report_generator.py` (to be implemented) |
| **PDF Conversion** | External Tool | `docx2pdf` or `soffice` | `cra_report_service.py:750` |
| **Async Execution** | Python | `asyncio.to_thread()` | `cra_report_service.py` |

---

## 📝 **KEY FUNCTIONS SUMMARY**

### Word Generation
```python
# Main entry point
render_word_report(path, assessment_data, rows, summary, ...)

# Internal helpers
_populate_cover_page(doc, ...)          # First page with logo/address
_populate_content_pages(doc, ...)       # Main assessment data
_update_native_chart_caches(path, ...) # Update chart XML in ZIP
_bar_chart_png(values)                  # Generate chart images
_sanitize(text)                         # Clean XML-illegal characters
```

### PDF Conversion
```python
# Main entry point
_convert_docx_to_pdf_async(docx_path, pdf_path)

# Helpers
_is_valid_pdf(path)                     # Verify PDF integrity
```

### Customization
```python
store_customization(assessment_id, logo_path, address, company_name)
get_customization(assessment_id)
clear_customization(assessment_id)
```

