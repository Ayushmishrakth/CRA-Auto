# Routing Correction Report

## Summary

| Metric | Value |
| --- | ---: |
| Official parameters audited | 65 |
| Python Graph collectors available for official parameters | 65 |
| Previously routed to PowerShell by manifest-first rule | 64 |
| Routed to Graph after fix | 65 |
| Routed to PowerShell after fix | 0 |

## All Parameter Routing Audit

| parameter_key | current collector | previous runtime | corrected runtime | should_be_graph | should_be_powershell | should_be_manual |
| --- | --- | --- | --- | --- | --- | --- |
| `active_inactive_teams` | `powershell.active_inactive_teams` | `powershell` | `graph` | True | False | False |
| `active_sites_count` | `powershell.active_sites_count` | `powershell` | `graph` | True | False | False |
| `active_users_on_sharepoint` | `powershell.active_users_on_sharepoint` | `powershell` | `graph` | True | False | False |
| `activer_inactive_teams_users` | `powershell.activer_inactive_teams_users` | `powershell` | `graph` | True | False | False |
| `copilot_integration_enabled` | `powershell.copilot_integration_enabled` | `powershell` | `graph` | True | False | False |
| `external_storage_providers_in_owa` | `powershell.external_storage_providers_in_owa` | `powershell` | `graph` | True | False | False |
| `external_sharing_settings` | `powershell.external_sharing_settings` | `powershell` | `graph` | True | False | False |
| `full_calendar_schedules_able_to_be_shared_externally` | `powershell.full_calendar_schedules_able_to_be_shared_externally` | `powershell` | `graph` | True | False | False |
| `getting_all_sites_with_sensitivity_keywords_on_a_tenant` | `powershell.getting_all_sites_with_sensitivity_keywords_on_a_tenant` | `powershell` | `graph` | True | False | False |
| `guest_access_enabled_disabled` | `powershell.guest_access_enabled_disabled` | `powershell` | `graph` | True | False | False |
| `mailbox_storage_usage` | `powershell.mailbox_storage_usage` | `powershell` | `graph` | True | False | False |
| `mailboxes_status_active_inactive` | `powershell.mailboxes_status_active_inactive` | `powershell` | `graph` | True | False | False |
| `meeting_policies_configuration` | `powershell.meeting_policies_configuration` | `powershell` | `graph` | True | False | False |
| `meeting_recording_retention_policies` | `powershell.meeting_recording_retention_policies` | `powershell` | `graph` | True | False | False |
| `meeting_transcription_enabled` | `powershell.meeting_transcription_enabled` | `powershell` | `graph` | True | False | False |
| `minimum_number_of_owners` | `powershell.minimum_number_of_owners` | `powershell` | `graph` | True | False | False |
| `number_of_emails_read_received` | `powershell.number_of_emails_read_received` | `powershell` | `graph` | True | False | False |
| `number_of_emails_sent` | `powershell.number_of_emails_sent` | `powershell` | `graph` | True | False | False |
| `orphan_teams` | `powershell.orphan_teams` | `powershell` | `graph` | True | False | False |
| `sharepoint_and_onedrive_guest_access_expiry` | `powershell.sharepoint_and_onedrive_guest_access_expiry` | `powershell` | `graph` | True | False | False |
| `sharepoint_modern_authentication` | `powershell.sharepoint_modern_authentication` | `powershell` | `graph` | True | False | False |
| `sharing_settings_external_internal` | `powershell.sharing_settings_external_internal` | `powershell` | `graph` | True | False | False |
| `storage_quota_consumption` | `powershell.storage_quota_consumption` | `powershell` | `graph` | True | False | False |
| `teams_channel_email_addresses` | `powershell.teams_channel_email_addresses` | `powershell` | `graph` | True | False | False |
| `teams_file_storage_option` | `powershell.teams_file_storage_option` | `powershell` | `graph` | True | False | False |
| `teams_lobby_bypass` | `powershell.teams_lobby_bypass` | `powershell` | `graph` | True | False | False |
| `teams_meeting_chat` | `powershell.teams_meeting_chat` | `powershell` | `graph` | True | False | False |
| `teams_with_external_users` | `powershell.teams_with_external_users` | `powershell` | `graph` | True | False | False |
| `third_party_apps_allowed` | `powershell.third_party_apps_allowed` | `powershell` | `graph` | True | False | False |
| `total_active_users_on_onedrive` | `powershell.total_active_users_on_onedrive` | `powershell` | `graph` | True | False | False |
| `audit_logs_enabled` | `powershell.audit_logs_enabled` | `powershell` | `graph` | True | False | False |
| `audit_log_retention_duration` | `portal.audit_log_retention_duration` | `powershell` | `graph` | True | False | False |
| `compliance_score_overview` | `portal.compliance_score_overview` | `powershell` | `graph` | True | False | False |
| `dlp_rules_configured` | `powershell.dlp_rules_configured` | `powershell` | `graph` | True | False | False |
| `information_protection_labels_applied` | `powershell.information_protection_labels_applied` | `powershell` | `graph` | True | False | False |
| `secure_score_percentage` | `portal.secure_score_percentage` | `powershell` | `graph` | True | False | False |
| `sensitivity_labels_applied_to_teams` | `powershell.sensitivity_labels_applied_to_teams` | `powershell` | `graph` | True | False | False |
| `sensitivity_labels_configured_and_applied` | `powershell.sensitivity_labels_configured_and_applied` | `powershell` | `graph` | True | False | False |
| `days_to_retain_a_deleted_user_s_onedrive` | `powershell.days_to_retain_a_deleted_user_s_onedrive` | `powershell` | `graph` | True | False | False |
| `inactive_site_policies` | `powershell.inactive_site_policies` | `powershell` | `graph` | True | False | False |
| `site_ownership_policies` | `powershell.site_ownership_policies` | `powershell` | `graph` | True | False | False |
| `account_enabled` | `powershell.account_enabled` | `powershell` | `graph` | True | False | False |
| `admin_consent_workflow` | `powershell.admin_consent_workflow` | `powershell` | `graph` | True | False | False |
| `authentication_methods_enabled` | `powershell.authentication_methods_enabled` | `powershell` | `graph` | True | False | False |
| `cap_policies_for_risky_sign_ins` | `powershell.cap_policies_for_risky_sign_ins` | `powershell` | `graph` | True | False | False |
| `conditional_access_policies_exclusion` | `powershell.conditional_access_policies_exclusion` | `powershell` | `graph` | True | False | False |
| `custom_banned_password_list` | `portal.custom_banned_password_list` | `powershell` | `graph` | True | False | False |
| `devices_without_compliance_policies` | `powershell.devices_without_compliance_policies` | `powershell` | `graph` | True | False | False |
| `emergency_access_accounts` | `manual.emergency_access_accounts` | `powershell` | `graph` | True | False | False |
| `entra_tenant_creation_by_non_admin` | `powershell.entra_tenant_creation_by_non_admin` | `powershell` | `graph` | True | False | False |
| `entra_third_party_app_integrations` | `powershell.entra_third_party_app_integrations` | `powershell` | `graph` | True | False | False |
| `global_administrator_accounts` | `powershell.global_administrator_accounts` | `graph` | `graph` | True | False | False |
| `guest_invite_settings` | `powershell.guest_invite_settings` | `powershell` | `graph` | True | False | False |
| `guest_users_count` | `powershell.guest_users_count` | `powershell` | `graph` | True | False | False |
| `restricted_access_to_microsoft_entra_admin_centre` | `portal.restricted_access_to_microsoft_entra_admin_centre` | `powershell` | `graph` | True | False | False |
| `self_service_password_reset_authentication_method` | `portal.self_service_password_reset_authentication_method` | `powershell` | `graph` | True | False | False |
| `tenant_collaboration_invitations` | `powershell.tenant_collaboration_invitations` | `powershell` | `graph` | True | False | False |
| `user_consent_for_applications` | `portal.user_consent_for_applications` | `powershell` | `graph` | True | False | False |
| `user_information` | `powershell.user_information` | `powershell` | `graph` | True | False | False |
| `users_without_mfa` | `powershell.users_without_mfa` | `powershell` | `graph` | True | False | False |
| `auto_expiration_policy_for_inactive_m365_groups` | `powershell.auto_expiration_policy_for_inactive_m365_groups` | `powershell` | `graph` | True | False | False |
| `expiration_policy_for_anyone_links` | `powershell.expiration_policy_for_anyone_links` | `powershell` | `graph` | True | False | False |
| `permission_setting_for_anyone_links` | `powershell.permission_setting_for_anyone_links` | `powershell` | `graph` | True | False | False |
| `teams_with_external_guest_as_owner` | `powershell.teams_with_external_guest_as_owner` | `powershell` | `graph` | True | False | False |
| `customer_lockbox` | `powershell.customer_lockbox` | `powershell` | `graph` | True | False | False |

## Incorrectly Routed Before Fix

- `active_inactive_teams`
- `active_sites_count`
- `active_users_on_sharepoint`
- `activer_inactive_teams_users`
- `copilot_integration_enabled`
- `external_storage_providers_in_owa`
- `external_sharing_settings`
- `full_calendar_schedules_able_to_be_shared_externally`
- `getting_all_sites_with_sensitivity_keywords_on_a_tenant`
- `guest_access_enabled_disabled`
- `mailbox_storage_usage`
- `mailboxes_status_active_inactive`
- `meeting_policies_configuration`
- `meeting_recording_retention_policies`
- `meeting_transcription_enabled`
- `minimum_number_of_owners`
- `number_of_emails_read_received`
- `number_of_emails_sent`
- `orphan_teams`
- `sharepoint_and_onedrive_guest_access_expiry`
- `sharepoint_modern_authentication`
- `sharing_settings_external_internal`
- `storage_quota_consumption`
- `teams_channel_email_addresses`
- `teams_file_storage_option`
- `teams_lobby_bypass`
- `teams_meeting_chat`
- `teams_with_external_users`
- `third_party_apps_allowed`
- `total_active_users_on_onedrive`
- `audit_logs_enabled`
- `audit_log_retention_duration`
- `compliance_score_overview`
- `dlp_rules_configured`
- `information_protection_labels_applied`
- `secure_score_percentage`
- `sensitivity_labels_applied_to_teams`
- `sensitivity_labels_configured_and_applied`
- `days_to_retain_a_deleted_user_s_onedrive`
- `inactive_site_policies`
- `site_ownership_policies`
- `account_enabled`
- `admin_consent_workflow`
- `authentication_methods_enabled`
- `cap_policies_for_risky_sign_ins`
- `conditional_access_policies_exclusion`
- `custom_banned_password_list`
- `devices_without_compliance_policies`
- `emergency_access_accounts`
- `entra_tenant_creation_by_non_admin`
- `entra_third_party_app_integrations`
- `guest_invite_settings`
- `guest_users_count`
- `restricted_access_to_microsoft_entra_admin_centre`
- `self_service_password_reset_authentication_method`
- `tenant_collaboration_invitations`
- `user_consent_for_applications`
- `user_information`
- `users_without_mfa`
- `auto_expiration_policy_for_inactive_m365_groups`
- `expiration_policy_for_anyone_links`
- `permission_setting_for_anyone_links`
- `teams_with_external_guest_as_owner`
- `customer_lockbox`

## Code Change

Changed `runtime_assessment_service._select_runtime()` so existing Python Graph collectors are selected before manifest PowerShell flags.
