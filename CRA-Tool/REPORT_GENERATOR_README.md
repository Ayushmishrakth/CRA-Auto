# CRA Report Generator

This tool generates fully populated Word (.docx) CRA (Copilot Readiness Assessment) reports from a template and JSON data file.

## Quick Start

### Prerequisites

```bash
pip install pillow openpyxl lxml --break-system-packages
```

### Basic Usage

```bash
python3 generate_report.py data.json
```

This will:
1. Unpack the `sample.docx` template to XML
2. Update text placeholders with your data
3. Update all 12 charts with real data
4. Update embedded Excel files
5. Regenerate the pass/fail bar image
6. Repack everything into `output_report.docx`

## Input Data Format

Create a `data.json` file with the following structure:

```json
{
  "client_name": "WealthScape",
  "tenant_name": "WealthScape",
  "report_date": "2026-06-10",
  "readiness_level": "Not Ready",
  "pass_count": 7,
  "fail_count": 58,
  "gaps_count": 44,
  "total_params": 65,
  "pass_percentage": "10.66",
  "security_fail_pct": "68",
  "governance_fail_pct": "70",
  "bestpractice_fail_pct": "67",
  "eligible_users": "0",
  "total_users": "14",
  "onedrive_active_pct": "0",
  "teams_active_pct": "0",
  "outlook_active_pct": "75",
  "sharepoint_active_pct": "0",
  "pillars": {
    "Security": 34,
    "Best Practices": 51,
    "Governance": 15
  },
  "services_distribution": {
    "EntraID": 31,
    "ExchangeOnline": 11,
    "MicrosoftPurview": 14,
    "MicrosoftTeams": 23,
    "OneDrive": 6,
    "SharePointOnline": 14
  },
  "risk_counts": {
    "Critical": 18,
    "High": 17,
    "Medium": 18,
    "Low": 5,
    "Informational": 42
  },
  "licenses": [
    {"name": "E5", "count": 14}
  ],
  "user_info_fields": {
    "First Name": {"added": 0, "not_added": 1},
    "Last Name": {"added": 0, "not_added": 1},
    "Job Title": {"added": 0, "not_added": 1},
    "Department": {"added": 0, "not_added": 1},
    "Manager": {"added": 0, "not_added": 1},
    "City": {"added": 0, "not_added": 1},
    "Country": {"added": 0, "not_added": 1},
    "Office Location": {"added": 0, "not_added": 1}
  },
  "usage": {
    "SharePoint": {"active": 0, "inactive": 4},
    "OneDrive": {"active": 0, "inactive": 4},
    "Teams": {"active": 0, "inactive": 4},
    "Outlook": {"active": 3, "inactive": 1}
  },
  "service_pillar_matrix": {
    "fail": { ... },
    "pass": { ... }
  },
  "severity_pillar_matrix": {
    "Informational": { ... },
    "Low": { ... },
    "Medium": { ... },
    "High": { ... },
    "Critical": { ... }
  },
  "parameters": {
    "Custom Banned Password List": {
      "status": "Fail",
      "severity": "Critical",
      "description": "Enabled: No; Custom Word Count: 0; Configured: No"
    }
  }
}
```

Use `data_sample.json` as a template.

## What Gets Updated

### Text Placeholders
- Client name (appears in multiple places and formats)
- Report date
- Readiness level and gap counts
- Pass/fail percentages
- Pillar and service statistics
- User and service usage percentages

### Charts (12 total)
1. **3 Pillars of CRA** (pie chart)
2. **M365 Services** (pie chart)
3. **Risk-wise Parameters** (pie chart)
4. **Pass/Fail Bar** (horizontal bar)
5. **Executive Summary - M365 Services and 3 Pillars** (grouped bar)
6. **Executive Summary - Severity and 3 Pillars** (grouped bar)
7. **Licenses Assigned Data** (pie chart)
8. **User Information Details** (bar chart)
9. **SharePoint Usage** (doughnut)
10. **OneDrive Usage** (doughnut)
11. **Teams Usage** (doughnut)
12. **Outlook Usage** (doughnut)

### Images
- Pass/fail bar (`image12.png`) — regenerated based on data
- All gauge images remain static (pre-rendered)

### Embedded Excel
- Updates all linked Excel worksheets with matching chart data

### Per-Parameter Data
- Parameter descriptions
- Pass/Fail indicators (color-coded tables)
- Risk severity gauges

## Output Files

- **output_report.docx** — The generated report

The file is validated before completion and ready to open in Microsoft Word.

## Troubleshooting

### "Template unpacked" but script fails
- Ensure `sample.docx` exists in the same directory
- Check that all required dependencies are installed

### "XML validation error"
- This indicates malformed XML after updates
- Check your JSON data for special characters that might break XML

### Charts don't update
- Verify the chart files exist in `word/charts/`
- Ensure your JSON keys match the expected names exactly

### Excel files not updating
- The `embeddings` directory might not exist in your template
- Charts may not have linked Excel worksheets

## Files

- `generate_report.py` — Main script
- `scripts/office/unpack.py` — DOCX unpacker
- `scripts/office/pack.py` — DOCX repacker
- `scripts/office/validate.py` — Validation tool
- `data_sample.json` — Sample data file
- `sample.docx` — Template file (must exist)

## Advanced Usage

### Validate Output
```bash
python3 scripts/office/validate.py output_report.docx
```

### Custom Output Path
Edit `OUTPUT = "output_report.docx"` in `generate_report.py`

### Use Different Template
Edit `TEMPLATE = "sample.docx"` in `generate_report.py`

## Technical Details

The script uses the "unpack → edit XML → repack" approach:

1. **Unpack** — Extracts DOCX (ZIP) to directory
2. **Edit** — Modifies XML files in-place (document.xml, chart XMLs, etc.)
3. **Repack** — Recreates DOCX from modified files

This preserves all formatting, images, positioning, and advanced features that would be lost in library-based approaches.

---

**Version:** 1.0  
**Last Updated:** 2026-06-10
