# Why Audit Log Retention Parameter Still Shows "Could Not Be Retrieved"

## Root Causes (5 Issues):

### **Issue #1: Wrong Execution Architecture** ⚠️ CRITICAL
**Problem:** 
- I added `audit_log_retention_duration` to `POWERSHELL_REQUIRED_PARAMETERS`
- But the Python collector function `collect_audit_log_retention_duration()` is STILL being called from the Graph collectors path
- The runtime doesn't know NOT to call the Python function when a parameter is in POWERSHELL_REQUIRED_PARAMETERS

**Why:**
- The Graph collectors are loaded and called first
- The POWERSHELL_REQUIRED_PARAMETERS is checked AFTER the Graph collector runs
- Since the function is in GRAPH_COLLECTORS dict, it gets called regardless

**Impact:** 
- The Python collector runs first and fails (tries to call non-existent PowerShell engine method)
- Then the PowerShell collector never even gets a chance to run

---

### **Issue #2: Non-Existent Method** ⚠️ CODE ERROR
**Problem:**
In my Python collector code, I wrote:
```python
ps_engine = PowerShellExecutionEngine()
result = await ps_engine.execute_purview_collector(...)
```

**Reality:**
- `execute_purview_collector()` method does NOT exist
- The actual method is `run_collector()`
- But `run_collector()` should NOT be called from within a Graph collector function

**This is a design flaw** - Graph collectors cannot directly invoke PowerShell collectors

---

### **Issue #3: Collector Registration Mismatch** ⚠️ ARCHITECTURE
**Problem:**
- I registered the collector as `powershell.audit_log_retention_duration` in collectors.json
- But the Python function `collect_audit_log_retention_duration` is registered in GRAPH_COLLECTORS dict in graph_cra_collector_service.py
- The runtime sees TWO conflicting registrations

**Code Location:**
- Line 4420 in graph_cra_collector_service.py: `"audit_log_retention_duration": collect_audit_log_retention_duration,`
- This MUST be removed since we want PowerShell collection, not Graph

---

### **Issue #4: Execution Flow Doesn't Support Mixed Calls** ⚠️ FLOW
**Current Flow:**
1. Runtime Assessment Service loops through GRAPH_COLLECTORS
2. Calls each Graph collector function (including audit_log_retention_duration)
3. LATER, it checks if parameter is in POWERSHELL_REQUIRED_PARAMETERS
4. By then, the Graph collector already ran and returned a result

**Problem:**
- Graph collector runs first and returns "could not be retrieved" 
- PowerShell collection never happens because Graph collector already set the result

**Expected Flow:**
1. Runtime checks if parameter is in POWERSHELL_REQUIRED_PARAMETERS
2. If YES → Call PowerShell collector via PowerShellExecutionEngine.run_collector()
3. If NO → Call Graph collector from GRAPH_COLLECTORS
4. Return result (never call both)

---

### **Issue #5: Parameters Not Properly Linked** ⚠️ CONFIG
**Problem:**
- collectors.json says `"collector_name": "powershell.audit_log_retention_duration"`
- But runtime_assessment_service.py doesn't know to skip the Graph collector with the same parameter_key
- No mechanism to tell runtime: "For THIS parameter, use PowerShell, not Graph"

**Result:**
- Both collectors get called
- Graph collector runs first and fails (error handling catches the bad method call)
- PowerShell collector never runs or is ignored

---

## Summary of All Issues:

| Issue | Cause | Impact | Severity |
|-------|-------|--------|----------|
| #1 | Graph collector called instead of PowerShell | Parameter uses wrong collector type | CRITICAL |
| #2 | Non-existent method `execute_purview_collector()` | Runtime error caught by exception handler | HIGH |
| #3 | Collector registered in BOTH graph and config | Conflicting registrations | HIGH |
| #4 | Execution flow doesn't switch collectors | Always uses Graph path | CRITICAL |
| #5 | No skip-Graph logic for PowerShell params | Graph runs when PowerShell should | CRITICAL |

---

## What Needs to Happen:

The collector needs to be:
1. ✅ Added to POWERSHELL_REQUIRED_PARAMETERS (DONE)
2. ❌ REMOVED from GRAPH_COLLECTORS dict (NOT DONE)
3. ❌ Runtime must skip Graph collector for PowerShell params (NOT DONE)
4. ✅ Registered in collectors.json as PowerShell (DONE)
5. ✅ PowerShell script has correct logic (DONE)

---

## The Actual Error Message Reason:

When you see: **"Configuration for this control could not be automatically retrieved during this assessment run"**

This happens because:
1. Runtime calls the Python Graph collector function
2. That function tries to call `ps_engine.execute_purview_collector()` (doesn't exist)
3. Exception is caught
4. Function returns an error/fallback result
5. Report displays "could not be retrieved"

**The PowerShell script never even runs** because the Python function fails first.

