# Collector Execution Audit

Latest failed assessment audited: `f499ec4c-6b6b-4b05-8991-5f47b3ce0db6`

| collector_name | parameter_key | started | completed | failed | execution_time |
|---|---|---:|---:|---:|---:|
| `powershell.account_enabled` | `account_enabled` | yes | yes | no | 0.93s |
| `powershell.active_inactive_teams` | `active_inactive_teams` | yes | yes | no | 2.84s |
| `powershell.active_sites_count` | `active_sites_count` | yes | no | yes | 0.35s |
| `powershell.active_users_on_sharepoint` | `active_users_on_sharepoint` | yes | yes | no | 1.55s |
| `powershell.activer_inactive_teams_users` | `activer_inactive_teams_users` | yes | no | yes | 0.41s |
| `powershell.admin_consent_workflow` | `admin_consent_workflow` | yes | yes | no | 4.26s |
| `powershell.assigned_license` | `assigned_license` | yes | yes | no | 1.83s |
| `powershell.authentication_methods_enabled` | `authentication_methods_enabled` | yes | yes | no | 1.08s |
| `powershell.cap_policies_for_risky_sign_ins` | `cap_policies_for_risky_sign_ins` | yes | yes | no | 2.46s |
| `powershell.conditional_access_policies_exclusion` | `conditional_access_policies_exclusion` | yes | yes | no | 1.45s |
| `powershell.copilot_integration_enabled` | `copilot_integration_enabled` | yes | yes | no | 0.69s |
| `powershell.devices_without_compliance_policies` | `devices_without_compliance_policies` | yes | no | yes | 0.44s |
| `powershell.entra_tenant_creation_by_non_admin` | `entra_tenant_creation_by_non_admin` | yes | no | yes | 0.38s |
| `powershell.entra_third_party_app_integrations` | `entra_third_party_app_integrations` | yes | no | yes | 0.39s |
| `powershell.global_administrator_accounts` | `global_administrator_accounts` | yes | no | yes | 0.37s |
| `powershell.guest_access_enabled_disabled` | `guest_access_enabled_disabled` | yes | no | yes | 0.49s |
| `powershell.guest_invite_settings` | `guest_invite_settings` | yes | yes | no | 0.95s |
| `powershell.guest_users_count` | `guest_users_count` | yes | yes | no | 1.01s |
| `powershell.mailbox_storage_usage` | `mailbox_storage_usage` | yes | no | yes | 0.44s |
| `powershell.mailboxes_status_active_inactive` | `mailboxes_status_active_inactive` | yes | yes | no | 1.45s |
| `powershell.meeting_policies_configuration` | `meeting_policies_configuration` | yes | no | yes | 0.37s |
| `powershell.meeting_recording_retention_policies` | `meeting_recording_retention_policies` | yes | no | yes | 0.45s |
| `powershell.meeting_transcription_enabled` | `meeting_transcription_enabled` | yes | no | yes | 0.39s |
| `powershell.minimum_number_of_owners` | `minimum_number_of_owners` | yes | no | yes | 0.39s |
| `powershell.non_admin_users_can_register_applications` | `non_admin_users_can_register_applications` | yes | yes | no | 0.81s |
| `powershell.number_of_emails_read_received` | `number_of_emails_read_received` | yes | yes | no | 1.53s |
| `powershell.number_of_emails_sent` | `number_of_emails_sent` | yes | no | yes | 0.46s |
| `powershell.orphan_teams` | `orphan_teams` | yes | yes | no | 1.40s |
| `portal.restricted_access_to_microsoft_entra_admin_centre` | `restricted_access_to_microsoft_entra_admin_centre` | yes | yes | no | 0.80s |
| `portal.self_service_password_reset_authentication_method` | `self_service_password_reset_authentication_method` | yes | no | yes | 0.53s |
| `powershell.teams_anonymous_users` | `teams_anonymous_users` | yes | yes | no | 0.60s |
| `powershell.teams_channel_email_addresses` | `teams_channel_email_addresses` | yes | no | yes | 0.33s |
| `powershell.teams_external_unmanaged_user_communication` | `teams_external_unmanaged_user_communication` | yes | yes | no | 0.78s |
| `powershell.teams_file_storage_option` | `teams_file_storage_option` | yes | yes | no | 0.64s |
| `powershell.teams_lobby_bypass` | `teams_lobby_bypass` | yes | no | yes | 0.43s |
| `powershell.teams_meeting_chat` | `teams_meeting_chat` | yes | no | yes | 0.39s |
| `powershell.teams_with_external_users` | `teams_with_external_users` | yes | yes | no | 1.73s |
| `powershell.tenant_collaboration_invitations` | `tenant_collaboration_invitations` | yes | no | yes | 0.37s |
| `powershell.third_party_apps_allowed` | `third_party_apps_allowed` | yes | no | yes | 0.50s |
| `powershell.total_active_users_on_onedrive` | `total_active_users_on_onedrive` | yes | yes | no | 2.91s |
| `powershell.unused_licenses_count` | `unused_licenses_count` | yes | yes | no | 0.73s |
| `portal.user_consent_for_applications` | `user_consent_for_applications` | yes | no | yes | 0.38s |
| `powershell.user_information` | `user_information` | yes | yes | no | 0.91s |
| `powershell.users_without_mfa` | `users_without_mfa` | yes | no | yes | 0.32s |

## Findings

- No stuck collector was found in the failed assessment event stream.
- Collectors that failed emitted `collector.failed` events.
- The assessment stalled from the UI perspective because runtime marked the job `incomplete` and skipped scoring/recommendations/report generation.
- No timeout event was recorded.
