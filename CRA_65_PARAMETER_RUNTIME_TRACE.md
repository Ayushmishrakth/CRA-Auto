# CRA 65 Parameter Runtime Trace

Scope: actual code paths in this repository only.

Runtime chain traced:

- Registry/manifest: `CRA-Tool/app/config/collector_manifest.json`
- Runtime selector/executor: `CRA-Tool/app/services/runtime_assessment_service.py`
- Graph collector map: `CRA-Tool/app/services/graph_cra_collector_service.py`
- PowerShell executor/parser: `CRA-Tool/app/services/powershell/powershell_runtime.py`
- CSV evidence parsing: `CRA-Tool/app/services/csv_ingestion/*`
- Persistence: `AssessmentArtifact` and `AssessmentFinding` writes inside `_persist_artifact()` and `_persist_finding()`

Important constraint: I did not run a tenant assessment here, so `Working`, `Returns Data`, `Missing Permissions`, and `Missing License` cannot be proven from tenant output. Where the runtime code only proves that a route exists, the table says exactly that.

## Runtime Rules Observed

- `_runtime_parameters()` returns the full registry parameter list.
- `_select_runtime()` forces 13 parameters to PowerShell when `supports_powershell` is true.
- For every other parameter, if the key exists in `GRAPH_COLLECTORS`, runtime chooses Graph before falling back to PowerShell.
- Graph collectors return a collector result directly: `pass`, `fail`, `warning`, or `collection_error`.
- PowerShell collectors execute the manifest script, parse a JSON contract, then evaluate the expected CSV if the contract says `not_collected`.
- Successful collector results are persisted as collected artifacts and assessment findings.
- Failed collectors are still persisted as failed artifacts and reconciled findings, usually `collection_error`, `manual_validation`, or `licensing_required` depending on the runtime error message.

## Matrix

| Parameter | Collector Exists | Working | Returns Data | Collection Error | Missing Permissions | Missing License | Missing PowerShell | Manual Validation |
|---|---|---|---|---|---|---|---|---|
| active_inactive_teams | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| active_sites_count | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| active_users_on_sharepoint | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| activer_inactive_teams_users | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| copilot_integration_enabled | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| external_storage_providers_in_owa | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| external_sharing_settings | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| full_calendar_schedules_able_to_be_shared_externally | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| getting_all_sites_with_sensitivity_keywords_on_a_tenant | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| guest_access_enabled_disabled | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| mailbox_storage_usage | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| mailboxes_status_active_inactive | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| meeting_policies_configuration | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| meeting_recording_retention_policies | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| meeting_transcription_enabled | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| minimum_number_of_owners | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| number_of_emails_read_received | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| number_of_emails_sent | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| orphan_teams | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| sharepoint_and_onedrive_guest_access_expiry | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| sharepoint_modern_authentication | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| sharing_settings_external_internal | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| storage_quota_consumption | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| teams_channel_email_addresses | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| teams_file_storage_option | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| teams_lobby_bypass | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| teams_meeting_chat | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| teams_with_external_users | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| third_party_apps_allowed | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| total_active_users_on_onedrive | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| audit_log_retention_duration | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| audit_logs_enabled | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| compliance_score_overview | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| dlp_rules_configured | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| information_protection_labels_applied | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| secure_score_percentage | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| sensitivity_labels_applied_to_teams | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| sensitivity_labels_configured_and_applied | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| days_to_retain_a_deleted_user_s_onedrive | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| inactive_site_policies | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| site_ownership_policies | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| account_enabled | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| admin_consent_workflow | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| authentication_methods_enabled | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| cap_policies_for_risky_sign_ins | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| conditional_access_policies_exclusion | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| custom_banned_password_list | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| devices_without_compliance_policies | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| emergency_access_accounts | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| entra_tenant_creation_by_non_admin | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| entra_third_party_app_integrations | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| global_administrator_accounts | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| guest_invite_settings | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| guest_users_count | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| restricted_access_to_microsoft_entra_admin_centre | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| self_service_password_reset_authentication_method | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| tenant_collaboration_invitations | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| user_consent_for_applications | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| user_information | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| users_without_mfa | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| auto_expiration_policy_for_inactive_m365_groups | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| expiration_policy_for_anyone_links | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| permission_setting_for_anyone_links | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| teams_with_external_guest_as_owner | Yes - Graph route | Code path exists; tenant success not proven | Graph collector_result if Graph call succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |
| customer_lockbox | Yes - PowerShell route | Code path exists; tenant success not proven | CSV evidence if script succeeds | Not proven by static code | Not proven by static code | Not proven by static code | No | No static requirement |

## Parameters Most Likely To Convert With Minimal Engineering

Because every one of the 65 parameters has a registered collector route and an evidence persistence path, the static code does not show a missing collector or missing script blocker.

The lowest-engineering conversions from `collection_error` to `pass/fail` are the 13 forced PowerShell parameters, because the runtime already routes them to scripts and CSV evidence:

- `copilot_integration_enabled`
- `customer_lockbox`
- `external_storage_providers_in_owa`
- `full_calendar_schedules_able_to_be_shared_externally`
- `guest_access_enabled_disabled`
- `meeting_policies_configuration`
- `meeting_recording_retention_policies`
- `meeting_transcription_enabled`
- `teams_channel_email_addresses`
- `teams_file_storage_option`
- `teams_lobby_bypass`
- `teams_meeting_chat`
- `third_party_apps_allowed`

For these, minimal effort should be environment/runtime validation, not collector design:

- PowerShell module availability
- Non-interactive auth behavior
- Correct tenant/admin context
- Required Exchange/Teams/Purview/SharePoint roles
- Expected CSV actually generated by the script

The remaining 52 parameters already route through `GRAPH_COLLECTORS`. Their conversion from `collection_error` to `pass/fail` depends on runtime Graph success:

- Valid app registration credentials
- Granted application permissions
- Tenant workload availability
- Graph endpoint support for the target tenant
- Any premium/license-gated API behavior returned at runtime

## Bottom Line

From code trace only, there is no evidence that any of the 65 lacks registration, routing, execution handling, or finding persistence.

What cannot be proven without a real assessment run:

- Whether each collector works against your tenant
- Whether each collector returns actual tenant data
- Whether failures are permission, license, module, auth, timeout, or endpoint limitations

To identify exact `collection_error -> pass/fail` candidates, the next required input is runtime artifact/finding error data from a failed assessment, not more static code review.
