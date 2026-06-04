# Collector Execution Trace V2

## Summary

| Metric | Count |
| --- | ---: |
| Collectors expected | 65 |
| Collectors started | 65 |
| Collectors completed | 1 |
| Collectors failed | 64 |
| Graph collectors started | 1 |
| PowerShell collectors started | 64 |
| NotImplementedError failures | 64 |

## Executed Collectors

| Parameter Key | Collector | Runtime | Script | Completed | Failed | Artifact Status | Finding Status | Exception |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `account_enabled` | `powershell.account_enabled` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `active_inactive_teams` | `powershell.active_inactive_teams` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `active_sites_count` | `powershell.active_sites_count` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `active_users_on_sharepoint` | `powershell.active_users_on_sharepoint` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `activer_inactive_teams_users` | `powershell.activer_inactive_teams_users` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `admin_consent_workflow` | `powershell.admin_consent_workflow` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `audit_log_retention_duration` | `portal.audit_log_retention_duration` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `audit_logs_enabled` | `powershell.audit_logs_enabled` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `authentication_methods_enabled` | `powershell.authentication_methods_enabled` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `auto_expiration_policy_for_inactive_m365_groups` | `powershell.auto_expiration_policy_for_inactive_m365_groups` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `cap_policies_for_risky_sign_ins` | `powershell.cap_policies_for_risky_sign_ins` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `compliance_score_overview` | `portal.compliance_score_overview` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `conditional_access_policies_exclusion` | `powershell.conditional_access_policies_exclusion` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `copilot_integration_enabled` | `powershell.copilot_integration_enabled` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `custom_banned_password_list` | `portal.custom_banned_password_list` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `customer_lockbox` | `powershell.customer_lockbox` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `days_to_retain_a_deleted_user_s_onedrive` | `powershell.days_to_retain_a_deleted_user_s_onedrive` | `powershell` | `app/powershell/onedrive/onedrive_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `devices_without_compliance_policies` | `powershell.devices_without_compliance_policies` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `dlp_rules_configured` | `powershell.dlp_rules_configured` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `emergency_access_accounts` | `manual.emergency_access_accounts` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `entra_tenant_creation_by_non_admin` | `powershell.entra_tenant_creation_by_non_admin` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `entra_third_party_app_integrations` | `powershell.entra_third_party_app_integrations` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `expiration_policy_for_anyone_links` | `powershell.expiration_policy_for_anyone_links` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `external_sharing_settings` | `powershell.external_sharing_settings` | `powershell` | `app/powershell/onedrive/onedrive_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `external_storage_providers_in_owa` | `powershell.external_storage_providers_in_owa` | `powershell` | `app/powershell/exchange/exchange_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `full_calendar_schedules_able_to_be_shared_externally` | `powershell.full_calendar_schedules_able_to_be_shared_externally` | `powershell` | `app/powershell/exchange/exchange_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `getting_all_sites_with_sensitivity_keywords_on_a_tenant` | `powershell.getting_all_sites_with_sensitivity_keywords_on_a_tenant` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `global_administrator_accounts` | `powershell.global_administrator_accounts` | `graph` | `app/powershell/entra/entra_master.ps1` | yes | no | `collected` | `pass` | `` |
| `guest_access_enabled_disabled` | `powershell.guest_access_enabled_disabled` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `guest_invite_settings` | `powershell.guest_invite_settings` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `guest_users_count` | `powershell.guest_users_count` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `inactive_site_policies` | `powershell.inactive_site_policies` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `information_protection_labels_applied` | `powershell.information_protection_labels_applied` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `mailbox_storage_usage` | `powershell.mailbox_storage_usage` | `powershell` | `app/powershell/exchange/exchange_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `mailboxes_status_active_inactive` | `powershell.mailboxes_status_active_inactive` | `powershell` | `app/powershell/exchange/exchange_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `meeting_policies_configuration` | `powershell.meeting_policies_configuration` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `meeting_recording_retention_policies` | `powershell.meeting_recording_retention_policies` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `meeting_transcription_enabled` | `powershell.meeting_transcription_enabled` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `minimum_number_of_owners` | `powershell.minimum_number_of_owners` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `number_of_emails_read_received` | `powershell.number_of_emails_read_received` | `powershell` | `app/powershell/exchange/exchange_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `number_of_emails_sent` | `powershell.number_of_emails_sent` | `powershell` | `app/powershell/exchange/exchange_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `orphan_teams` | `powershell.orphan_teams` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `permission_setting_for_anyone_links` | `powershell.permission_setting_for_anyone_links` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `restricted_access_to_microsoft_entra_admin_centre` | `portal.restricted_access_to_microsoft_entra_admin_centre` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `secure_score_percentage` | `portal.secure_score_percentage` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `self_service_password_reset_authentication_method` | `portal.self_service_password_reset_authentication_method` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `sensitivity_labels_applied_to_teams` | `powershell.sensitivity_labels_applied_to_teams` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `sensitivity_labels_configured_and_applied` | `powershell.sensitivity_labels_configured_and_applied` | `powershell` | `app/powershell/purview/purview_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `sharepoint_and_onedrive_guest_access_expiry` | `powershell.sharepoint_and_onedrive_guest_access_expiry` | `powershell` | `app/powershell/onedrive/onedrive_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `sharepoint_modern_authentication` | `powershell.sharepoint_modern_authentication` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `sharing_settings_external_internal` | `powershell.sharing_settings_external_internal` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `site_ownership_policies` | `powershell.site_ownership_policies` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `storage_quota_consumption` | `powershell.storage_quota_consumption` | `powershell` | `app/powershell/sharepoint/sharepoint_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `teams_channel_email_addresses` | `powershell.teams_channel_email_addresses` | `powershell` | `app/powershell/exchange/exchange_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `teams_file_storage_option` | `powershell.teams_file_storage_option` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `teams_lobby_bypass` | `powershell.teams_lobby_bypass` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `teams_meeting_chat` | `powershell.teams_meeting_chat` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `teams_with_external_guest_as_owner` | `powershell.teams_with_external_guest_as_owner` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `teams_with_external_users` | `powershell.teams_with_external_users` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `tenant_collaboration_invitations` | `powershell.tenant_collaboration_invitations` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `third_party_apps_allowed` | `powershell.third_party_apps_allowed` | `powershell` | `app/powershell/teams/teams_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `total_active_users_on_onedrive` | `powershell.total_active_users_on_onedrive` | `powershell` | `app/powershell/onedrive/onedrive_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `user_consent_for_applications` | `portal.user_consent_for_applications` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `user_information` | `powershell.user_information` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
| `users_without_mfa` | `powershell.users_without_mfa` | `powershell` | `app/powershell/entra/entra_master.ps1` | no | yes | `failed` | `collection_error` | `NotImplementedError` |
