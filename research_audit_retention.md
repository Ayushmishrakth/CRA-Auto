# Audit Log Retention in Microsoft 365 - Research

## Current Implementation Analysis

### What's Currently Being Used:
1. **Get-RetentionComplianceRule** - Gets retention compliance rules
   - Returns: Name, Policy, RetentionDuration, RetentionComplianceAction, ExpirationDateOption
   - Currently exports to "audit_log_retention_duration.csv"
   - This is for general data retention, not audit log specific retention

2. **Get-AdminAuditLogConfig** - Gets admin audit log configuration
   - Returns: UnifiedAuditLogIngestionEnabled, AdminAuditLogEnabled, TestCmdletLoggingEnabled
   - This shows if audit logging is ENABLED, not the retention duration

### What Microsoft Documentation Says:

**Get-UnifiedAuditLogRetentionPolicy** (if it exists)
- This cmdlet should retrieve the unified audit log retention policy
- Returns: Priority, Name, Description, RecordTypes, Operations, UserIds, RetentionDuration
- RetentionDuration values: ThreeMonths, SixMonths, NineMonths, TwelveMonths, TenYears

**Difference:**
- Get-RetentionComplianceRule = Data retention policies (documents, emails, etc.)
- Get-UnifiedAuditLogRetentionPolicy = Audit log retention policies (who did what and when)

These are DIFFERENT things!

## Questions to Verify:

1. Is Get-UnifiedAuditLogRetentionPolicy a real cmdlet in ExchangeOnlineManagement?
2. If yes, what permissions are required?
3. If no, what's the correct way to retrieve audit log retention duration?
4. Can this be retrieved via Microsoft Graph instead?

## Current Issue:
The code says it "could not be confirmed automatically" but it's not actually trying to call 
Get-UnifiedAuditLogRetentionPolicy or Get-RetentionCompliancePolicy properly.

The PowerShell script uses Get-RetentionComplianceRule which is for GENERAL retention,
not specifically for AUDIT LOG retention.

## Need to Verify:
- Check if Get-UnifiedAuditLogRetentionPolicy actually exists and is accessible
- Check Microsoft Learn documentation for this cmdlet
- Check if there are RBAC permissions preventing access
- Check if this data is available via Graph API instead

## Microsoft Official Documentation References:

### 1. Audit Log Retention Policies
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/purview/audit-log-retention-policies

Key findings:
- Default audit log retention: 90 days for all Microsoft 365 organizations
- Organizations with E5 licenses can retain audit logs for longer
- Can set different retention durations for different types of records
- Retention duration options: 3 months, 6 months, 9 months, 12 months, 10 years

### 2. PowerShell Cmdlets Available:
According to Microsoft documentation, the correct cmdlets are:

**For Audit Log Retention Policies:**
- Get-UnifiedAuditLogRetentionPolicy
- New-UnifiedAuditLogRetentionPolicy  
- Set-UnifiedAuditLogRetentionPolicy
- Remove-UnifiedAuditLogRetentionPolicy

Module: ExchangeOnlineManagement (same as Exchange Online PowerShell)
Connection: Connect-IPPSSession (Compliance & Security PowerShell)

**For General Data Retention:**
- Get-RetentionCompliancePolicy (incorrect for audit logs)
- Get-RetentionComplianceRule (incorrect for audit logs)

### 3. Required Permissions:
To manage audit log retention policies, users need:
- Compliance Administrator role, OR
- Security Administrator role, OR
- Organization Management role (in Exchange Online)

### 4. What Get-UnifiedAuditLogRetentionPolicy Returns:

```
Priority       : 1
Name           : "Audit Retention Policy - 1 Year"
Description    : "Retain audit logs for 1 year"
RecordTypes    : [All record types OR specific ones]
Operations     : [All operations OR specific ones]
UserIds        : [All users OR specific ones]
RetentionDuration : TwelveMonths
```

## Conclusion:

**YES, Get-UnifiedAuditLogRetentionPolicy IS REAL and IS ACCESSIBLE**

✓ It's a documented Microsoft cmdlet
✓ It's in the ExchangeOnlineManagement module
✓ It requires Connect-IPPSSession (not Connect-ExchangeOnline)
✓ It's accessible to Compliance Administrators
✓ It returns the exact RetentionDuration we need

## Why Current Implementation Says "Cannot Be Confirmed":

The current code:
1. Does NOT call Get-UnifiedAuditLogRetentionPolicy at all
2. Uses Get-AdminAuditLogConfig which only shows if audit logging is ENABLED
3. Uses Get-RetentionComplianceRule which is for general data retention, NOT audit logs
4. Then returns "could not be confirmed" because it's not asking the right questions

## RECOMMENDATION:

This parameter CAN be automated. It should call:
- Connect-IPPSSession (using app registration with Compliance Admin role)
- Get-UnifiedAuditLogRetentionPolicy | Sort-Object -Property Priority -Descending | Select-Object Priority,Name,Description,RecordTypes,Operations,UserIds,RetentionDuration

The highest priority policy's RetentionDuration field contains the actual audit log retention.
