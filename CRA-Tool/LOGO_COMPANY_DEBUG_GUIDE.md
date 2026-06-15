# Logo & Company Name Integration - Complete Debug Guide

**Status:** ✅ Fixed and Ready to Test  
**Date:** 2026-06-12

---

## What Was Fixed

### Logo Integration
✅ Added proper file existence checking  
✅ Added detailed logging for debugging  
✅ Improved error handling  
✅ Logo insertion with fallback  

### Company Name & Address
✅ Company name now appears on cover page  
✅ Company address appears below company name  
✅ Company name used in Executive Summary  
✅ Company name used in Conclusion  
✅ Professional formatting maintained  

---

## Files Updated

```
✅ app/services/reporting/enhanced_report_generator.py
   - Updated _add_cover_page() with logo + company details
   - Added logging for debugging
   - Added file existence checking
   - Added fallback for missing logo

✅ app/api/v1/assessments.py
   - Pass company_address to assessment_data
   - Enhanced logging for customization
```

---

## 🎯 How to Test (Step-by-Step)

### STEP 1: Restart Application
```bash
# Stop current instance
Ctrl+C

# Restart
python main.py

# You should see server running on localhost:3000
```

### STEP 2: Open Assessment
```
1. Go to http://localhost:3000
2. Click "Assessments"
3. Click on any completed assessment
4. You should see "Customize & Generate" button
```

### STEP 3: Upload Logo
```
1. Click "Customize & Generate" button
2. Modal dialog opens
3. Click "Upload Logo" button
4. Select a PNG, JPG, or SVG file from your computer
5. After upload, logo preview appears in form
6. Keep dialog open for next step
```

### STEP 4: Enter Company Details
```
1. In "Company Name" field:
   - Clear any existing text
   - Type: "Your Company Name"
   - Example: "Acme Corporation"

2. In "Company Address" field:
   - Type: "123 Business Street, City, State 12345"
   - This will appear on cover page below company name

3. Select Report Format:
   - Choose "PDF" or "Word Document"
   - For testing, PDF is faster

4. Click "Apply & Generate" button
```

### STEP 5: Check Server Logs
```
Application logs will show:
[LOGO] Attempting to add logo from: storage/logos/...
[LOGO] Logo path exists: True
[LOGO] Logo added successfully
[DOWNLOAD] Applying company name: Your Company Name
[DOWNLOAD] Applying company address: 123 Business Street...
[DOWNLOAD] Company: Your Company Name
```

**If you see these messages → Logo is being processed correctly ✅**

### STEP 6: Download Report
```
1. Wait 10-30 seconds for generation
2. Report should download automatically
3. If not, check browser download folder
```

### STEP 7: Open Report & Verify
```
Open the PDF or DOCX file and check:

✅ Cover Page:
   - Logo appears at TOP, centered
   - Logo size: approximately 1.5 inches wide
   - Company name appears below logo (larger font, bold)
   - Company address appears below company name
   - Assessment date at bottom

✅ Executive Summary (page 5):
   - Should mention your company name
   - Example: "As part of its digital transformation strategy, 
     Your Company Name engaged..."

✅ Conclusion (last page):
   - Should mention your company name
   - Example: "The Copilot Readiness Assessment for 
     Your Company Name reveals..."

✅ All other content:
   - All 65 parameters should be present
   - Color-coded tables
   - Charts with proper colors
   - Professional formatting
```

---

## Expected Cover Page Layout

```
┌────────────────────────────────────────┐
│                                        │
│          [COMPANY LOGO]                │
│    (1.5 inches wide, centered)         │
│                                        │
│  Microsoft 365 Copilot Readiness       │
│     Assessment Report                  │
│                                        │
│         Acme Corporation               │
│      (Your Company Name)               │
│                                        │
│   123 Business Street, City, State     │
│         (Your Address)                 │
│                                        │
│    Assessment Date: 12 June 2026       │
│                                        │
└────────────────────────────────────────┘
```

---

## Troubleshooting

### Logo Not Appearing

**Check 1: Look at Application Logs**
```
If you see:
✅ [LOGO] Logo added successfully
   → Logo uploaded correctly, check report file

❌ [LOGO] Logo file not found
   → Logo file path is wrong or file doesn't exist
   → Try uploading again

❌ [LOGO] Picture insertion failed
   → File format issue or file corruption
   → Try with different image format
```

**Check 2: Verify Upload Worked**
```
After uploading logo, you should see:
- Logo preview in the form
- Success message (if shown)
- Form ready for next steps
```

**Check 3: Check File Location**
```bash
# Check if logo files exist
ls -la storage/logos/

# You should see files like:
# user-id_uuid-1.png
# user-id_uuid-2.jpg
```

**Check 4: Verify File Permissions**
```bash
# Check if files are readable
file storage/logos/*

# Should show:
# PNG image data
# JPEG image data
# SVG Scalable Vector Graphics image
```

### Company Name Not Appearing

**Check 1: Verify You Entered Name**
```
In form before generating report:
- "Company Name" field has your text
- Not empty or placeholder text
```

**Check 2: Check Logs**
```
You should see:
[DOWNLOAD] Applying company name: Your Company Name
[DOWNLOAD] Company: Your Company Name
```

**Check 3: Verify in Report**
```
- Cover page: Should show "Your Company Name" (20pt, bold)
- Executive Summary: Should mention company name
- Conclusion: Should mention company name
```

---

## Debug Checklist

Before asking for help, verify:

- [ ] Application restarted after changes
- [ ] Logo file is PNG, JPG, or SVG
- [ ] Logo file size < 5MB
- [ ] Company name entered in form
- [ ] Company address entered in form (optional)
- [ ] Report format selected (PDF or DOCX)
- [ ] Clicked "Apply & Generate" button
- [ ] Waited 10-30 seconds for generation
- [ ] Downloaded file opened successfully
- [ ] Checked application logs for errors
- [ ] Logo preview appeared in form
- [ ] File exists in storage/logos/

---

## What Each Log Message Means

```
[LOGO] Attempting to add logo from: storage/logos/user-id_uuid.png
  → Logo path found, trying to insert

[LOGO] Logo path exists: True
  → File found on disk and readable

[LOGO] Logo added successfully
  → Logo inserted into Word document ✅

[LOGO] Picture insertion failed: [error]
  → File exists but can't be added
  → Usually means corrupted file or wrong format

[DOWNLOAD] Applying company name: Acme Corporation
  → Company name being applied to report

[DOWNLOAD] Applying company address: 123 Business St
  → Company address being applied

[DOWNLOAD] Company: Acme Corporation
  → Final company name confirmed
```

---

## Testing with Real Files

### Example 1: PNG Logo
```
1. Find a PNG file on your computer
2. Make sure it's not too large (< 5MB)
3. Upload via form
4. Generate report
5. Check if logo appears on cover page
```

### Example 2: Company Details
```
1. Upload any logo
2. Enter: "Test Company Inc."
3. Enter: "456 Oak Avenue, Springfield, IL 62701"
4. Generate PDF
5. Open PDF and verify both appear on cover page
```

---

## Success Criteria

Report generation is working correctly when:

✅ **Logo**
- Appears at top of cover page
- Centered horizontally
- Sized appropriately (1.5" width)
- Clear and readable quality
- Works for PNG, JPG, and SVG

✅ **Company Name**
- Shows on cover page (large, bold)
- Shows in Executive Summary
- Shows in Conclusion
- Correct spelling and formatting

✅ **Company Address**
- Shows on cover page below company name
- Professional formatting
- Complete address visible

✅ **Report Quality**
- All 65 parameters present
- Color-coded tables
- Charts display correctly
- Professional appearance
- No errors in logs

---

## Common Issues & Solutions

### Issue: "Logo file not found"
**Solution:**
1. Check file exists in storage/logos/
2. Try uploading again
3. Verify file permissions
4. Check file isn't corrupted

### Issue: "Logo appears blurry"
**Solution:**
1. Use higher resolution image
2. Logo is sized to 1.5" - if source is small it may be pixelated
3. Try SVG format for crisp edges

### Issue: "Company name still shows 'Organization'"
**Solution:**
1. Make sure you entered name in form
2. Check logs show "Applying company name: Your Name"
3. Verify report was regenerated after entering name

### Issue: "Address doesn't appear"
**Solution:**
1. Address is optional - only appears if you enter it
2. Make sure you typed in "Company Address" field
3. Check logs show "Applying company address: ..."

### Issue: "Report generation timeout"
**Solution:**
1. Wait 30+ seconds (first time is slower)
2. Check application logs for errors
3. Restart application and try again
4. Try smaller assessment first

---

## Next Steps After Testing

Once logo and company name appear correctly:

1. ✅ Test with different logos (PNG, JPG, SVG)
2. ✅ Test with different company names
3. ✅ Test both PDF and DOCX formats
4. ✅ Test with multiple assessments
5. ✅ Verify consistency across all pages
6. ✅ Check professional appearance

---

## Questions or Issues?

If logo still doesn't appear after testing:

1. **Check the logs** - Most detailed error info is there
2. **Verify file exists** - ls storage/logos/
3. **Try different image** - Might be file format issue
4. **Restart application** - Clear any stuck state
5. **Check file permissions** - Image file must be readable

---

## Summary

The logo and company name integration is now complete with:
- ✅ Logo file handling with proper validation
- ✅ Company name applied throughout report
- ✅ Company address on cover page
- ✅ Enhanced logging for debugging
- ✅ Fallback handling for errors
- ✅ Professional formatting

Everything is ready to test!

