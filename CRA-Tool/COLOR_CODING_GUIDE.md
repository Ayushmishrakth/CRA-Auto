# Report Color Coding - Severity & Pillar Colors

**Status:** ✅ Added  
**Date:** 2026-06-12  
**Enhancement:** Color-coded tables for better readability and visual hierarchy

---

## Color Scheme

### Severity Column Colors

| Severity | Color | Hex Code | Usage |
|----------|-------|----------|-------|
| Critical | Red | #DC2626 | ⚠️ Requires immediate attention |
| High | Orange | #EA580C | ⚠️ High priority remediation |
| Medium | Yellow | #D97706 | ⚠️ Medium priority remediation |
| Low | Light Green | #65A30D | ✓ Low priority items |
| Informational | Blue | #2563EB | ℹ️ Informational only |

### Pillar Column Colors

| Pillar | Background Color | Usage |
|--------|------------------|-------|
| Security | Light Red (#FFE6E6) | Security-related findings |
| Governance | Light Blue (#E6F2FF) | Governance-related findings |
| Best Practices | Light Green (#E6F9E6) | Best practice findings |

### Status Column Colors

| Status | Background Color | Usage |
|--------|------------------|-------|
| Pass | Green (#90EE90) | ✓ Requirement met |
| Fail | Light Red (#FFB6C6) | ✗ Requirement not met |

---

## Visual Examples

### Table Header
- **Background:** Dark Blue (#003366)
- **Text:** White, Bold
- Columns: S. No | Parameter | CRA Pillar | Finding | Severity

### Sample Table Row
```
01 | Custom Banned Password List | Security      | Fail  | Critical
                                   (Light Red)    (Red)   (Dark Red)
```

### Color Meanings

🔴 **Critical (Red #DC2626)**
- Immediate action required
- High security/compliance risk
- Example: Audit Logs Disabled, DLP Rules not configured

🟠 **High (Orange #EA580C)**
- High priority remediation
- Significant security/governance risk
- Example: Third-party apps allowed, CAP policies disabled

🟡 **Medium (Yellow #D97706)**
- Medium priority remediation
- Moderate risk level
- Example: Guest invite settings, Auto-expiration policies

🟢 **Low (Green #65A30D)**
- Low priority items
- Minor security/governance impact
- Example: User information incomplete

🔵 **Informational (Blue #2563EB)**
- Informational only
- No action required
- Example: Active user counts, storage consumption

---

## Implementation Details

### Where Colors Appear

1. **Assessment Summary Tables Section**
   - One table per service (Entra ID, Exchange, Teams, etc.)
   - 5 columns: S. No | Parameter | CRA Pillar | Finding | Severity
   - All rows are color-coded by severity, pillar, and status

2. **Column Styling**
   - **S. No:** Regular (no color)
   - **Parameter:** Regular (no color)
   - **CRA Pillar:** Light background (Security=Red, Governance=Blue, Best Practices=Green)
   - **Finding:** Light background (Pass=Green, Fail=Red)
   - **Severity:** Distinct color for each severity level (Critical/High/Medium/Low/Info)

3. **Text Formatting**
   - All colored cells have **bold text** for better readability
   - High contrast between text and background
   - Professional appearance maintained

---

## How to Use Colors in Reports

### Quick Visual Scan
1. **Red cells** = Immediate attention needed (Critical findings)
2. **Orange cells** = High priority (High severity)
3. **Yellow cells** = Medium priority (Medium severity)
4. **Green cells** = Low priority or passing checks
5. **Blue cells** = Informational items

### By Pillar
- **Light Red column** = All Security findings
- **Light Blue column** = All Governance findings
- **Light Green column** = All Best Practice findings

### By Status
- **Green background** = Requirement is met (Pass)
- **Red background** = Requirement is not met (Fail)

---

## Benefits

✅ **Improved Readability**
- Color separates severity levels visually
- Quick identification of critical issues
- Professional appearance

✅ **Risk Prioritization**
- Red severity stands out immediately
- Helps stakeholders focus on high-risk items
- Supports decision-making

✅ **Better Information Hierarchy**
- Pillar colors group related findings
- Status colors show compliance status
- Severity colors indicate urgency

✅ **Compliance & Standards**
- Matches industry best practices
- Professional reporting standards
- Easy to understand for non-technical stakeholders

---

## Color Accessibility

### For Color-Blind Users
- **Red/Green:** Uses distinct hues (red #DC2626 vs green #65A30D)
- **Contrast:** All colors have sufficient contrast with text
- **Text Labels:** All colors have explicit labels (Critical, High, Medium, etc.)

### Print-Friendly
- Colors are print-safe
- Black & white printing still shows severity hierarchy through shades
- Professional appearance in both digital and print formats

---

## Examples in Generated Reports

### ENTRA ID Table
```
S. No | Parameter                              | CRA Pillar | Finding | Severity
01    | Custom Banned Password List            | Security   | Fail    | Critical
02    | Restricted Access to Microsoft Entra   | Security   | Fail    | Critical
03    | Emergency Access Accounts              | Security   | Fail    | Critical
...
```

### EXCHANGE ONLINE Table
```
S. No | Parameter                        | CRA Pillar | Finding | Severity
01    | Mailbox status (Active/Inactive) | Governance | Pass    | Critical
02    | External Storage providers       | Security   | Fail    | High
...
```

### MICROSOFT TEAMS Table
```
S. No | Parameter                    | CRA Pillar | Finding | Severity
01    | Copilot Integration Enabled  | Governance | Pass    | Critical
02    | Third Party apps allowed     | Governance | Fail    | High
...
```

---

## Customization Options

If you want to adjust colors in the future, edit `enhanced_report_generator.py`:

```python
# Severity colors (line ~38-44)
SEVERITY_COLORS = {
    'Critical': {'hex': 'DC2626', 'rgb': (220, 20, 60)},  # Change hex code
    'High': {'hex': 'EA580C', 'rgb': (255, 140, 0)},
    ...
}

# Pillar colors (line ~478-485)
if pillar == 'Security':
    shade_cell(row_cells[2], 'FFE6E6')  # Change hex code
elif pillar == 'Governance':
    shade_cell(row_cells[2], 'E6F2FF')  # Change hex code
...

# Status colors (line ~489-495)
if status == 'Pass':
    shade_cell(row_cells[3], '90EE90')  # Change hex code
elif status == 'Fail':
    shade_cell(row_cells[3], 'FFB6C6')  # Change hex code
```

---

## Testing

The color coding is now active in all generated reports:

1. **Download a Report**
   - Go to assessment in UI
   - Click "Download PDF" or "Download DOCX"
   - Open the generated report

2. **Check Tables**
   - Look at "Assessment Summary Tables" section
   - Each service has a colored table
   - Severity, pillar, and status columns are color-coded

3. **Verify Colors**
   - Critical findings should have red background
   - Security pillar should have light red background
   - Passed checks should have green background
   - Informational items should have blue background

---

**Status:** ✅ Color coding fully implemented and ready for use

