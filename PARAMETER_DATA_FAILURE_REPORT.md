# Parameter Data Failure Report

This report analyzes the failure root causes for all parameters that did not successfully return tenant configuration data.

| Parameter Name | Collector Name | Failure Reason | Root Cause Investigation |
|---|---|---|---|
| Auto-expiration policy for M365 Groups | graph.auto_expiration_policy_for_inactive_m365_groups | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| CAP policies for risky sign-ins | graph.cap_policies_for_risky_sign_ins | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Conditional Access Policies (Exclusion) | graph.conditional_access_policies_exclusion | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Custom Banned Password List | graph.custom_banned_password_list | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Tenant Collaboration Invitations | graph.tenant_collaboration_invitations | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| External Storage Providers In OWA | graph.external_storage_providers_in_owa | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Full Calendar Schedules Able To Be Shared Externally | graph.full_calendar_schedules_able_to_be_shared_externally | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Mailbox Storage usage | graph.mailbox_storage_usage | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Mailboxes Status (Active/Inactive) | graph.mailboxes_status_active_inactive | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Number of emails read/received | graph.number_of_emails_read_received | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Number of emails sent | graph.number_of_emails_sent | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Customer Lockbox | graph.customer_lockbox | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Compliance Score overview | graph.compliance_score_overview | Tenant Has No Configuration | Specific configuration/policy is missing or requires manual validation via admin portal. |
| DLP rules configured | graph.dlp_rules_configured | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Information Protection Labels applied | graph.information_protection_labels_applied | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Sensitivity Labels configured and applied | graph.sensitivity_labels_configured_and_applied | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Active /Inactive teams | graph.active_inactive_teams | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Activer/Inactive Teams users | graph.activer_inactive_teams_users | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Copilot integration enabled | graph.copilot_integration_enabled | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Guest access enabled / disabled | graph.guest_access_enabled_disabled | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Meeting Policies configuration | graph.meeting_policies_configuration | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Meeting recording retention policies | graph.meeting_recording_retention_policies | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Meeting transcription enabled | graph.meeting_transcription_enabled | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Teams - Channel Email Addresses | graph.teams_channel_email_addresses | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Teams - File Storage Option | graph.teams_file_storage_option | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Teams - Lobby Bypass | graph.teams_lobby_bypass | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Teams - Meeting Chat | graph.teams_meeting_chat | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Third-party apps allowed | graph.third_party_apps_allowed | Authentication Failure | Microsoft service principal is disabled or tenant access subscription lapsed. |
| Days to retain a deleted user’s OneDrive | graph.days_to_retain_a_deleted_user_s_onedrive | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| External sharing settings | graph.external_sharing_settings | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Total active users on OneDrive | graph.total_active_users_on_onedrive | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Expiration Policy for Anyone links | graph.expiration_policy_for_anyone_links | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Inactive site policies | graph.inactive_site_policies | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Permission Settings for anyone links | graph.permission_setting_for_anyone_links | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Site Ownership policies | graph.site_ownership_policies | PowerShell Failure | PowerShell execution environment not supported via app-only Microsoft Graph token. |
| Active Sites count | graph.active_sites_count | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Active users on SharePoint | graph.active_users_on_sharepoint | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |
| Getting all sites with Sensitivity keywords on a Tenant | graph.getting_all_sites_with_sensitivity_keywords_on_a_tenant | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| SharePoint & OneDrive Guest Access Expiry | graph.sharepoint_and_onedrive_guest_access_expiry | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| SharePoint - Modern Authentication | graph.sharepoint_modern_authentication | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Sharing Settings (External/Internal) | graph.sharing_settings_external_internal | Permission Failure | Target API endpoint requires Premium licensing tier not present on the tenant. |
| Storage Quota consumption | graph.storage_quota_consumption | Parser Failure | The parser could not extract configuration elements because JSON structures were empty or schema mismatch. |