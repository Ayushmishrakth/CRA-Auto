# Collector Coverage Completion Report

Generated: 2026-06-02

## Summary

Phase 8.8 completed the remaining approved collector registrations and runtime collectors.

The platform now has collector coverage for all approved parameters:

| Metric | Value |
|---|---:|
| Approved parameters | 65 |
| Implemented collectors | 65 |
| Collector coverage | 100% |
| Duplicate parameters | 0 |
| Extra runtime collector keys | 0 |

## Files Changed

| File | Change |
|---|---|
| `CRA-Tool/app/services/graph_cra_collector_service.py` | Added the remaining 21 collectors, registered all 65 collector keys, added traceable limitation result helpers, hardened report/site collection errors, and added `remediation` to the collector output contract. |

## Newly Implemented Parameters

### Microsoft Purview

| Parameter | Collector Evidence |
|---|---|
| `compliance_score_overview` | Purview portal compliance score limitation evidence. |
| `secure_score_percentage` | Microsoft Graph `/security/secureScores?$top=1`. |
| `audit_log_retention_duration` | Purview retention PowerShell command requirement evidence. |
| `audit_logs_enabled` | Microsoft Graph `/auditLogs/directoryAudits?$top=1`. |
| `dlp_rules_configured` | Microsoft Graph beta DLP endpoint response/limitation evidence. |
| `information_protection_labels_applied` | Microsoft Graph beta sensitivity label response/limitation evidence. |
| `sensitivity_labels_configured_and_applied` | Microsoft Graph beta sensitivity label response/limitation evidence. |
| `sensitivity_labels_applied_to_teams` | Microsoft Graph Teams groups with `assignedLabels`. |
| `sensitivity_labels_are_applied` | Microsoft Graph beta sensitivity label response/limitation evidence. |

### Exchange Online

| Parameter | Collector Evidence |
|---|---|
| `external_storage_providers_in_owa` | Exchange Online PowerShell command requirement evidence. |
| `full_calendar_schedules_able_to_be_shared_externally` | Exchange Online sharing policy / organization config command requirement evidence. |

### Entra ID

| Parameter | Collector Evidence |
|---|---|
| `emergency_access_accounts` | Microsoft Graph Global Administrator role membership inspection. |
| `custom_banned_password_list` | Microsoft Graph beta password authentication method configuration response/limitation evidence. |

### SharePoint / OneDrive

| Parameter | Collector Evidence |
|---|---|
| `external_sharing_settings` | SharePoint Online PowerShell command requirement evidence. |
| `sharepoint_modern_authentication` | SharePoint Online legacy auth PowerShell command requirement evidence. |
| `storage_quota_consumption` | Microsoft 365 Reports `/reports/getSharePointSiteUsageDetail(period='D30')`. |
| `sharing_settings_external_internal` | SharePoint Online sharing settings command requirement evidence. |
| `sharepoint_and_onedrive_guest_access_expiry` | SharePoint Online guest/link expiry command requirement evidence. |
| `checking_sharing_permissions_for_each_sites_on_a_tenant` | Microsoft Graph `/sites?search=*` response/limitation evidence. |
| `getting_all_sites_with_sensitivity_keywords_on_a_tenant` | Microsoft Graph `/sites?search=*` sensitivity keyword inspection or Graph limitation evidence. |

### Microsoft 365

| Parameter | Collector Evidence |
|---|---|
| `customer_lockbox` | Exchange Online organization config command requirement evidence. |

## Final Validation

Fresh assessment:

| Field | Value |
|---|---|
| Assessment ID | `ecf07294-dc31-47a2-8813-90638daa644a` |
| Job ID | `6da709e1-927f-4529-8d7d-f3fc74f29e46` |
| Assessment status | `completed` |
| Progress | `100.0` |
| Collector total | `65` |
| Collector collected | `65` |
| Collector incomplete | `0` |
| Graph calls | `81` |
| Artifacts generated | `65` |
| Findings generated | `65` |
| Recommendations generated | `65` |
| Reports generated | `2` |
| Remediation field persisted in artifacts | `65` |

Scores:

| Score | Value |
|---|---:|
| Overall | 15.74 |
| Identity | 0.0 |
| Security | 99.66 |
| Compliance | 0.0 |
| Collaboration | 0.0 |
| Licensing | 99.0 |

Finding status counts:

| Status | Count |
|---|---:|
| `pass` | 16 |
| `fail` | 33 |
| `licensing_limitation` | 5 |
| `not_supported` | 11 |

## Coverage By Area

| Area | Approved Parameters | Implemented Collectors | Coverage |
|---|---:|---:|---:|
| Entra ID / Intune | 22 | 22 | 100% |
| Exchange | 6 | 6 | 100% |
| Teams | 17 | 17 | 100% |
| SharePoint | 8 | 8 | 100% |
| OneDrive | 2 | 2 | 100% |
| Purview | 9 | 9 | 100% |
| Microsoft 365 | 1 | 1 | 100% |

## Evidence Notes

No mock data was introduced.

Collectors use one of these evidence classes:

- Direct Microsoft Graph response data.
- Microsoft 365 Reports CSV output.
- Microsoft Graph error/limitation payloads.
- Traceable PowerShell-required evidence where the approved source is PowerShell-only and no delegated PowerShell session exists in the app-only runtime.

PowerShell-only controls return `not_supported` findings with:

- `powershell_command`
- `collection_status`
- `actual_value`
- `expected_value`
- `pass_criteria`
- `fail_criteria`
- `reasoning`
- `remediation`

Graph/Premium-gated controls return `licensing_limitation` or `not_supported` with the Microsoft response payload preserved in evidence.

## Verification

Backend compilation:

`.\venv\Scripts\python.exe -m py_compile app\services\graph_cra_collector_service.py app\services\runtime_assessment_service.py`

Result: passed.

Fresh runtime validation:

Result: completed with 65/65 collectors, 65 artifacts, 65 findings, 65 recommendations, and report generation.

## Remaining Operational Notes

Several controls are approved in the specification but require delegated Microsoft 365 PowerShell or portal-only evidence for exact values. The current app-only runtime records this accurately as traceable `not_supported` evidence instead of fabricating tenant values.

