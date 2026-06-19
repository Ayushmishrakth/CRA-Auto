# CRITICAL FIX: Customer Data Binding

**Status:** COMPLETE AND VALIDATED  
**Date:** 2026-06-20  
**Commit:** 9867a44  
**Branch:** main

---

## THE PROBLEM

Reports were showing:

```
"TechPlusTalent engaged TechPlusTalent
for a Copilot Readiness Assessment"
```

Instead of actual customer data:

```
"WealthScape engaged Lumbee International
for a Copilot Readiness Assessment"
```

---

## ROOT CAUSE ANALYSIS

**File:** CRA-Tool/app/services/reporting/cra_report_service.py

**Issue 1 - Line 33 (Hardcoded Default):**
```python
DEFAULT_REPORT_COMPANY_NAME = "TechPlusTalent"
```

**Issue 2 - Line 49 (Applied to customer name):**
```python
"partner_name": (partner_name or "").strip() or DEFAULT_REPORT_COMPANY_NAME,
```

**Issue 3 - Line 550 (Overwrites assessment data):**
```python
report_data['partner_name'] = partner_name  # Overwrites with "TechPlusTalent"
```

**Issue 4 - Lines 569, 572 (Parameters override assessment data):**
```python
build_docx_report(
    company_name=partner_name,        # "TechPlusTalent"
    partner_name=partner_name,        # "TechPlusTalent"
)
```

---

## THE FIX

### Change 1: resolve_report_branding()

**File:** CRA-Tool/app/services/reporting/cra_report_service.py:37-52

**Before:**
```python
"partner_name": (partner_name or "").strip() or DEFAULT_REPORT_COMPANY_NAME,
```

**After:**
```python
"partner_name": (partner_name or "").strip() or None,
```

**Result:** Logo branding still uses DEFAULT_REPORT_COMPANY_NAME, but customer names no longer do.

---

### Change 2: generate_report_bundle()

**File:** CRA-Tool/app/services/reporting/cra_report_service.py:546-573

**Before:**
```python
report_data['partner_name'] = partner_name
build_docx_report(
    assessment_data=report_data,
    output_path=str(docx_path),
    company_name=partner_name,
    company_address=company_address,
    logo_path=logo_path,
    partner_name=partner_name,
)
```

**After:**
```python
# CRITICAL: Do NOT override assessment data with branding defaults
if partner_name:
    report_data['partner_name'] = partner_name

build_docx_report(
    assessment_data=report_data,
    output_path=str(docx_path),
    company_name=None,  # Force assessment data priority
    company_address=company_address,
    logo_path=logo_path,
    partner_name=partner_name,
)
```

**Result:** Assessment data only overridden if custom branding explicitly provided. Passes None for company_name to force priority chain.

---

### Change 3: build_docx_report()

**File:** CRA-Tool/app/services/reporting/report_builder.py:4937-4978

**Implemented Priority Chain for Customer Names:**

```
Priority 1: organization_name (from assessment)
Priority 2: customer_name (from assessment)
Priority 3: tenant_name (from assessment)
Priority 4: company_name parameter (optional override)
Priority 5: Fallback to 'Client'
```

**Implemented Priority Chain for Partner Name:**

```
Priority 1: partner_name from assessment data
Priority 2: partner_name parameter (optional override)
Priority 3: Fallback to 'CRA Assessment Team'
```

**Before:**
```python
display_name = (company_name or '').strip() or assessment_data.get('tenant_name', 'Client')
partner = (partner_name or '').strip() or 'CRA Assessment Team'
```

**After:**
```python
tenant_name_from_data = assessment_data.get('tenant_name', '').strip()
customer_name_from_data = assessment_data.get('customer_name', '').strip()
org_name_from_data = assessment_data.get('organization_name', '').strip()
partner_name_from_data = assessment_data.get('partner_name', '').strip()

display_name = (
    org_name_from_data or
    customer_name_from_data or
    tenant_name_from_data or
    (company_name or '').strip() or
    'Client'
)

partner = (
    partner_name_from_data or
    (partner_name or '').strip() or
    'CRA Assessment Team'
)
```

---

### Change 4: Validation

**Added strict validation to prevent accidental DEFAULT_REPORT_COMPANY_NAME usage:**

```python
from app.services.reporting.cra_report_service import DEFAULT_REPORT_COMPANY_NAME

if display_name == DEFAULT_REPORT_COMPANY_NAME and tenant_name_from_data != DEFAULT_REPORT_COMPANY_NAME:
    logger.error(f"[REPORT_BUILDER] FAILED: DEFAULT_REPORT_COMPANY_NAME '{display_name}' used as customer name for tenant '{tenant_name_from_data}'")
    raise ValueError(f"Report generation failed: Using DEFAULT_REPORT_COMPANY_NAME '{display_name}' as customer name for assessment tenant '{tenant_name_from_data}'. Assessment data must contain correct customer information.")
```

**Result:** Report generation fails immediately if DEFAULT_REPORT_COMPANY_NAME ("TechPlusTalent") is accidentally used as customer name for a different tenant.

---

## VALIDATION RESULTS

### Test Case 1: WealthScape with partner from assessment

**Input:**
- tenant_name: "WealthScape"
- organization_name: "WealthScape Inc"
- partner_name: "Lumbee International"
- company_name parameter: None
- partner_name parameter: None

**Output:**
- [PASS] Report contains "WealthScape Inc" (customer)
- [PASS] Report contains "Lumbee" (partner)
- [PASS] Report does NOT contain "TechPlusTalent engaged TechPlusTalent"

---

### Test Case 2: Acme Corp with custom partner

**Input:**
- tenant_name: "acme-corp"
- organization_name: "Acme Corporation"
- partner_name: "Global Consulting LLC"
- company_name parameter: None
- partner_name parameter: None

**Output:**
- [PASS] Report contains "Acme" (customer)
- [PASS] Report contains "Global" (partner)
- [PASS] Report does NOT contain "TechPlusTalent"

---

### Test Case 3: Only tenant_name available

**Input:**
- tenant_name: "TestCorp"
- organization_name: "" (empty)
- customer_name: "" (empty)
- partner_name: "" (empty)
- company_name parameter: None
- partner_name parameter: None

**Output:**
- [PASS] Report contains "TestCorp" (customer from tenant_name)
- [PASS] Report contains "CRA Assessment Team" (default partner)
- [PASS] Report does NOT contain "TechPlusTalent"

---

## DATA BINDING LOGGING

Every report generation now logs data sources:

```
[REPORT_BUILDER] Data Binding Validation
  Customer Name = WealthScape Inc (source: org)
  Tenant Name = WealthScape
  Organization = WealthScape Inc
  Partner = Lumbee International (source: data)
```

Shows:
- Which field was used as customer name
- Where each value came from
- Confirms no hardcoded values were used

---

## FILES MODIFIED

### 1. CRA-Tool/app/services/reporting/cra_report_service.py

**Lines 37-52:** resolve_report_branding()
- Changed partner_name fallback to None instead of DEFAULT_REPORT_COMPANY_NAME

**Lines 546-573:** generate_report_bundle()
- Only override assessment_data if partner_name explicitly provided
- Pass company_name=None to force assessment data priority

### 2. CRA-Tool/app/services/reporting/report_builder.py

**Lines 4937-4978:** build_docx_report()
- Implement priority chain for customer names
- Implement priority chain for partner names
- Add validation to reject DEFAULT_REPORT_COMPANY_NAME for non-TechPlusTalent tenants
- Enhance logging to show data sources

---

## EXECUTIVE SUMMARY

### Before Fix

```
Customer Report Generated:
Assessment: WealthScape
Output: "TechPlusTalent engaged TechPlusTalent"
Root Cause: DEFAULT_REPORT_COMPANY_NAME hardcoded default leaked into customer names
```

### After Fix

```
Customer Report Generated:
Assessment: WealthScape
Output: "WealthScape engaged [partner from assessment]"
Result: Assessment data used, no hardcoded defaults
Validation: Prevents accidental misuse
```

---

## PRODUCTION CHECKLIST

- [x] Root cause identified
- [x] Hardcoded DEFAULT_REPORT_COMPANY_NAME removed from customer data path
- [x] Priority chain implemented (assessment data → parameter → fallback)
- [x] Validation added (fails if TechPlusTalent used for non-TechPlusTalent tenant)
- [x] Logging enhanced (shows data sources)
- [x] All test cases passing
- [x] No regressions in page layout, fonts, or YAML
- [x] Committed to main

---

## DEPLOYMENT NOTES

**No breaking changes.** Existing systems will see improved data accuracy:

- Reports that were showing "TechPlusTalent" will now show correct customer names
- Custom branding (logo, partner name override) still works but no longer affects customer ID
- Assessment data always takes priority over parameters
- Validation catches accidental misconfiguration immediately

---

**Fix Complete - Ready for Production**
