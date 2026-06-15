# Final Logo Diagnostic - Complete Checklist

**Goal:** Find exactly why logo is not appearing

---

## Step 1: Check Template Has Logo Placeholder

Run this:
```bash
python check_template.py
```

This will check:
- ✅ Does sample.docx exist?
- ✅ Does it have `{{ logo_image }}` placeholder?
- ✅ What other variables does it expect?

**Important:** If template does NOT have `{{ logo_image }}`, that's the problem! The template must have this placeholder for the logo to appear.

---

## Step 2: Check Storage Directories

Run:
```bash
# Windows PowerShell
Get-ChildItem -Path "storage/" -Recurse -Force

# Or create directories if missing
mkdir -p storage/temp/logos
mkdir -p storage/reports
mkdir -p storage/logos
```

**Look for:**
- ✅ Does `storage/temp/logos/` exist?
- ✅ Are logo files being saved there after upload?
- ✅ What files are in it?

---

## Step 3: Redirect Logs to File

Stop current app and restart with logging:

```bash
# Windows PowerShell
Ctrl+C  # Stop current app

# Start with logging to file
python main.py 2>&1 | Tee-Object -FilePath app.log

# Or simpler:
python main.py > app.log 2>&1
```

This captures ALL console output to `app.log`.

---

## Step 4: Generate Report and Capture Logs

While app is running with logging:

1. **Upload Logo:**
   - Open assessment
   - Click "Customize & Generate"
   - Upload a logo file
   - Write down the filename

2. **Generate Report:**
   - Enter company name: "TEST_COMPANY"
   - Enter address: "123 TEST STREET"
   - Select format: DOCX
   - Click Generate
   - Wait for download

3. **Stop App:**
   - Press Ctrl+C in the terminal
   - This flushes the log file

---

## Step 5: Check Logs for Key Messages

Run:
```bash
python check_logs.py
```

This will show you:
- ✅ All [LOGO] messages
- ✅ All [CACHE] messages
- ✅ All [REPORT] messages
- ✅ Any errors

**What you SHOULD see:**
```
[CACHE] Storing customization...
[CACHE]   logo_path: storage/temp/logos/...

[CACHE] Retrieving customization...
[LOGO] render_word_report received logo_path: storage/temp/logos/...
[LOGO] Logo file exists: True
[LOGO] ✅ Logo image created successfully
```

**If you see DIFFERENT messages**, that tells us the problem!

---

## Step 6: Manual Log Analysis

Open `app.log` and search for:

### Look for [LOGO] messages:
```
[LOGO] render_word_report received logo_path: ...
[LOGO] Logo file exists: True/False
[LOGO] File size: XXXXX bytes
[LOGO] ✅ Logo image created successfully
```

**If you see:**
- `Logo file exists: False` → File wasn't saved properly
- `File size: 0` → File is empty
- No [LOGO] messages → Code path not being executed

### Look for [CACHE] messages:
```
[CACHE] Storing customization for {id}:
[CACHE]   logo_path: storage/temp/logos/...
```

**If missing:** Customization not being stored

### Look for file system checks:
```
File does not exist
Permission denied
No such file
```

---

## Step 7: Check Generated Report Location

After generating report, check where it was saved:

```bash
# Find all Word documents
Get-ChildItem -Path "storage/" -Filter "*.docx" -Recurse

# Find all PDFs
Get-ChildItem -Path "storage/" -Filter "*.pdf" -Recurse
```

You should see files like:
```
storage/reports/{assessment_id}/Copilot_Readiness_Assessment_TEST_COMPANY_20260612_134500.docx
```

---

## Step 8: Check Template File Itself

The template file must have the logo placeholder. Open `sample.docx`:

1. Locate: `app/services/reporting/templates/sample.docx`
2. In Microsoft Word or LibreOffice:
   - Click Insert → Field or Edit → Find & Replace
   - Search for `logo_image` or `logo`
   - **Template MUST have this placeholder!**

If it doesn't:
- Add a placeholder: `{{ logo_image }}`
- Save the template
- Try again

---

## Likely Problems & Solutions

### Problem 1: Template doesn't have {{ logo_image }}
**Solution:**
1. Open sample.docx in Word
2. Find where you want the logo (top of cover page)
3. Right-click → Edit Field or Insert placeholder
4. Add: `{{ logo_image }}`
5. Save sample.docx

### Problem 2: Logo file not being created
**Solution:**
- Check `storage/temp/logos/` directory exists
- Check file permissions (should be writable)
- Try uploading a different logo file
- Check file size < 5MB

### Problem 3: Logo file exists but not inserted
**Solution:**
- Check [LOGO] messages for errors
- Verify template has `{{ logo_image }}`
- Try a different file format (PNG specifically)
- Check InlineImage is compatible with docxtpl

### Problem 4: No log messages at all
**Solution:**
- Make sure you restarted app AFTER code changes
- Make sure logging is redirected to file properly
- Check logs are being written to file
- Look at console output directly

---

## Quick Command Checklist

```bash
# 1. Check template
python check_template.py

# 2. Create directories
mkdir -p storage/temp/logos
mkdir -p storage/reports

# 3. Start app with logging
python main.py 2>&1 | Tee-Object app.log

# 4. (In another terminal) Generate report with logo

# 5. Stop app (Ctrl+C) to flush logs

# 6. Check logs
python check_logs.py

# 7. Search logs manually
Select-String -Path "app.log" -Pattern "\[LOGO\]|\[CACHE\]"

# 8. Check files created
Get-ChildItem storage/temp/logos/
Get-ChildItem storage/reports/ -Recurse
```

---

## Share This Information

Once you've run the diagnostics, share:

1. **Output from `python check_template.py`**
   - Does template have `{{ logo_image }}`?

2. **Output from `python check_logs.py`**
   - What [LOGO] messages do you see?
   - What [CACHE] messages?

3. **Files in storage/temp/logos/**
   - Are logo files being created?
   - How many files?

4. **Full [LOGO] and [CACHE] messages from app.log**
   - Copy the actual messages

5. **Any error messages**
   - Especially ones with "logo", "image", "file"

This will tell us **exactly** where the problem is!

---

## Example: What Should Happen

```
User uploads logo.png (50 KB)
    ↓
[CACHE] Storing customization...
[CACHE]   logo_path: storage/temp/logos/2747d178-logo.png
    ↓
File appears in storage/temp/logos/
    ↓
User generates report
    ↓
[CACHE] Retrieving customization...
[CACHE]   logo_path from cache: storage/temp/logos/2747d178-logo.png
[CACHE]   logo file exists: True
[CACHE]   logo file size: 50000 bytes
    ↓
[LOGO] render_word_report received logo_path: storage/temp/logos/2747d178-logo.png
[LOGO] Logo file exists: True
[LOGO] File size: 50000 bytes
[LOGO] ✅ Logo image created successfully
    ↓
Report generated with logo on cover page ✅
```

If any step shows a different message, that's where we need to focus.

---

## I'm Ready to Help

Once you run these diagnostics and share the output, I can pinpoint exactly what's wrong and fix it.

Run:
1. `python check_template.py` → Share output
2. Start app with logging → Generate report → Stop app
3. `python check_logs.py` → Share output
4. Share [LOGO] and [CACHE] lines from app.log

Then we'll know the exact problem!
