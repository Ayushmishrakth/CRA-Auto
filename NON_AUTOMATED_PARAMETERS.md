# Non-Automated Parameters

Latest assessment: `83e0f4d2238e4be1bf5a8fc4687f4088`

Total parameters: 65
Automated PASS/FAIL evidence: 44
Not returning real PASS/FAIL evidence: 21

| Parameter Name | Current Status | Reason |
|---|---:|---|
| Auto-expiration policy for M365 Groups | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| Custom Banned Password List | `LICENSING_REQUIRED` | Blocked by license/permission/service prerequisite: Microsoft Entra ID P1 or P2; role: Authentication Policy Administrator or Global Administrator; permissions: Policy.Read.All |
| External Storage Providers In OWA | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| Full Calendar Schedules Able To Be Shared Externally | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| Customer Lockbox | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| Audit log retention duration | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| Compliance Score overview | `MANUAL_VALIDATION` | Runtime reports no stable app-only endpoint for this tenant-level control; current evidence is procedural/manual validation, not automated measurement. |
| DLP rules configured | `LICENSING_REQUIRED` | Blocked by license/permission/service prerequisite: Microsoft 365 E5 or Microsoft Purview DLP; role: Compliance Administrator or DLP Compliance Management; permissions: SecurityActions.Read.All |
| Information Protection Labels applied | `LICENSING_REQUIRED` | Blocked by license/permission/service prerequisite: Microsoft 365 E5 or Microsoft Purview Information Protection; role: Compliance Administrator or Information Protection Administrator; permissions: InformationProtectionPolicy.Read.All |
| Sensitivity Labels configured and applied | `LICENSING_REQUIRED` | Blocked by license/permission/service prerequisite: Microsoft 365 E5 or Microsoft Purview Information Protection; role: Compliance Administrator or Information Protection Administrator; permissions: InformationProtectionPolicy.Read.All |
| Teams with external guest as owner | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| Days to retain a deleted user’s OneDrive | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| External sharing settings | `LICENSING_REQUIRED` | Blocked by license/permission/service prerequisite: SharePoint Online; role: SharePoint Administrator or Global Administrator; permissions: SharePointTenantSettings.Read.All |
| Expiration Policy for Anyone links | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| Getting all sites with Sensitivity keywords on a Tenant | `LICENSING_REQUIRED` | Blocked by license/permission/service prerequisite: SharePoint Online; role: SharePoint Administrator or Global Administrator; permissions: Sites.Read.All |
| Inactive site policies | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| Permission Settings for anyone links | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| SharePoint & OneDrive Guest Access Expiry | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
| SharePoint - Modern Authentication | `LICENSING_REQUIRED` | Blocked by license/permission/service prerequisite: SharePoint Online; role: SharePoint Administrator or Global Administrator; permissions: SharePointTenantSettings.Read.All |
| Sharing Settings (External/Internal) | `LICENSING_REQUIRED` | Blocked by license/permission/service prerequisite: SharePoint Online; role: SharePoint Administrator or Global Administrator; permissions: SharePointTenantSettings.Read.All |
| Site Ownership policies | `FAILED_COLLECTOR` | No real evidence. Artifact status is failed; runtime failure is NotImplementedError. This is an implementation/runtime mapping gap, not tenant evidence. |
