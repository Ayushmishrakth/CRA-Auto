# CRA Collector Status

## Summary

Source registries:

- Parameters: `CRA-Tool/app/config/assessment_registry/parameters.json`
- Collectors: `CRA-Tool/app/config/assessment_registry/collectors.json`
- Runtime selector: `CRA-Tool/app/services/runtime_assessment_service.py`
- Graph collectors: `CRA-Tool/app/services/graph_cra_collector_service.py`
- PowerShell runtime: `CRA-Tool/app/services/powershell/powershell_runtime.py`

Registry contains 76 CRA parameters.

Current runtime behavior:

- Only 7 parameters are selected by `FIRST_OPERATIONAL_GRAPH_PARAMETERS`.
- Those 7 parameters are collected through first-class Python Graph collector functions.
- The other 69 parameters are not executed in the current runtime because `_runtime_parameters` narrows the registry before execution.
- PowerShell collector infrastructure exists, but current runtime selection prevents most PowerShell/portal/manual registry parameters from running.

## Operational Graph Collectors

| Parameter | Collector Function | Graph Endpoints |
|---|---|---|
| `global_administrator_accounts` | `collect_global_administrator_accounts` | `/directoryRoles`, `/directoryRoles/{id}/members` |
| `guest_users_count` | `collect_guest_users_count` | `/users` |
| `account_enabled` | `collect_account_enabled` | `/users` |
| `user_information` | `collect_user_information` | `/users` |
| `guest_invite_settings` | `collect_guest_invite_settings` | `/policies/authorizationPolicy/authorizationPolicy` |
| `entra_tenant_creation_by_non_admin` | `collect_entra_tenant_creation_by_non_admin` | `/policies/authorizationPolicy/authorizationPolicy` |
| `entra_third_party_app_integrations` | `collect_entra_third_party_app_integrations` | `/policies/authorizationPolicy/authorizationPolicy` |

## Collector Audit Table

| Parameter | Collector | Implemented? | Working? | Graph Endpoint | Produces Artifact? | Produces Finding? | Produces Score? |
|---|---|---|---|---|---|---|---|
| restricted_access_to_microsoft_entra_admin_center | portal.restricted_access_to_microsoft_entra_admin_center | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| active_inactive_teams | powershell.active_inactive_teams | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| active_sites_count | powershell.active_sites_count | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| active_users_on_sharepoint | powershell.active_users_on_sharepoint | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| activer_inactive_teams_users | powershell.activer_inactive_teams_users | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| checking_sharing_permissions_for_each_sites_on_a_tenant | powershell.checking_sharing_permissions_for_each_sites_on_a_tenant | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| copilot_integration_enabled | powershell.copilot_integration_enabled | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| external_storage_providers_in_owa | powershell.external_storage_providers_in_owa | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| external_sharing_settings | powershell.external_sharing_settings | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| full_calendar_schedules_able_to_be_shared_externally | powershell.full_calendar_schedules_able_to_be_shared_externally | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| getting_all_sites_with_sensitivity_keywords_on_a_tenant | powershell.getting_all_sites_with_sensitivity_keywords_on_a_tenant | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| guest_access_enabled_disabled | powershell.guest_access_enabled_disabled | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| mailbox_storage_usage | powershell.mailbox_storage_usage | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| mailboxes_status_active_inactive | powershell.mailboxes_status_active_inactive | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| meeting_policies_configuration | powershell.meeting_policies_configuration | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| meeting_recording_retention_policies | powershell.meeting_recording_retention_policies | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| meeting_transcription_enabled | powershell.meeting_transcription_enabled | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| minimum_number_of_owners | powershell.minimum_number_of_owners | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| number_of_emails_read_received | powershell.number_of_emails_read_received | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| number_of_emails_sent | powershell.number_of_emails_sent | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| orphan_teams | powershell.orphan_teams | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| sharepoint_and_onedrive_guest_access_expiry | powershell.sharepoint_and_onedrive_guest_access_expiry | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| sharepoint_modern_authentication | powershell.sharepoint_modern_authentication | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| sharing_settings_external_internal | powershell.sharing_settings_external_internal | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| storage_quota_consumption | powershell.storage_quota_consumption | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| teams_anonymous_users | powershell.teams_anonymous_users | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| teams_channel_email_addresses | powershell.teams_channel_email_addresses | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| teams_external_unmanaged_user_communication | powershell.teams_external_unmanaged_user_communication | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| teams_file_storage_option | powershell.teams_file_storage_option | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| teams_lobby_bypass | powershell.teams_lobby_bypass | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| teams_meeting_chat | powershell.teams_meeting_chat | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| teams_with_external_users | powershell.teams_with_external_users | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| third_party_apps_allowed | powershell.third_party_apps_allowed | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| total_active_users_on_onedrive | powershell.total_active_users_on_onedrive | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| audit_logs_enabled | powershell.audit_logs_enabled | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| audit_log_retention_duration | portal.audit_log_retention_duration | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| compliance_score_overview | portal.compliance_score_overview | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| dlp_rules_configured | powershell.dlp_rules_configured | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| information_protection_labels_applied | powershell.information_protection_labels_applied | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| secure_score_percentage | portal.secure_score_percentage | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| sensitivity_labels_applied_to_teams | powershell.sensitivity_labels_applied_to_teams | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| sensitivity_labels_configured_and_applied | powershell.sensitivity_labels_configured_and_applied | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| sensitivity_labels_are_applied | powershell.sensitivity_labels_are_applied | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| days_to_retain_a_deleted_user_s_onedrive | powershell.days_to_retain_a_deleted_user_s_onedrive | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| inactive_site_policies | portal.inactive_site_policies | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| site_ownership_policies | portal.site_ownership_policies | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| account_enabled | powershell.account_enabled | Yes - Graph runtime | Likely working if Graph call succeeds | /users | Yes | Yes | Yes, if all selected collectors complete |
| admin_consent_workflow | powershell.admin_consent_workflow | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| assigned_license | powershell.assigned_license | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| authentication_methods_enabled | powershell.authentication_methods_enabled | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| cap_policies_for_risky_sign_ins | powershell.cap_policies_for_risky_sign_ins | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| conditional_access_policies_exclusion | powershell.conditional_access_policies_exclusion | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| custom_banned_password_list | portal.custom_banned_password_list | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| devices_without_compliance_policies | powershell.devices_without_compliance_policies | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| emergency_access_accounts | manual.emergency_access_accounts | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| entra_tenant_creation_by_non_admin | powershell.entra_tenant_creation_by_non_admin | Yes - Graph runtime | Likely working if Graph call succeeds | /policies/authorizationPolicy/authorizationPolicy | Yes | Yes | Yes, if all selected collectors complete |
| entra_third_party_app_integrations | powershell.entra_third_party_app_integrations | Yes - Graph runtime | Likely working if Graph call succeeds | /policies/authorizationPolicy/authorizationPolicy | Yes | Yes | Yes, if all selected collectors complete |
| global_administrator_accounts | powershell.global_administrator_accounts | Yes - Graph runtime | Likely working if Graph call succeeds | /directoryRoles + /directoryRoles/{id}/members | Yes | Yes | Yes, if all selected collectors complete |
| guest_invite_settings | powershell.guest_invite_settings | Yes - Graph runtime | Likely working if Graph call succeeds | /policies/authorizationPolicy/authorizationPolicy | Yes | Yes | Yes, if all selected collectors complete |
| guest_users_count | powershell.guest_users_count | Yes - Graph runtime | Likely working if Graph call succeeds | /users | Yes | Yes | Yes, if all selected collectors complete |
| non_admin_users_can_register_applications | powershell.non_admin_users_can_register_applications | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| restricted_access_to_microsoft_entra_admin_centre | portal.restricted_access_to_microsoft_entra_admin_centre | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| self_service_password_reset_authentication_method | portal.self_service_password_reset_authentication_method | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| tenant_collaboration_invitations | powershell.tenant_collaboration_invitations | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| unused_licenses_count | powershell.unused_licenses_count | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| user_consent_for_applications | portal.user_consent_for_applications | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| user_information | powershell.user_information | Yes - Graph runtime | Likely working if Graph call succeeds | /users | Yes | Yes | Yes, if all selected collectors complete |
| users_without_mfa | powershell.users_without_mfa | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| auto_expiration_policy_for_inactive_m365_groups | portal.auto_expiration_policy_for_inactive_m365_groups | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| device_without_compliance_policy | portal.device_without_compliance_policy | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| expiration_policy_for_anyone_links | powershell.expiration_policy_for_anyone_links | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| permission_setting_for_anyone_links | powershell.permission_setting_for_anyone_links | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| sensitive_sharepoint_site_excluded_from_copilot_search | portal.sensitive_sharepoint_site_excluded_from_copilot_search | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |
| teams_with_external_guest_as_owner | powershell.teams_with_external_guest_as_owner | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| customer_lockbox | powershell.customer_lockbox | Partial - registry only / runtime gated off | Not in current runtime | - | No in current runtime | No in current runtime | No |
| note_for_purview_if_e5_licenses_are_not_available_all_parameters_will_fail | unknown.note_for_purview_if_e5_licenses_are_not_available_all_parameters_will_fail | No - manual/portal/unknown | Not in current runtime | - | No in current runtime | No in current runtime | No |

## Collector Findings

- Implemented and runtime-selected: 7 / 76.
- Registry-only PowerShell entries: most M365/Teams/SharePoint/Exchange/Purview controls.
- Portal/manual/unknown entries have no current automated runtime.
- Because scoring only runs after the selected collector set completes, a single selected Graph collector failure can prevent score/recommendation/report generation.
