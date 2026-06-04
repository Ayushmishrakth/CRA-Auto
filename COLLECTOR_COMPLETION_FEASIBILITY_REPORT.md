# Collector Completion Feasibility Report

Generated: 2026-06-02

## Summary

| Metric | Value |
|---|---:|
| Approved parameters | 64 |
| Baseline real collectors | 48 |
| Baseline real coverage | 75.0% |
| Unsupported controls reviewed | 16 |
| Automatable with app-only Graph after consent | 10 |
| Automatable with delegated PowerShell | 5 |
| Manual-only controls | 1 |

## Coverage Projection

| Stage | Real Evidence Controls | Coverage |
|---|---:|---:|
| Current baseline | 48 / 64 | 75.0% |
| After Graph permission refresh | 53 / 64 | 82.81% |
| After E5 / premium Graph controls | 58 / 64 | 90.63% |
| After delegated PowerShell controls | 63 / 64 | 98.44% |
| After manual validation package | 64 / 64 | 100.0% evidence coverage, 98.44% automated collector coverage |

## Feasibility Matrix

| parameter_key | Available Graph API | Available PowerShell Command | Required License | Required Role | Required Permissions | Classification |
|---|---|---|---|---|---|---|
| `audit_log_retention_duration` | No stable app-only Graph endpoint for exact retention duration | `Get-RetentionCompliancePolicy`; `Get-RetentionComplianceRule` | Microsoft Purview / Exchange Online | Compliance Administrator | Delegated Compliance PowerShell | AUTOMATABLE_WITH_POWERSHELL |
| `compliance_score_overview` | No stable Graph endpoint for Compliance Manager score overview | Portal export only | Microsoft Purview Compliance Manager | Compliance Administrator | N/A | MANUAL_ONLY |
| `custom_banned_password_list` | Graph beta authentication methods policy password configuration | N/A | Entra ID P1/P2 | Authentication Policy Administrator | `Policy.Read.All` | AUTOMATABLE_WITH_E5 |
| `customer_lockbox` | No stable app-only Graph endpoint for tenant Lockbox setting | `Get-OrganizationConfig` | Microsoft 365 E5 / Customer Lockbox entitlement | Exchange Administrator / Global Administrator | Delegated Exchange PowerShell | AUTOMATABLE_WITH_POWERSHELL |
| `dlp_rules_configured` | Graph beta security DLP policies | `Get-DlpCompliancePolicy` | Microsoft 365 E5 / Purview DLP | Compliance Administrator | `SecurityActions.Read.All` or delegated Compliance PowerShell | AUTOMATABLE_WITH_E5 |
| `external_sharing_settings` | Graph beta SharePoint admin settings | `Get-SPOTenant`; `Get-PnPTenant` | SharePoint Online | SharePoint Administrator | `SharePointTenantSettings.Read.All` | AUTOMATABLE_NOW |
| `external_storage_providers_in_owa` | No Graph endpoint for OWA mailbox policy setting | `Get-OwaMailboxPolicy` | Exchange Online | Exchange Administrator | Delegated Exchange PowerShell | AUTOMATABLE_WITH_POWERSHELL |
| `full_calendar_schedules_able_to_be_shared_externally` | No complete app-only Graph endpoint for org sharing policies | `Get-SharingPolicy`; `Get-OrganizationConfig` | Exchange Online | Exchange Administrator | Delegated Exchange PowerShell | AUTOMATABLE_WITH_POWERSHELL |
| `getting_all_sites_with_sensitivity_keywords_on_a_tenant` | Graph site search | `Get-PnPTenantSite` | SharePoint Online | SharePoint Administrator | `Sites.Read.All` | AUTOMATABLE_NOW |
| `information_protection_labels_applied` | Graph beta information protection sensitivity labels | `Get-Label` | Microsoft 365 E5 / Purview Information Protection | Information Protection Administrator | `InformationProtectionPolicy.Read.All` | AUTOMATABLE_WITH_E5 |
| `sensitivity_labels_are_applied` | Graph beta information protection sensitivity labels | `Get-Label` | Microsoft 365 E5 / Purview Information Protection | Information Protection Administrator | `InformationProtectionPolicy.Read.All` | AUTOMATABLE_WITH_E5 |
| `sensitivity_labels_configured_and_applied` | Graph beta information protection sensitivity labels | `Get-Label`; `Get-LabelPolicy` | Microsoft 365 E5 / Purview Information Protection | Information Protection Administrator | `InformationProtectionPolicy.Read.All` | AUTOMATABLE_WITH_E5 |
| `sharepoint_and_onedrive_guest_access_expiry` | No stable Graph field for exact guest/link expiry policy | `Get-SPOTenant`; `Get-PnPTenant` | SharePoint Online | SharePoint Administrator | Delegated SharePoint/PnP PowerShell | AUTOMATABLE_WITH_POWERSHELL |
| `sharepoint_modern_authentication` | Graph beta SharePoint admin settings | `Get-SPOTenant`; `Get-PnPTenant` | SharePoint Online | SharePoint Administrator | `SharePointTenantSettings.Read.All` | AUTOMATABLE_NOW |
| `sharing_settings_external_internal` | Graph beta SharePoint admin settings | `Get-SPOTenant`; `Get-PnPTenant` | SharePoint Online | SharePoint Administrator | `SharePointTenantSettings.Read.All` | AUTOMATABLE_NOW |
| `checking_sharing_permissions_for_each_sites_on_a_tenant` | Graph site permissions | `Get-PnPTenantSite`; PnP sharing reports | SharePoint Online | SharePoint Administrator | `Sites.FullControl.All` | AUTOMATABLE_NOW |

## Microsoft Learn References

- Microsoft Graph information protection labels: https://learn.microsoft.com/graph/api/resources/security-informationprotectionlabel
- Microsoft Graph DLP/security APIs: https://learn.microsoft.com/graph/api/resources/security-api-overview
- Microsoft Graph site permissions: https://learn.microsoft.com/graph/api/site-list-permissions
- Microsoft Graph SharePoint admin settings: https://learn.microsoft.com/graph/api/resources/sharepointsettings
- Exchange Online `Get-OwaMailboxPolicy`: https://learn.microsoft.com/powershell/module/exchange/get-owamailboxpolicy
- Exchange Online `Get-SharingPolicy`: https://learn.microsoft.com/powershell/module/exchange/get-sharingpolicy
- Exchange Online `Get-OrganizationConfig`: https://learn.microsoft.com/powershell/module/exchange/get-organizationconfig
- Purview `Get-DlpCompliancePolicy`: https://learn.microsoft.com/powershell/module/exchange/get-dlpcompliancepolicy
- Purview retention cmdlets: https://learn.microsoft.com/powershell/module/exchange/get-retentioncompliancepolicy
- SharePoint Online tenant cmdlets: https://learn.microsoft.com/powershell/module/sharepoint-online/get-spotenant

