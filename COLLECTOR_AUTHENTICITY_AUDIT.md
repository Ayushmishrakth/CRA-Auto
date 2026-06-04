# Collector Authenticity Audit

Generated: 2026-06-02

## Classification Rules

`REAL_COLLECTOR` means the current runtime returns actual tenant evidence from Microsoft Graph or Microsoft 365 Reports.

`PLACEHOLDER_COLLECTOR` means the current runtime returns `NOT_SUPPORTED`, `LICENSING_LIMITATION`, `POWERSHELL_REQUIRED`, or `GRAPH_LIMITATION` instead of a tenant value.

## Summary

| Metric | Count |
|---|---:|
| Approved parameters | 64 |
| Real collectors | 48 |
| Placeholder collectors | 16 |
| Unsupported controls | 16 |
| Real collector coverage | 75.0% |

## Latest Assessment Status Counts

| status | count |
| --- | --- |
| FAIL | 33 |
| LICENSING_LIMITATION | 5 |
| NOT_SUPPORTED | 11 |
| PASS | 15 |

## Collector Matrix

| parameter_key | category | runtime_function | collector_type | authenticity | latest_result |
| --- | --- | --- | --- | --- | --- |
| account_enabled | Entra ID | collect_account_enabled | REAL_GRAPH | REAL_COLLECTOR | PASS |
| active_inactive_teams | Microsoft Teams | collect_active_inactive_teams | REAL_REPORT | REAL_COLLECTOR | PASS |
| active_sites_count | SharePoint Online | collect_active_sites_count | REAL_REPORT | REAL_COLLECTOR | FAIL |
| active_users_on_sharepoint | SharePoint Online | collect_active_users_on_sharepoint | REAL_REPORT | REAL_COLLECTOR | FAIL |
| activer_inactive_teams_users | Microsoft Teams | collect_activer_inactive_teams_users | REAL_REPORT | REAL_COLLECTOR | PASS |
| admin_consent_workflow | Entra ID | collect_admin_consent_workflow | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| assigned_license | Entra ID | collect_assigned_license | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| audit_log_retention_duration | Microsoft Purview | collect_audit_log_retention_duration | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| audit_logs_enabled | Microsoft Purview | collect_audit_logs_enabled | REAL_GRAPH | REAL_COLLECTOR | PASS |
| authentication_methods_enabled | Entra ID | collect_authentication_methods_enabled | REAL_GRAPH | REAL_COLLECTOR | PASS |
| cap_policies_for_risky_sign_ins | Entra ID | collect_cap_policies_for_risky_sign_ins | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| checking_sharing_permissions_for_each_sites_on_a_tenant | SharePoint Online | collect_checking_sharing_permissions_for_each_sites_on_a_tenant | LICENSING_LIMITATION | PLACEHOLDER_COLLECTOR | LICENSING_LIMITATION |
| compliance_score_overview | Microsoft Purview | collect_compliance_score_overview | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| conditional_access_policies_exclusion | Entra ID | collect_conditional_access_policies_exclusion | REAL_GRAPH | REAL_COLLECTOR | PASS |
| copilot_integration_enabled | Microsoft Teams | collect_copilot_integration_enabled | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| custom_banned_password_list | Entra ID | collect_custom_banned_password_list | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| customer_lockbox | M365 | collect_customer_lockbox | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| devices_without_compliance_policies | Entra ID | collect_devices_without_compliance_policies | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| dlp_rules_configured | Microsoft Purview | collect_dlp_rules_configured | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| emergency_access_accounts | Entra ID | collect_emergency_access_accounts | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| entra_tenant_creation_by_non_admin | Entra ID | collect_entra_tenant_creation_by_non_admin | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| entra_third_party_app_integrations | Entra ID | collect_entra_third_party_app_integrations | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| external_sharing_settings | OneDrive for Business | collect_external_sharing_settings | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| external_storage_providers_in_owa | Exchange Online | collect_external_storage_providers_in_owa | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| full_calendar_schedules_able_to_be_shared_externally | Exchange Online | collect_full_calendar_schedules_able_to_be_shared_externally | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| getting_all_sites_with_sensitivity_keywords_on_a_tenant | SharePoint Online | collect_getting_all_sites_with_sensitivity_keywords_on_a_tenant | LICENSING_LIMITATION | PLACEHOLDER_COLLECTOR | LICENSING_LIMITATION |
| global_administrator_accounts | Entra ID | collect_global_administrator_accounts | REAL_GRAPH | REAL_COLLECTOR | PASS |
| guest_access_enabled_disabled | Microsoft Teams | collect_guest_access_enabled_disabled | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| guest_invite_settings | Entra ID | collect_guest_invite_settings | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| guest_users_count | Entra ID | collect_guest_users_count | REAL_GRAPH | REAL_COLLECTOR | PASS |
| information_protection_labels_applied | Microsoft Purview | collect_information_protection_labels_applied | LICENSING_LIMITATION | PLACEHOLDER_COLLECTOR | LICENSING_LIMITATION |
| mailbox_storage_usage | Exchange Online | collect_mailbox_storage_usage | REAL_REPORT | REAL_COLLECTOR | PASS |
| mailboxes_status_active_inactive | Exchange Online | collect_mailboxes_status_active_inactive | REAL_REPORT | REAL_COLLECTOR | FAIL |
| meeting_policies_configuration | Microsoft Teams | collect_meeting_policies_configuration | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| meeting_recording_retention_policies | Microsoft Teams | collect_meeting_recording_retention_policies | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| meeting_transcription_enabled | Microsoft Teams | collect_meeting_transcription_enabled | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| minimum_number_of_owners | Microsoft Teams | collect_minimum_number_of_owners | REAL_GRAPH | REAL_COLLECTOR | PASS |
| non_admin_users_can_register_applications | Entra ID | collect_non_admin_users_can_register_applications | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| number_of_emails_read_received | Exchange Online | collect_number_of_emails_read_received | REAL_REPORT | REAL_COLLECTOR | FAIL |
| number_of_emails_sent | Exchange Online | collect_number_of_emails_sent | REAL_REPORT | REAL_COLLECTOR | FAIL |
| orphan_teams | Microsoft Teams | collect_orphan_teams | REAL_GRAPH | REAL_COLLECTOR | PASS |
| restricted_access_to_microsoft_entra_admin_centre | Entra ID | collect_restricted_access_to_microsoft_entra_admin_centre | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| secure_score_percentage | Microsoft Purview | collect_secure_score_percentage | REAL_GRAPH | REAL_COLLECTOR | PASS |
| self_service_password_reset_authentication_method | Entra ID | collect_self_service_password_reset_authentication_method | REAL_REPORT | REAL_COLLECTOR | PASS |
| sensitivity_labels_applied_to_teams | Microsoft Purview | collect_sensitivity_labels_applied_to_teams | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| sensitivity_labels_are_applied | Microsoft Purview | collect_sensitivity_labels_are_applied | LICENSING_LIMITATION | PLACEHOLDER_COLLECTOR | LICENSING_LIMITATION |
| sensitivity_labels_configured_and_applied | Microsoft Purview | collect_sensitivity_labels_configured_and_applied | LICENSING_LIMITATION | PLACEHOLDER_COLLECTOR | LICENSING_LIMITATION |
| sharepoint_and_onedrive_guest_access_expiry | SharePoint Online | collect_sharepoint_and_onedrive_guest_access_expiry | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| sharepoint_modern_authentication | SharePoint Online | collect_sharepoint_modern_authentication | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| sharing_settings_external_internal | SharePoint Online | collect_sharing_settings_external_internal | NOT_SUPPORTED | PLACEHOLDER_COLLECTOR | NOT_SUPPORTED |
| storage_quota_consumption | SharePoint Online | collect_storage_quota_consumption | REAL_REPORT | REAL_COLLECTOR | PASS |
| teams_anonymous_users | Microsoft Teams | collect_teams_anonymous_users | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| teams_channel_email_addresses | Microsoft Teams | collect_teams_channel_email_addresses | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| teams_external_unmanaged_user_communication | Microsoft Teams | collect_teams_external_unmanaged_user_communication | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| teams_file_storage_option | Microsoft Teams | collect_teams_file_storage_option | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| teams_lobby_bypass | Microsoft Teams | collect_teams_lobby_bypass | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| teams_meeting_chat | Microsoft Teams | collect_teams_meeting_chat | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| teams_with_external_users | Microsoft Teams | collect_teams_with_external_users | REAL_GRAPH | REAL_COLLECTOR | PASS |
| tenant_collaboration_invitations | Entra ID | collect_tenant_collaboration_invitations | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| third_party_apps_allowed | Microsoft Teams | collect_third_party_apps_allowed | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| total_active_users_on_onedrive | OneDrive for Business | collect_total_active_users_on_onedrive | REAL_REPORT | REAL_COLLECTOR | FAIL |
| user_consent_for_applications | Entra ID | collect_user_consent_for_applications | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| user_information | Entra ID | collect_user_information | REAL_GRAPH | REAL_COLLECTOR | FAIL |
| users_without_mfa | Entra ID | collect_users_without_mfa | REAL_GRAPH | REAL_COLLECTOR | FAIL |
