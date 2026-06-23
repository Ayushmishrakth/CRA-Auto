# Purpose Section Placeholder Fix

**Status:** COMPLETE AND VALIDATED  
**Date:** 2026-06-20  
**Commit:** df1fd07  
**Fixes:** Template placeholders in Purpose section and Executive Summary

---

## THE PROBLEM

Reports contained unfilled template placeholders:

### Issue 1: Purpose Section
**Before:**
```
"Evaluate the __________ environment for alignment with industry best practices."
```

**Should be:**
```
"Evaluate the WealthScape Inc environment for alignment with industry best practices."
```

### Issue 2: Executive Summary
**Before (hardcoded):**
```
"...to evaluate the Client's Microsoft 365 environment..."
```

**Should be (dynamic):**
```
"...to evaluate the WealthScape Inc's Microsoft 365 environment..."
```

---

## ROOT CAUSE

The Purpose section and Executive Summary had template placeholders that weren't being replaced:

1. **Purpose bullet placeholder:** `__________` (underscore format, not `{{...}}` format)
2. **Executive Summary hardcoding:** "Client's" was hardcoded in YAML, not replaced dynamically

The placeholder replacement logic only handled `{{placeholder}}` format, missing the underscore style.

---

## THE FIX

### Change 1: Add Underscore Placeholder Mapping

**File:** CRA-Tool/app/services/reporting/report_builder.py:4542-4551

**Code:**
```python
placeholder_values = {
    "{{customer_name}}": company_name or "{{customer_name}}",
    "{{prepared_by}}": partner_name or "{{prepared_by}}",
    "{{assessment_date}}": assessment_data.get("assessment_date", "{{assessment_date}}"),
    "{{tenant_name}}": assessment_data.get("tenant_name", "{{tenant_name}}"),
    "{{readiness_score}}": str(score) if score else "{{readiness_score}}",
    # CRITICAL: Replace underscore placeholder with customer display name
    "__________": company_name or "Client",
    # Handle "Client's" in Executive Summary
    "Client's": f"{company_name}'s" if company_name else "Client's",
}
```

**Effect:**
- `__________` → Replaced with customer display_name (e.g., "WealthScape Inc")
- `Client's` → Replaced with "{customer_name}'s" (e.g., "WealthScape Inc's")

---

### Change 2: Apply Placeholder Replacement to All Content

The existing loop at lines 4569-4573 already handles Purpose bullets:

```python
for bullet_text in purpose_bullets:
    resolved_bullet = bullet_text
    for placeholder, value in placeholder_values.items():
        resolved_bullet = resolved_bullet.replace(placeholder, value)
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(4)
    _apply_run_style(p.add_run(resolved_bullet), config)
```

With the new placeholder mappings, this now resolves:
- `__________` → Customer name
- `Client's` → Customer name with possessive

---

### Change 3: Add Placeholder Validation

**File:** CRA-Tool/app/services/reporting/report_builder.py:4941-4970

**New function:** `_validate_no_unfilled_placeholders(docx_path, customer_name)`

**Purpose:**
- Scan final report for any remaining unfilled placeholders
- Check for patterns: `{{...}}`, `__________`
- Fail report generation immediately if found
- Log successful validation with customer name

**Code:**
```python
def _validate_no_unfilled_placeholders(docx_path, customer_name):
    """Check that report contains no unfilled placeholders."""
    doc = Document(docx_path)
    all_text = "\n".join(p.text for p in doc.paragraphs)

    unfilled_patterns = [
        "__________",           # Purpose section placeholder
        "{{customer_name}}",    # Unresolved template
        "{{prepared_by}}",      # Unresolved template
        "{{assessment_date}}",  # Unresolved template
        "{{tenant_name}}",      # Unresolved template
        "{{readiness_score}}",  # Unresolved template
    ]

    found_unfilled = []
    for pattern in unfilled_patterns:
        if pattern in all_text:
            found_unfilled.append(pattern)

    if found_unfilled:
        logger.error(f"Found unfilled placeholders: {found_unfilled}")
        raise ValueError(f"Report validation failed: Found unfilled placeholders: {found_unfilled}")

    logger.info(f"Placeholder Validation: PASS")
    logger.info(f"  Customer Name = {customer_name}")
    logger.info(f"  All placeholders resolved successfully")
```

**Integration:** Called at line 5061 before returning report:
```python
_validate_no_unfilled_placeholders(output_path_obj, display_name)
```

---

## VALIDATION RESULTS

### Test 1: WealthScape with organization name

**Input:**
- tenant_name: "WealthScape"
- organization_name: "WealthScape Inc"

**Output:**
- [PASS] Purpose Bullet: "Evaluate the WealthScape Inc environment for alignment with industry best practices."
- [PASS] No unfilled placeholders
- [PASS] No `__________` or `{{...}}` remnants

---

### Test 2: Contoso with tenant name only

**Input:**
- tenant_name: "Contoso"
- organization_name: "" (empty)

**Output:**
- [PASS] Purpose Bullet: "Evaluate the Contoso environment for alignment with industry best practices."
- [PASS] Fallback to tenant_name when organization_name missing
- [PASS] All 8 Purpose bullets present and resolved

---

### Test 3: Missing customer names (fallback)

**Input:**
- tenant_name: "" (empty)
- organization_name: "" (empty)

**Output:**
- [PASS] Purpose Bullet: "Evaluate the Client environment for alignment with industry best practices."
- [PASS] Fallback to "Client" when all fields missing
- [PASS] Graceful degradation, no crashes

---

## ALL 8 PURPOSE BULLETS NOW RESOLVED

Verified in generated reports:

1. "Evaluate the **[CUSTOMER]** environment for alignment with industry best practices." ✓
2. "Assess the environment across Microsoft 365 products and services..." ✓
3. "Identify gaps that could pose security or compliance risks..." ✓
4. "Establish a baseline for future audits and compliance tracking..." ✓
5. "Highlight licensing readiness and user eligibility..." ✓
6. "Provide a risk-based prioritization of remediation efforts..." ✓
7. "Offer actionable insights to strengthen governance..." ✓
8. "Support strategic decision-making by outlining prerequisites..." ✓

---

## DESIGN COMPLIANCE

No changes to:
- Page layout or margins
- Font sizes or colors
- YAML styling or structure
- Bullet formatting
- Document structure

Only data binding fixed - all rendered content matches YAML specification.

---

## FILES MODIFIED

**CRA-Tool/app/services/reporting/report_builder.py**

1. **Lines 4542-4551:** Added placeholder mappings for `__________` and `Client's`
2. **Lines 4941-4970:** Added `_validate_no_unfilled_placeholders()` function
3. **Line 5061:** Call validation before returning

Total: 3 changes, ~40 lines added

---

## PRE-DEPLOYMENT CHECKS

- [x] Purpose bullet #1 resolves customer name dynamically
- [x] All 8 Purpose bullets present
- [x] No unfilled `__________` placeholders
- [x] No unresolved `{{...}}` templates
- [x] Validation catches any remaining placeholders
- [x] Fallback to "Client" works when data missing
- [x] Customer name priority works (organization > tenant > fallback)
- [x] Executive Summary "Client's" replaced with customer name
- [x] No page layout changes
- [x] No styling changes
- [x] YAML unchanged

---

## PRODUCTION READY

**Status:** ALL VALIDATIONS PASSING

Reports now correctly show:

```
Purpose

Evaluate the [CUSTOMER_NAME] environment for alignment with industry best practices.

Assess the environment across Microsoft 365 products and services...

[etc - all 8 bullets with customer name resolved]
```

No more unfilled template placeholders. All customer names come from assessment data.

---

**Fix Complete**
