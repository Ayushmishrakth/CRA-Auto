# Live Tenant Parameter Matrix

This matrix lists all 65 approved parameters evaluated against the active Microsoft 365 tenant.

| Parameter Name | Collector Name | Tenant Data Returned (YES/NO) | Raw Value Returned | Evidence Stored | Status |
|---|---|---|---|---|---|---|---|---|---|
| Account enabled | graph.account_enabled | YES | {"enabled_count": 14, "enabled_percent": 100.0, "total_users": 14} | YES | PASS |
| Admin Consent Workflow | graph.admin_consent_workflow | YES | {"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#policies/adminConsentRequestPolicy/$e... | YES | PASS |
| Authentication methods enabled | graph.authentication_methods_enabled | YES | {"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"metho... | YES | PASS |
| Auto-expiration policy for M365 Groups | graph.auto_expiration_policy_for_inactive_m365_groups | NO | {"active_policy_count": 0, "policy_count": 0} | NO | COLLECTION_ERROR |
| CAP policies for risky sign-ins | graph.cap_policies_for_risky_sign_ins | NO | {"policies": [], "risky_policy_count": 0} | NO | COLLECTION_ERROR |
| Conditional Access Policies (Exclusion) | graph.conditional_access_policies_exclusion | NO | {"exclusions": [], "policies_with_exclusions": 0} | NO | COLLECTION_ERROR |
| Custom Banned Password List | graph.custom_banned_password_list | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["Policy.Read.All"], "required_r... | NO | LICENSING_REQUIRED |
| Devices without compliance policies | graph.devices_without_compliance_policies | YES | {"error": {"code": "BadRequest", "innerError": {"client-request-id": "2e48ec4c-62bc-49e6-a108-26990c... | YES | PASS |
| Emergency Access Accounts | graph.emergency_access_accounts | YES | {"emergency_access_accounts": 0, "global_admin_members": 2} | YES | PASS |
| Entra - Tenant Creation By Non-Admin | graph.entra_tenant_creation_by_non_admin | YES | True | YES | PASS |
| Entra - Third Party App Integrations | graph.entra_third_party_app_integrations | YES | True | YES | PASS |
| Global Administrator Accounts | graph.global_administrator_accounts | YES | 2 | YES | PASS |
| Guest Invite Settings | graph.guest_invite_settings | YES | everyone | YES | PASS |
| Guest users count | graph.guest_users_count | YES | {"guest_count": 0, "guest_ratio_percent": 0.0, "total_users": 14} | YES | PASS |
| Restricted Access To Microsoft Entra Admin Centre | graph.restricted_access_to_microsoft_entra_admin_centre | YES | True | YES | PASS |
| Self-Service Password Reset Authentication Method | graph.self_service_password_reset_authentication_method | YES | {"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"metho... | YES | PASS |
| Tenant Collaboration Invitations | graph.tenant_collaboration_invitations | NO | {"default": {}, "partner_count": 0} | NO | COLLECTION_ERROR |
| User Consent For Applications | graph.user_consent_for_applications | YES | {"permissionGrantPoliciesAssigned": ["ManagePermissionGrantsForSelf.microsoft-user-default-recommend... | YES | PASS |
| User Information | graph.user_information | YES | {"complete_users": 12, "incomplete_users": 2, "total_users": 14} | YES | PASS |
| Users without MFA | graph.users_without_mfa | YES | {"total_users": 14, "users_without_mfa": 2} | YES | PASS |
| External Storage Providers In OWA | graph.external_storage_providers_in_owa | NO | {"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange... | NO | COLLECTION_ERROR |
| Full Calendar Schedules Able To Be Shared Externally | graph.full_calendar_schedules_able_to_be_shared_externally | NO | {"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange... | NO | COLLECTION_ERROR |
| Mailbox Storage usage | graph.mailbox_storage_usage | NO | {"mailbox_count": 0, "over_threshold": 0, "storage_usage_ratio": 0.0} | NO | COLLECTION_ERROR |
| Mailboxes Status (Active/Inactive) | graph.mailboxes_status_active_inactive | NO | {"active_mailboxes": 0, "active_ratio": 0.0, "inactive_mailboxes": 0} | NO | COLLECTION_ERROR |
| Number of emails read/received | graph.number_of_emails_read_received | NO | {"engaged_users": 0, "read_ratio": 0.0, "total_users": 0} | NO | COLLECTION_ERROR |
| Number of emails sent | graph.number_of_emails_sent | NO | {"average_sent_per_user": 0.0, "total_users": 0} | NO | COLLECTION_ERROR |
| Customer Lockbox | graph.customer_lockbox | NO | {"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange... | NO | COLLECTION_ERROR |
| Audit Logs enabled | graph.audit_logs_enabled | YES | {"audit_logs_queryable": true, "sample_count": 1} | YES | PASS |
| Audit log retention duration | graph.audit_log_retention_duration | YES | {"audit_log_sample_count": 166, "retention_policy_source": "Purview PowerShell required for exact du... | YES | PASS |
| Compliance Score overview | graph.compliance_score_overview | NO | {"collection_status": "MANUAL_VALIDATION_REQUIRED", "expected_evidence": "Compliance Manager score o... | NO | MANUAL_VALIDATION |
| DLP rules configured | graph.dlp_rules_configured | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SecurityActions.Read.All"], "r... | NO | LICENSING_REQUIRED |
| Information Protection Labels applied | graph.information_protection_labels_applied | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["InformationProtectionPolicy.Re... | NO | LICENSING_REQUIRED |
| Secure Score percentage | graph.secure_score_percentage | YES | {"current_score": 54.0, "max_score": 64.0, "secure_score_percentage": 84.38} | YES | PASS |
| Sensitivity Labels applied to Teams | graph.sensitivity_labels_applied_to_teams | YES | {"labeled_teams": 0, "total_teams": 1} | YES | PASS |
| Sensitivity Labels configured and applied | graph.sensitivity_labels_configured_and_applied | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["InformationProtectionPolicy.Re... | NO | LICENSING_REQUIRED |
| Active /Inactive teams | graph.active_inactive_teams | NO | {"active_team_count": 0, "inactive_team_count": 0} | NO | COLLECTION_ERROR |
| Activer/Inactive Teams users | graph.activer_inactive_teams_users | NO | {"active_users": 0, "inactive_ratio": 0.0, "inactive_users": 0} | NO | COLLECTION_ERROR |
| Copilot integration enabled | graph.copilot_integration_enabled | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Guest access enabled / disabled | graph.guest_access_enabled_disabled | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Meeting Policies configuration | graph.meeting_policies_configuration | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Meeting recording retention policies | graph.meeting_recording_retention_policies | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Meeting transcription enabled | graph.meeting_transcription_enabled | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Minimum number of owners | graph.minimum_number_of_owners | YES | {"teams_with_less_than_2_owners": 0, "total_teams": 1} | YES | PASS |
| Orphan Teams | graph.orphan_teams | YES | {"orphan_team_count": 0, "total_teams": 1} | YES | PASS |
| Teams - Channel Email Addresses | graph.teams_channel_email_addresses | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Teams - File Storage Option | graph.teams_file_storage_option | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Teams - Lobby Bypass | graph.teams_lobby_bypass | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Teams - Meeting Chat | graph.teams_meeting_chat | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Teams with external guest as owner | graph.teams_with_external_guest_as_owner | YES | {"teams_with_external_guest_owner": 0, "total_teams": 1} | YES | PASS |
| Teams with external users | graph.teams_with_external_users | YES | {"external_team_ratio": 0.0, "teams_with_external_users": 0, "total_teams": 1} | YES | PASS |
| Third-party apps allowed | graph.third_party_apps_allowed | NO | {"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resourc... | NO | COLLECTION_ERROR |
| Days to retain a deleted user’s OneDrive | graph.days_to_retain_a_deleted_user_s_onedrive | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.... | NO | LICENSING_REQUIRED |
| External sharing settings | graph.external_sharing_settings | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.... | NO | LICENSING_REQUIRED |
| Total active users on OneDrive | graph.total_active_users_on_onedrive | NO | {"active_ratio": 0.0, "active_users": 0, "total_users": 0} | NO | COLLECTION_ERROR |
| Expiration Policy for Anyone links | graph.expiration_policy_for_anyone_links | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.... | NO | LICENSING_REQUIRED |
| Inactive site policies | graph.inactive_site_policies | NO | {"inactive_site_count": 0, "inactive_site_percent": 0.0, "site_count": 0} | NO | COLLECTION_ERROR |
| Permission Settings for anyone links | graph.permission_setting_for_anyone_links | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.... | NO | LICENSING_REQUIRED |
| Site Ownership policies | graph.site_ownership_policies | NO | {"collection_status": "COLLECTION_ERROR", "reason": "Tenant does not have a SPO license.", "required... | NO | COLLECTION_ERROR |
| Active Sites count | graph.active_sites_count | NO | {"active_ratio": 0.0, "active_site_count": 0, "total_sites": 0} | NO | COLLECTION_ERROR |
| Active users on SharePoint | graph.active_users_on_sharepoint | NO | {"active_ratio": 0.0, "active_users": 0, "total_users": 0} | NO | COLLECTION_ERROR |
| Getting all sites with Sensitivity keywords on a Tenant | graph.getting_all_sites_with_sensitivity_keywords_on_a_tenant | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["Sites.Read.All"], "required_ro... | NO | LICENSING_REQUIRED |
| SharePoint & OneDrive Guest Access Expiry | graph.sharepoint_and_onedrive_guest_access_expiry | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.... | NO | LICENSING_REQUIRED |
| SharePoint - Modern Authentication | graph.sharepoint_modern_authentication | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.... | NO | LICENSING_REQUIRED |
| Sharing Settings (External/Internal) | graph.sharing_settings_external_internal | NO | {"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.... | NO | LICENSING_REQUIRED |
| Storage Quota consumption | graph.storage_quota_consumption | NO | {"max_storage_quota_ratio": 0.0, "site_count": 0, "sites_over_90_percent": 0} | NO | COLLECTION_ERROR |