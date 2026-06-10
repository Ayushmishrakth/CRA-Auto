# Quick Test Steps - Report Generation Fix

## ⏱️ Time Required: 5-10 minutes

## Step 1: Restart Backend (1 minute)

```bash
# Stop current backend if running
# Press Ctrl+C in the backend terminal

# Restart with the fixed code
cd CRA-Auto/CRA-Tool
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected: Server starts without errors

---

## Step 2: Verify Frontend (1 minute)

```bash
# In another terminal, restart frontend (if running)
cd CRA-Auto/CRA-frontend
npm run dev
```

Expected: Frontend loads without errors at `http://localhost:3000`

---

## Step 3: Test Report Generation (5-10 minutes)

### Option A: If you have a completed assessment

1. Navigate to: `http://localhost:3000/assessments/<assessment_id>/results`
2. Click the **"Customize & Generate"** button (blue button in sidebar)
3. A modal should appear with:
   - Logo upload section
   - Company name input
   - Address input
   - Output format dropdown

4. **Select format:** "Word DOCX - recommended" (default)
5. **Click:** "Apply & Generate"
6. Wait for progress bar to complete (~30-45 seconds)
7. When done, click: **"Download DOCX"**

### Option B: If you don't have a completed assessment

1. Start a new assessment: `http://localhost:3000/assessments`
2. Wait for it to complete (takes ~2-5 minutes)
3. Then follow Option A steps 1-7

---

## Step 4: Verify DOCX Opens (2 minutes)

1. **Download completed?** Check your Downloads folder
2. **File looks good?** Should be named `CRA_Report_*.docx` (size ~500KB-2MB)
3. **Open in Word:**
   - Double-click the file
   - Or right-click → Open with → Microsoft Word

### ✅ SUCCESS:
- File opens in Word without any "corrupted" error
- You can see:
  - Client name (replaced from "XYZ")
  - Date (current date)
  - Assessment data
  - Charts and tables

### ❌ FAILURE (Still seeing "corrupted" error):
- Check backend logs for errors
- Try format: "Word DOCX only" instead of "DOCX and PDF"
- Let me know the exact error message

---

## Step 5: Test Error Handling (Optional, 2 minutes)

1. Go back to generate another report
2. **Select format:** "Word DOCX and PDF"
3. **Click:** "Apply & Generate"
4. If PDF converter is not available, you should see:

   **Toast message:** ⚠️ "DOCX report generated successfully. PDF conversion failed. You can download the DOCX report instead."

5. **Download DOCX** - should still work perfectly

---

## Expected Results Summary

### ✅ Working Correctly (After Fix)
```
User Action: Click "Customize & Generate" → Select DOCX → Download
Result: Opens in Word ✅ No corruption error ✅
Time: ~45 seconds ✅

User Action: Select "DOCX and PDF" → PDF converter unavailable
Result: DOCX downloads and works ✅ Clear error message ✅
PDF: Not available (expected) ✅
```

### ❌ Still Broken (Needs More Investigation)
```
User Action: Click "Customize & Generate" → Download DOCX
Result: Word says "file appears to be corrupted" ❌
Next: Check backend logs and share error message
```

---

## Backend Logs to Watch For

After clicking "Generate Report", check backend terminal for:

### ✅ GOOD (Expected)
```
INFO:     GET /api/v1/assessments/xxx/report HTTP/1.1
INFO:     POST /api/v1/reports/assessments/xxx/customize HTTP/1.1
INFO:     POST /api/v1/assessments/xxx/generate-report HTTP/1.1
```

No errors = Report generated successfully ✅

### ⚠️ WARNING (Non-critical)
```
WARNING: Chart cache update failed (report still usable): ...
```

This is OK - DOCX still works, just uses template charts instead of updated ones

### ❌ ERROR (Problem)
```
ERROR: RuntimeError: PDF generation requires...
```

This is expected if PDF converter not available. DOCX should still download.

---

## If Something Goes Wrong

### Problem: Report page shows "Generation failed"
**Solution:**
1. Check backend logs for error message
2. Try selecting "Word DOCX - recommended" format (not "both")
3. Clear browser cache: `Ctrl+Shift+Delete` and clear all

### Problem: Downloaded file is 0 bytes or corrupted
**Solution:**
1. Restart backend
2. Try again
3. Check `/storage/reports/<assessment_id>/` for file

### Problem: Frontend shows "Network Error"
**Solution:**
1. Check backend is running: `http://localhost:8000/health`
2. Check browser console for errors: `F12` → Console tab
3. Try refreshing page

---

## Success Criteria

- [x] Python syntax validation passed
- [ ] Backend starts without errors
- [ ] Frontend loads at localhost:3000  
- [ ] Assessment available in results page
- [ ] "Customize & Generate" button appears
- [ ] Modal opens with format dropdown
- [ ] "Word DOCX - recommended" is default
- [ ] DOCX generates (progress bar shows 100%)
- [ ] File downloads to your computer
- [ ] **DOCX opens in Word without corruption errors** ← KEY TEST
- [ ] All content is visible (client name, date, data)

---

## Report Back

Once you've tested, reply with:

```
✅ SUCCESS / ❌ FAILURE

DOCX opens in Word? YES / NO
Format selected: [DOCX only / DOCX+PDF]
File size: [#] KB
Any error messages? [describe]
Backend logs show errors? [copy error if present]
```

This will tell me if the fix works or if we need additional debugging.

