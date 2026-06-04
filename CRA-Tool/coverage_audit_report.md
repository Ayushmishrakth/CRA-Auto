# CRA Parameter Collection Coverage Audit

Generated: 2026-06-05

## Scope And Method

Read-only inspection of:

- `app/config/assessment_registry/parameters.json`
- `app/config/assessment_registry/collectors.json`
- `app/config/collector_manifest.json`
- `app/services/graph_cra_collector_service.py`
- `app/powershell/*`
- runtime services under `app/services/runtime_*`, `app/services/powershell/*`, and domain runtimes
- latest local SQLite assessment records in read-only mode

No source/config/runtime files were modified by this audit.

## Latest Assessment Snapshot

- assessment_id: `ba98c39187524dd1ac1ccaac060ad8f4`
- status: `completed`
- progress_pct: `100.0`
- tenant_id: `7aa280d0-4a2c-4438-8dee-ec4646f1e5d4`
- overall_score: `10.34`
- assessment_artifacts: `65`
- assessment_findings: `65`
- assessment_recommendations: `65`
- assessment_reports: `2`
- assessment_events: `333`
- collector_started_events: `65`
- collector_completed_events: `65`
- collector_failed_events: `0`

Latest finding status counts:

| Status | Count |
| --- | ---: |
| collection_error | 13 |
| fail | 30 |
| licensing_required | 4 |
| manual_validation | 1 |
| pass | 17 |

## Count Reconciliation

| Source | Count | Notes |
| --- | ---: | --- |
| Registry parameter count | 65 | Official parameter list |
| Registry collector count | 65 | One collector registry entry per official parameter |
| Manifest collector entries | 75 | Contains 10 extra non-official entries |
| Manifest unique official coverage | 65 | Missing official manifest keys: 0 |
| Graph runtime collector map | 71 | Contains 6 extra non-official entries |
| Graph runtime official coverage | 65 | All official parameters currently mapped to Graph runtime |
| Latest assessment collector.started events | 65 | Runtime attempted all official parameters |
| Latest assessment collector.completed events | 65 | Completed event emitted for all official parameters |
| Latest assessment artifacts/findings/recommendations | 65/65/65 | Persisted rows reconcile to 65 |

Extra manifest keys:

`assigned_license`, `checking_sharing_permissions_for_each_sites_on_a_tenant`, `device_without_compliance_policy`, `non_admin_users_can_register_applications`, `note_for_purview_if_e5_licenses_are_not_available_all_parameters_will_fail`, `restricted_access_to_microsoft_entra_admin_center`, `sensitive_sharepoint_site_excluded_from_copilot_search`, `sensitivity_labels_are_applied`, `teams_anonymous_users`, `teams_external_unmanaged_user_communication`

Extra Graph runtime keys:

`assigned_license`, `checking_sharing_permissions_for_each_sites_on_a_tenant`, `non_admin_users_can_register_applications`, `sensitivity_labels_are_applied`, `teams_anonymous_users`, `teams_external_unmanaged_user_communication`

## Category Totals

| Category | Count | Percentage |
| --- | ---: | ---: |
| A. Fully Automated | 47 | 72.31% |
| B. Partially Automated | 1 | 1.54% |
| C. Licensing Dependent | 4 | 6.15% |
| D. Collector Missing | 0 | 0.00% |
| E. Broken Collector | 13 | 20.00% |

## Summary Totals

- Total parameters: `65`
- Automated parameters: `47`
- Manual validation parameters: `1`
- Licensing dependent parameters: `4`
- Missing collectors: `0`
- Broken collectors: `13`

## Runtime Routing Finding

The runtime selector in `app/services/runtime_assessment_service.py` uses Graph first:

```text
if parameter_key in GRAPH_COLLECTORS:
    return "graph"
```

Because all 65 official parameter keys are present in `GRAPH_COLLECTORS`, the latest assessment routed all official parameters through Graph runtime, even where registry/manifest collector names still say `powershell.*`. This explains why several Exchange and Teams controls show `collection_error`: the code has PowerShell commands in scripts, but the current runtime path chose app-only Graph collectors.

## Complete Parameter Coverage Matrix

| ID | Parameter Key | Parameter Name | Service | Collector | Method | Implemented | Runtime Reachable | Evidence Produced | PASS/FAIL Logic | Latest Status | Category |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | active_inactive_teams | Active /Inactive teams | Teams | powershell.active_inactive_teams | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 2 | active_sites_count | Active Sites count | SharePoint | powershell.active_sites_count | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 3 | active_users_on_sharepoint | Active users on SharePoint | SharePoint | powershell.active_users_on_sharepoint | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 4 | activer_inactive_teams_users | Activer/Inactive Teams users | Teams | powershell.activer_inactive_teams_users | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 5 | copilot_integration_enabled | Copilot integration enabled | Teams | powershell.copilot_integration_enabled | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 6 | external_storage_providers_in_owa | External Storage Providers In OWA | Exchange | powershell.external_storage_providers_in_owa | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 7 | external_sharing_settings | External sharing settings | OneDrive | powershell.external_sharing_settings | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 8 | full_calendar_schedules_able_to_be_shared_externally | Full Calendar Schedules Able To Be Shared Externally | Exchange | powershell.full_calendar_schedules_able_to_be_shared_externally | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 9 | getting_all_sites_with_sensitivity_keywords_on_a_tenant | Getting all sites with Sensitivity keywords on a Tenant | Purview | powershell.getting_all_sites_with_sensitivity_keywords_on_a_tenant | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 10 | guest_access_enabled_disabled | Guest access enabled / disabled | Teams | powershell.guest_access_enabled_disabled | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 11 | mailbox_storage_usage | Mailbox Storage usage | Exchange | powershell.mailbox_storage_usage | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 12 | mailboxes_status_active_inactive | Mailboxes Status (Active/Inactive) | Exchange | powershell.mailboxes_status_active_inactive | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 13 | meeting_policies_configuration | Meeting Policies configuration | Teams | powershell.meeting_policies_configuration | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 14 | meeting_recording_retention_policies | Meeting recording retention policies | Purview | powershell.meeting_recording_retention_policies | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 15 | meeting_transcription_enabled | Meeting transcription enabled | Teams | powershell.meeting_transcription_enabled | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 16 | minimum_number_of_owners | Minimum number of owners | Teams | powershell.minimum_number_of_owners | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 17 | number_of_emails_read_received | Number of emails read/received | Exchange | powershell.number_of_emails_read_received | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 18 | number_of_emails_sent | Number of emails sent | Exchange | powershell.number_of_emails_sent | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 19 | orphan_teams | Orphan Teams | Teams | powershell.orphan_teams | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 20 | sharepoint_and_onedrive_guest_access_expiry | SharePoint & OneDrive Guest Access Expiry | OneDrive | powershell.sharepoint_and_onedrive_guest_access_expiry | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 21 | sharepoint_modern_authentication | SharePoint - Modern Authentication | SharePoint | powershell.sharepoint_modern_authentication | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 22 | sharing_settings_external_internal | Sharing Settings (External/Internal) | SharePoint | powershell.sharing_settings_external_internal | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 23 | storage_quota_consumption | Storage Quota consumption | SharePoint | powershell.storage_quota_consumption | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 24 | teams_channel_email_addresses | Teams - Channel Email Addresses | Exchange | powershell.teams_channel_email_addresses | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 25 | teams_file_storage_option | Teams - File Storage Option | Teams | powershell.teams_file_storage_option | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 26 | teams_lobby_bypass | Teams - Lobby Bypass | Teams | powershell.teams_lobby_bypass | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 27 | teams_meeting_chat | Teams - Meeting Chat | Teams | powershell.teams_meeting_chat | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 28 | teams_with_external_users | Teams with external users | Teams | powershell.teams_with_external_users | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 29 | third_party_apps_allowed | Third-party apps allowed | Teams | powershell.third_party_apps_allowed | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |
| 30 | total_active_users_on_onedrive | Total active users on OneDrive | OneDrive | powershell.total_active_users_on_onedrive | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 31 | audit_logs_enabled | Audit Logs enabled | Purview | powershell.audit_logs_enabled | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 32 | audit_log_retention_duration | Audit log retention duration | Purview | portal.audit_log_retention_duration | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 33 | compliance_score_overview | Compliance Score overview | Purview | portal.compliance_score_overview | Graph | YES | YES | NO | NO | manual_validation | B. Partially Automated |
| 34 | dlp_rules_configured | DLP rules configured | Purview | powershell.dlp_rules_configured | Graph | YES | YES | NO | NO | licensing_required | C. Licensing Dependent |
| 35 | information_protection_labels_applied | Information Protection Labels applied | Purview | powershell.information_protection_labels_applied | Graph | YES | YES | NO | NO | licensing_required | C. Licensing Dependent |
| 36 | secure_score_percentage | Secure Score percentage | Purview | portal.secure_score_percentage | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 37 | sensitivity_labels_applied_to_teams | Sensitivity Labels applied to Teams | Purview | powershell.sensitivity_labels_applied_to_teams | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 38 | sensitivity_labels_configured_and_applied | Sensitivity Labels configured and applied | Purview | powershell.sensitivity_labels_configured_and_applied | Graph | YES | YES | NO | NO | licensing_required | C. Licensing Dependent |
| 39 | days_to_retain_a_deleted_user_s_onedrive | Days to retain a deleted user's OneDrive | OneDrive | powershell.days_to_retain_a_deleted_user_s_onedrive | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 40 | inactive_site_policies | Inactive site policies | SharePoint | powershell.inactive_site_policies | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 41 | site_ownership_policies | Site Ownership policies | SharePoint | powershell.site_ownership_policies | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 42 | account_enabled | Account enabled | Entra | powershell.account_enabled | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 43 | admin_consent_workflow | Admin Consent Workflow | Entra | powershell.admin_consent_workflow | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 44 | authentication_methods_enabled | Authentication methods enabled | Entra | powershell.authentication_methods_enabled | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 45 | cap_policies_for_risky_sign_ins | CAP policies for risky sign-ins | Entra | powershell.cap_policies_for_risky_sign_ins | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 46 | conditional_access_policies_exclusion | Conditional Access Policies (Exclusion) | Entra | powershell.conditional_access_policies_exclusion | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 47 | custom_banned_password_list | Custom Banned Password List | Entra | graph.custom_banned_password_list | Graph | YES | YES | NO | NO | licensing_required | C. Licensing Dependent |
| 48 | devices_without_compliance_policies | Devices without compliance policies | Entra | powershell.devices_without_compliance_policies | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 49 | emergency_access_accounts | Emergency Access Accounts | Entra | manual.emergency_access_accounts | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 50 | entra_tenant_creation_by_non_admin | Entra - Tenant Creation By Non-Admin | Entra | powershell.entra_tenant_creation_by_non_admin | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 51 | entra_third_party_app_integrations | Entra - Third Party App Integrations | Entra | powershell.entra_third_party_app_integrations | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 52 | global_administrator_accounts | Global Administrator Accounts | Entra | powershell.global_administrator_accounts | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 53 | guest_invite_settings | Guest Invite Settings | Entra | powershell.guest_invite_settings | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 54 | guest_users_count | Guest users count | Entra | powershell.guest_users_count | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 55 | restricted_access_to_microsoft_entra_admin_centre | Restricted Access To Microsoft Entra Admin Centre | Entra | portal.restricted_access_to_microsoft_entra_admin_centre | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 56 | self_service_password_reset_authentication_method | Self-Service Password Reset Authentication Method | Entra | portal.self_service_password_reset_authentication_method | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 57 | tenant_collaboration_invitations | Tenant Collaboration Invitations | Entra | powershell.tenant_collaboration_invitations | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 58 | user_consent_for_applications | User Consent For Applications | Entra | portal.user_consent_for_applications | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 59 | user_information | User Information | Entra | powershell.user_information | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 60 | users_without_mfa | Users without MFA | Entra | powershell.users_without_mfa | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 61 | auto_expiration_policy_for_inactive_m365_groups | Auto-expiration policy for M365 Groups | M365 | powershell.auto_expiration_policy_for_inactive_m365_groups | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 62 | expiration_policy_for_anyone_links | Expiration Policy for Anyone links | SharePoint | powershell.expiration_policy_for_anyone_links | Graph | YES | YES | YES | YES | fail | A. Fully Automated |
| 63 | permission_setting_for_anyone_links | Permission Settings for anyone links | SharePoint | powershell.permission_setting_for_anyone_links | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 64 | teams_with_external_guest_as_owner | Teams with external guest as owner | Teams | powershell.teams_with_external_guest_as_owner | Graph | YES | YES | YES | YES | pass | A. Fully Automated |
| 65 | customer_lockbox | Customer Lockbox | Purview | powershell.customer_lockbox | Graph | YES | YES | NO | NO | collection_error | E. Broken Collector |

## Parameters Not Fully Automated

| Parameter Key | Reason | Missing API | Missing Permission | Missing PowerShell Command | Manual Validation Requirement | Licensing Dependency |
| --- | --- | --- | --- | --- | --- | --- |
| copilot_integration_enabled | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| external_storage_providers_in_owa | This control is fully automatable with Exchange Online PowerShell. The app-only Graph runtime cannot read OWA mailbox policy settings directly, so this collector must run through delegated Exchange automation. | Get-OwaMailboxPolicy / Select-Object Identity,AdditionalStorageProvidersAvailable |  | Get-OwaMailboxPolicy / Select-Object Identity,AdditionalStorageProvidersAvailable |  |  |
| full_calendar_schedules_able_to_be_shared_externally | This control is fully automatable with Exchange Online PowerShell sharing policies. The app-only Graph runtime cannot read this tenant sharing policy directly. | Get-SharingPolicy / Format-List Domains,Enabled,Default |  | Get-SharingPolicy / Format-List Domains,Enabled,Default |  |  |
| guest_access_enabled_disabled | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| meeting_policies_configuration | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| meeting_recording_retention_policies | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| meeting_transcription_enabled | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| teams_channel_email_addresses | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| teams_file_storage_option | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| teams_lobby_bypass | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| teams_meeting_chat | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| third_party_apps_allowed | Requested API is not supported in application-only context | Microsoft Teams admin policy Graph/PowerShell | TeamSettings.Read.All, Teams admin consent | Teams PowerShell policy cmdlets for this control |  |  |
| compliance_score_overview | Microsoft does not expose a stable tenant automation endpoint for this control in the current app-only runtime. |  |  |  | Open Compliance Manager, export or capture the current compliance score overview, and attach the tenant score evidence to the assessment package. |  |
| dlp_rules_configured | Microsoft Purview Data Loss Prevention evidence requires Microsoft 365 E5 or Microsoft Purview DLP, Compliance Administrator or DLP Compliance Management, and Graph permission(s): SecurityActions.Read.All. | https://graph.microsoft.com/beta/security/dataLossPrevention/policies | SecurityActions.Read.All |  |  | Microsoft 365 E5 or Microsoft Purview DLP |
| information_protection_labels_applied | Microsoft Purview Information Protection evidence requires Microsoft 365 E5 or Microsoft Purview Information Protection, Compliance Administrator or Information Protection Administrator, and Graph permission(s): InformationProtectionPolicy.Read.All. | https://graph.microsoft.com/beta/security/informationProtection/sensitivityLabels | InformationProtectionPolicy.Read.All |  |  | Microsoft 365 E5 or Microsoft Purview Information Protection |
| sensitivity_labels_configured_and_applied | Microsoft Purview Information Protection evidence requires Microsoft 365 E5 or Microsoft Purview Information Protection, Compliance Administrator or Information Protection Administrator, and Graph permission(s): InformationProtectionPolicy.Read.All. | https://graph.microsoft.com/beta/security/informationProtection/sensitivityLabels | InformationProtectionPolicy.Read.All |  |  | Microsoft 365 E5 or Microsoft Purview Information Protection |
| custom_banned_password_list | Entra ID Password Protection evidence requires Microsoft Entra ID P1 or P2, Authentication Policy Administrator or Global Administrator, and Graph permission(s): Policy.Read.All. | https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/password | Policy.Read.All |  |  | Microsoft Entra ID P1 or P2 |
| customer_lockbox | This control is fully automatable with Exchange Online PowerShell organization configuration. The app-only Graph runtime cannot read CustomerLockBoxEnabled directly. | Get-OrganizationConfig / Select-Object CustomerLockBoxEnabled |  | Get-OrganizationConfig / Select-Object CustomerLockBoxEnabled |  |  |

## Final Finding

The claimed official parameter execution count matches reality for the latest assessment: 65 official parameters were attempted and persisted as 65 artifacts, 65 findings, and 65 recommendations.

The collector definition counts do not perfectly match the official catalog:

- `parameters.json`: 65 official parameters
- `collectors.json`: 65 official collector entries
- `collector_manifest.json`: 75 entries, including 10 extra non-official/legacy keys
- `GRAPH_COLLECTORS`: 71 entries, including 6 extra non-official/legacy keys

The practical automation coverage from the latest assessment is 47/65 = 72.31% fully automated PASS/FAIL. The remaining 18 parameters are not fully automated because of collection errors, licensing requirements, or manual validation.
