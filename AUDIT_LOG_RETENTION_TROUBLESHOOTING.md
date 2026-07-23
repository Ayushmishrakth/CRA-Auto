# Audit Log Retention - Why It's Still Failing

## Current Status:
- ✅ Graph collector removed
- ✅ PowerShell parameter added
- ✅ PowerShell script has logic
- ❌ **PowerShell collection is FAILING**
- ❌ Falling back to "could not be retrieved"

## Root Cause Analysis:

The error message "Configuration for this control could not be automatically retrieved" 
means the PowerShell collector is returning an ERROR or NO DATA.

This happens in the PowerShell script when Connect-IPPSSession fails or 
Get-UnifiedAuditLogRetentionPolicy returns nothing.

---

## Likely Failure Reasons (in order of probability):

### **1. App Registration Missing Compliance Administrator Role** 🔴 MOST LIKELY
**Problem:** 
Get-UnifiedAuditLogRetentionPolicy requires Compliance Administrator role.

**How to Fix:**
1. Go to Azure AD > App registrations > Find your CRA app
2. Go to Enterprise Applications
3. Search for the app
4. Click "Assign users and groups"
5. Assign the app to a user with Compliance Administrator role
OR
6. Create a direct app role assignment for Compliance Administrator

**Verify:**
```powershell
Connect-IPPSSession -AppId $appId -CertificateThumbprint $thumbprint -Organization tenant.onmicrosoft.com
Get-UnifiedAuditLogRetentionPolicy
# Should return policies, not error
```

---

### **2. Connect-IPPSSession Is Failing** 🔴 VERY LIKELY
**Problem:**
The connection to Security & Compliance PowerShell is failing.

**Reasons:**
- Certificate thumbprint is wrong
- App ID is wrong
- Organization ID is wrong
- Certificate not installed on the server
- Network/firewall blocking PowerShell connection

**How to Fix:**
Verify in PowerShell manually:
```powershell
# Test 1: Certificate exists
Get-ChildItem Cert:\CurrentUser\My | where {$_.Thumbprint -eq "YOUR_THUMBPRINT"}

# Test 2: Connection works
Connect-IPPSSession -AppId "YOUR_APP_ID" `
  -CertificateThumbprint "YOUR_THUMBPRINT" `
  -Organization "tenant.onmicrosoft.com"

# Test 3: Cmdlet works
Get-UnifiedAuditLogRetentionPolicy
```

---

### **3. ExchangeOnlineManagement Module Not Installed** 🟡 POSSIBLE
**Problem:**
Get-UnifiedAuditLogRetentionPolicy is in ExchangeOnlineManagement v3+

**How to Fix:**
```powershell
# Check if module is installed
Get-Module ExchangeOnlineManagement -ListAvailable

# If not, install
Install-Module -Name ExchangeOnlineManagement -Repository PSGallery -AllowClobber -Force

# Import module
Import-Module ExchangeOnlineManagement
```

---

### **4. Tenant Doesn't Support Audit Log Retention Policies** 🟡 LESS LIKELY
**Problem:**
Some M365 tenants don't have audit log retention policies feature enabled.

**How to Verify:**
```powershell
# After connecting
Get-UnifiedAuditLogRetentionPolicy

# Should return something, even if empty
# If it returns an error like "cmdlet not recognized", tenant doesn't support it
```

---

### **5. Certificate Thumbprint Mismatch** 🟡 POSSIBLE
**Problem:**
The certificate used for app auth doesn't match the one in app registration.

**How to Fix:**
1. Get cert thumbprint being used:
   ```powershell
   (Get-ChildItem Cert:\CurrentUser\My | where {$_.Subject -match "CN=your-cert"}).Thumbprint
   ```

2. Get thumbprint in app registration:
   - Azure AD > App registrations > Certificates & secrets > Thumbprint field

3. They MUST match exactly (case-sensitive)

---

## Debug Steps You Should Run:

**Step 1: Check the PowerShell script output**
```
Look in: CRA-Tool/artifacts/[assessment_id]/purview/unified_audit_log_retention_policy.csv

If file doesn't exist → Script didn't run or failed before this line
If file is empty/error → Script ran but Get-UnifiedAuditLogRetentionPolicy failed
If file has data → Issue is in Python parsing
```

**Step 2: Check Purview PowerShell script logs**
```
The purview_master.ps1 script location:
CRA-Tool/app/powershell/purview/purview_master.ps1

Check if it's being called at all by looking for output files:
- audit_logging.csv (from Get-AdminAuditLogConfig)
- dlp_policies.csv (from Get-DlpCompliancePolicy)
- unified_audit_log_retention_policy.csv (from Get-UnifiedAuditLogRetentionPolicy)

If only first 2 exist but NOT the 3rd → The script reached that point and failed
```

**Step 3: Manually test the PowerShell command**
```powershell
# On your server, run:
Import-Module ExchangeOnlineManagement

Connect-IPPSSession -AppId "YOUR_APP_ID" `
  -CertificateThumbprint "YOUR_CERT_THUMBPRINT" `
  -Organization "YOUR_TENANT.onmicrosoft.com"

# This should work without errors
Get-UnifiedAuditLogRetentionPolicy | Select-Object Priority,Name,RetentionDuration

# If this works, the rest should work too
```

---

## Most Likely Fix (90% chance this is it):

**Your app registration is missing the Compliance Administrator role assignment.**

This is needed for:
- Connect-IPPSSession authentication
- Access to Get-UnifiedAuditLogRetentionPolicy
- Read permissions on audit log retention policies

**To fix:**
1. Azure Portal → Azure AD → Enterprise Applications
2. Search for your CRA app registration
3. Assign "Compliance Administrator" role to the service principal
4. Wait 5 minutes for permissions to propagate
5. Run another assessment

---

## What To Check First (in order):

1. ✅ Does unified_audit_log_retention_policy.csv exist in artifacts?
2. ✅ Can you manually run `Get-UnifiedAuditLogRetentionPolicy` from PowerShell?
3. ✅ Does your app have Compliance Administrator role?
4. ✅ Is ExchangeOnlineManagement v3+ installed?
5. ✅ Is the certificate/app ID/thumbprint correct?

