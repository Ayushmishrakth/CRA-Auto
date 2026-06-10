# ACTION PLAN: Fix Report Data Not Being Populated

## 🎯 Problem
Report is generated but contains **empty/placeholder data** instead of real assessment information.

## ⚡ Quick Fix (5 minutes)

### Step 1: Run Diagnostic
```bash
cd C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool
python3 ../../diagnostic_report_generation.py
```

This will tell you:
- ✓ Template file found or ✗ missing
- ✓ Report structure valid or ✗ wrong
- ✓ Data populated or ✗ not populated

### Step 2: Based on Diagnostic Output

**If you see: `✗ MISSING` (template not found)**
→ Go to "SETUP: Template File" section below

**If you see: `Parameters found: 0`**
→ Your assessment has no data. Complete an assessment first or check database.

**If you see: `Tenant name populated: ✗ NO`**
→ Go to "FIX: Placeholder Mapping" section below

---

## 📋 Detailed Fixes

### SETUP: Template File

**Problem:** Template DOCX file is missing

**Solution:**

1. **Check for existing template:**
   ```bash
   # Look for template files
   ls -la C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool\app\services\reporting\templates\
   ```

2. **If file exists:** Copy it to one of the expected locations:
   ```bash
   # Copy to out/ folder (easiest)
   cp "C:\Users\Admin\Downloads\AAA Legal Process Copilot Readiness Assessment Report.docx" \
      "C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\out\sample.docx"
   ```

3. **If file doesn't exist:** Create minimal template:
   ```bash
   cd C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool
   python3 << 'EOF'
   from pathlib import Path
   from docx import Document
   
   doc = Document()
   doc.add_heading('Copilot Readiness Assessment Report', 0)
   doc.add_heading('Customer Name', 2)
   doc.add_heading('Assessment Date: DD-MM-YYYY', 2)
   doc.add_heading('Readiness Level: Not Ready', 1)
   
   # Add table with sample headers
   for service in ['Entra ID', 'Exchange Online']:
       table = doc.add_table(rows=2, cols=5)
       headers = ['S. No', 'Parameter', 'CRA Pillar', 'Finding', 'Severity']
       for i, h in enumerate(headers):
           table.rows[0].cells[i].text = h
   
   # Create templates directory if needed
   Path("app/services/reporting/templates").mkdir(parents=True, exist_ok=True)
   
   # Save template
   output = Path("app/services/reporting/templates/sample.docx")
   doc.save(output)
   print(f"✓ Template created: {output}")
   EOF
   ```

---

### FIX: Placeholder Mapping

**Problem:** Your template has different placeholder text than the code expects

**Solution:**

1. **Open your template DOCX in Word**
   - Find the placeholder texts (like "XYZ", "Customer Name", "DD-MM-YYYY")
   - Write them down EXACTLY as they appear

2. **Update code with your placeholders:**
   - Open: `CRA-Tool/app/services/reporting/word_report_generator.py`
   - Find: Line 130 (in the `_replace_template_placeholders` function)
   - Update the dictionary to match your template:

   ```python
   # BEFORE (current)
   _replace_template_placeholders(
       doc,
       {
           "XYZ.": f"{tenant_name}.",
           "XYZ ": f"{tenant_name} ",
           "XYZ": tenant_name,
           ...
       },
   )

   # AFTER (example - match YOUR template)
   _replace_template_placeholders(
       doc,
       {
           "[ORGANIZATION_NAME]": tenant_name,      # If template has [ORGANIZATION_NAME]
           "[DATE]": assessment_date,                # If template has [DATE]
           "Customer Name": tenant_name,             # If template has "Customer Name"
           "DD-MM-YYYY": assessment_date,            # If template has "DD-MM-YYYY"
           # Keep these for backwards compatibility
           "XYZ": tenant_name,
           "April 20, 2026": assessment_date,
       },
   )
   ```

3. **Restart backend and test:**
   ```bash
   # Stop current backend (Ctrl+C)
   # Restart
   python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

---

## 🧪 Test After Fixes

### Quick Test
1. Go to: `http://localhost:3000/assessments/<id>/results`
2. Click: "Customize & Generate"
3. Select: "Word DOCX - recommended"
4. Click: "Apply & Generate"
5. Download the report
6. **Open in Word**

### What to Check
- [ ] No "corrupted file" error
- [ ] Tenant/company name is correct (not "XYZ")
- [ ] Date is current (not "April 20, 2026")
- [ ] Tables have data rows (not empty)
- [ ] Assessment findings are listed
- [ ] No blank pages

---

## 🔍 Troubleshooting

### Still Seeing Empty Data?

1. **Check backend logs:**
   ```
   INFO: Generating report for assessment ...
   INFO:   Parameters found: 65          ← Should be > 0
   INFO: Placeholders replaced
   INFO: Service tables updated
   ```

   - If "Parameters found: 0" → Your assessment has no data
   - If no logs → Report generation crashed

2. **Check that assessment is completed:**
   - Go to: `http://localhost:3000/assessments`
   - Find your assessment
   - Status should be: "Completed" (not "In Progress" or "Error")

3. **Verify template was found:**
   - Run diagnostic script again
   - Should show: "✓ FOUND"

### Still Getting Corruption Error?

- Use the previous ZIP metadata fix (already implemented)
- Run: `python3 -m zipfile -l test_report.docx` to verify ZIP is valid

---

## 📞 Still Having Issues?

Provide:
1. **Diagnostic output** (from `diagnostic_report_generation.py`)
2. **Backend logs** (last 30 lines when generating report)
3. **Template file name** (what template are you using?)
4. **Screenshot** of generated DOCX opened in Word

Then I can provide targeted fix.

---

## ✅ Success Criteria

After fixes, you should see:

```
✓ Report generates in 30-45 seconds
✓ File downloads successfully
✓ Opens in Word without errors
✓ Shows tenant name (not "XYZ")
✓ Shows current date (not sample date)
✓ Tables have assessment data
✓ Charts show readiness scores
✓ Findings section populated
✓ Recommendations included
```

