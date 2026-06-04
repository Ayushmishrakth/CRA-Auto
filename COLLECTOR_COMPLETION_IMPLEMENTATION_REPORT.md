# Collector Completion Implementation Report

Generated: 2026-06-02

## Implementation Summary

| Metric | Value |
|---|---:|
| Approved parameters | 64 |
| Baseline real collectors | 48 |
| Graph collectors after routing update | 59 |
| PowerShell-backed approved collectors | 5 |
| Manual validation controls | 1 |
| Projected automated real collector coverage | 63 / 64 = 98.44% |
| Projected real evidence coverage with manual validation | 64 / 64 = 100.0% |

## Implemented Controls

| Control | Implementation |
|---|---|
| `custom_banned_password_list` | Graph beta authentication methods policy collector now returns real data when licensed/consented; otherwise returns `LICENSING_REQUIRED` with SKU, role, and permission requirements. |
| `dlp_rules_configured` | Graph beta DLP collector now returns real policy data when available; otherwise returns `LICENSING_REQUIRED`. Purview PowerShell also emits `dlp_rules_configured.csv`. |
| `information_protection_labels_applied` | Graph beta sensitivity label collector now returns real label data with `InformationProtectionPolicy.Read.All`; otherwise returns `LICENSING_REQUIRED`. Purview PowerShell emits canonical label CSV evidence. |
| `sensitivity_labels_are_applied` | Same real Graph/Purview PowerShell evidence path as label controls. |
| `sensitivity_labels_configured_and_applied` | Same real Graph/Purview PowerShell evidence path as label controls. |
| `external_sharing_settings` | Implemented Graph beta SharePoint admin settings collector. |
| `sharepoint_modern_authentication` | Implemented Graph beta SharePoint admin settings collector. |
| `sharing_settings_external_internal` | Implemented Graph beta SharePoint admin settings collector. |
| `checking_sharing_permissions_for_each_sites_on_a_tenant` | Implemented Graph site enumeration plus per-site permissions review using `Sites.FullControl.All`. |
| `getting_all_sites_with_sensitivity_keywords_on_a_tenant` | Hardened Graph site search collector and removed the previous limitation path for normal Graph responses. |
| `audit_log_retention_duration` | Routed to PowerShell runtime; Purview script now emits `audit_log_retention_duration.csv` from retention compliance rules. |
| `external_storage_providers_in_owa` | Routed to PowerShell runtime; Exchange script now emits `external_storage_providers_in_owa.csv` from OWA mailbox policies. |
| `full_calendar_schedules_able_to_be_shared_externally` | Routed to PowerShell runtime; Exchange script now emits `full_calendar_schedules_able_to_be_shared_externally.csv` from sharing policy/org config evidence. |
| `customer_lockbox` | Routed to PowerShell runtime; Purview script now emits `customer_lockbox.csv` from `Get-OrganizationConfig`. |
| `sharepoint_and_onedrive_guest_access_expiry` | Routed to PowerShell runtime; SharePoint script now emits `sharepoint_and_onedrive_guest_access_expiry.csv` from tenant settings. |
| `compliance_score_overview` | Converted from `NOT_SUPPORTED` to `MANUAL_VALIDATION_REQUIRED` with portal location, validation procedure, and expected evidence. |

## Code Changes

| File | Change |
|---|---|
| `CRA-Tool/app/services/graph_permission_service.py` | Added `Sites.FullControl.All`, `SharePointTenantSettings.Read.All`, `InformationProtectionPolicy.Read.All`, and `SecurityActions.Read.All` to required app permissions. |
| `CRA-Tool/app/services/graph_cra_collector_service.py` | Added licensing/manual result contracts, upgraded supported Graph collectors, and routed command-only controls out of Graph placeholders. |
| `CRA-Tool/app/services/runtime_assessment_service.py` | Runtime now executes the approved registry inventory and chooses Graph or PowerShell per parameter. |
| `CRA-Tool/app/services/assessment_service.py` | Evidence coverage excludes `LICENSING_REQUIRED` and `MANUAL_VALIDATION_REQUIRED` from collected counts. |
| `CRA-Tool/app/powershell/exchange/exchange_master.ps1` | Added canonical OWA external storage and calendar sharing evidence CSV outputs. |
| `CRA-Tool/app/powershell/purview/purview_master.ps1` | Added canonical DLP, retention duration, sensitivity label, and Customer Lockbox evidence CSV outputs. |
| `CRA-Tool/app/powershell/sharepoint/sharepoint_master.ps1` | Added canonical SharePoint sharing, site keyword, modern auth, sharing settings, and guest expiry evidence CSV outputs. |
| `CRA-frontend/src/pages/AssessmentEvidencePage.jsx` | Evidence page recognizes `LICENSING_REQUIRED` and `MANUAL_VALIDATION_REQUIRED` as unsupported/prerequisite statuses. |

## Remaining Unsupported Controls

| Control | Remaining Reason |
|---|---|
| `compliance_score_overview` | Manual validation required because Microsoft does not expose a stable app-only Graph or PowerShell endpoint for the tenant Compliance Manager score overview used by this assessment criterion. |

## Evidence Generated

No live reassessment was run in this pass because the new Graph permissions require refreshed admin consent and the PowerShell collectors require delegated Exchange/Purview/PnP authentication on the runtime host. The implementation now generates real evidence when those prerequisites are present and returns explicit prerequisite statuses when they are not.

## Validation

| Check | Result |
|---|---|
| Backend Python compilation | Passed |
| Frontend production build | Passed |
| Permission/deployment validation tests | Passed |

