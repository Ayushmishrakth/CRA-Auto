# Automation Feasibility Matrix

Latest assessment: `83e0f4d2238e4be1bf5a8fc4687f4088`

| Parameter Name | Current Status | Feasibility Classification | Notes |
|---|---:|---:|---|
| Auto-expiration policy for M365 Groups | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No License: Possible Entra ID P1/P2 feature requirement |
| Custom Banned Password List | `LICENSING_REQUIRED` | `LICENSING_BLOCKED` | No License: Microsoft Entra ID P1 or P2 required by runtime |
| External Storage Providers In OWA | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No |
| Full Calendar Schedules Able To Be Shared Externally | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No |
| Customer Lockbox | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No License: Customer Lockbox is commonly tied to eligible enterprise subscriptions; runtime did not reach licensing check |
| Audit log retention duration | `FAILED_COLLECTOR` | `PARTIALLY_AUTOMATABLE` | No License: Advanced audit retention may require E5/Purview licensing |
| Compliance Score overview | `MANUAL_VALIDATION` | `MANUAL_ONLY` | Not impossible for human export; not reliably automatable in this app-only runtime License: Compliance Manager licensing may affect availability |
| DLP rules configured | `LICENSING_REQUIRED` | `LICENSING_BLOCKED` | No License: Microsoft 365 E5 or Purview DLP required by runtime |
| Information Protection Labels applied | `LICENSING_REQUIRED` | `LICENSING_BLOCKED` | No License: Microsoft 365 E5 or Purview Information Protection required by runtime |
| Sensitivity Labels configured and applied | `LICENSING_REQUIRED` | `LICENSING_BLOCKED` | No License: Microsoft 365 E5 or Purview Information Protection required by runtime |
| Teams with external guest as owner | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No License: No special license beyond Teams/Graph access identified |
| Days to retain a deleted user’s OneDrive | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No License: SharePoint Online required |
| External sharing settings | `LICENSING_REQUIRED` | `LICENSING_BLOCKED` | No License: Runtime reported SharePoint Online/licensing/permission blocker |
| Expiration Policy for Anyone links | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No License: SharePoint Online required |
| Getting all sites with Sensitivity keywords on a Tenant | `LICENSING_REQUIRED` | `LICENSING_BLOCKED` | No License: Runtime reported SharePoint Online/licensing/permission blocker |
| Inactive site policies | `FAILED_COLLECTOR` | `PARTIALLY_AUTOMATABLE` | No, but may be partial depending on whether policy presence or computed inactive sites is required License: SharePoint Advanced Management may be needed for native inactive-site policy features |
| Permission Settings for anyone links | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No License: SharePoint Online required |
| SharePoint & OneDrive Guest Access Expiry | `FAILED_COLLECTOR` | `FULLY_AUTOMATABLE` | No License: SharePoint Online required |
| SharePoint - Modern Authentication | `LICENSING_REQUIRED` | `LICENSING_BLOCKED` | No License: Runtime reported SharePoint Online/licensing/permission blocker |
| Sharing Settings (External/Internal) | `LICENSING_REQUIRED` | `LICENSING_BLOCKED` | No License: Runtime reported SharePoint Online/licensing/permission blocker |
| Site Ownership policies | `FAILED_COLLECTOR` | `PARTIALLY_AUTOMATABLE` | No, but policy validation may be partial License: SharePoint Online; advanced policy features may require SharePoint Advanced Management |

## Feasibility Counts

- `FULLY_AUTOMATABLE`: 9
- `PARTIALLY_AUTOMATABLE`: 3
- `LICENSING_BLOCKED`: 8
- `MANUAL_ONLY`: 1
