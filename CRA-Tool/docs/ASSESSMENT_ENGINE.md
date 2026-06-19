# Assessment Engine

## Runtime Flow

The runtime assessment engine is centered in `CRA-Tool/app/services/runtime_assessment_service.py`.

1. A user starts an assessment through `POST /api/v1/assessments/start`.
2. The backend creates an assessment/job record and queues or runs the assessment job.
3. `run_assessment_job(job_id, worker_id=None)` loads the assessment job, tenant, and registry parameters.
4. The registry loads parameters from `CRA-Tool/app/config/assessment_registry/parameters.json`.
5. For each parameter, the runtime selects a collector path.
6. Graph-backed parameters use Graph collector services.
7. PowerShell-backed parameters use service scripts under `CRA-Tool/app/powershell/`.
8. The runtime persists raw evidence into `assessment_artifacts`.
9. Findings are evaluated and persisted into `assessment_findings`.
10. `apply_scores()` in `CRA-Tool/app/services/runtime_scoring_service.py` updates assessment scores and finding counts.
11. Recommendations are generated.
12. Assessment status and progress events are emitted.
13. The completed assessment can be viewed through the API and used for report generation.

## Assessment Registry Files

```text
CRA-Tool/app/config/assessment_registry/
|-- parameters.json        65 live assessment parameters.
|-- collectors.json        Collector mapping.
|-- rules.json             Scoring and evaluation rules.
|-- recommendations.json   Recommendation text.
`-- scoring.json           Scoring configuration.
```

## Service Counts

| Service | Parameter Count |
|---|---:|
| Entra ID | 21 |
| Exchange Online | 6 |
| Microsoft Purview | 8 |
| Microsoft Teams | 16 |
| OneDrive for Business | 3 |
| SharePoint Online | 11 |
| Total | 65 |

## Complete Parameter List

The list below is from `CRA-Tool/app/config/assessment_registry/parameters.json`.

### Entra ID

| # | Parameter Key | What It Checks | Pass Condition |
|---:|---|---|---|
| 1 | `account_enabled` | Number of accounts enabled | When number of enabled account is more than 85 % |
| 2 | `admin_consent_workflow` | Administrator Consent Workflows | When it is configured |
| 3 | `authentication_methods_enabled` | Authentication Methods Enabled | When authentication method has more than 2 authentication methods |
| 4 | `cap_policies_for_risky_sign_ins` | CAP Policies for Risky Sign-Ins | When CAP policy for Risky Sign -Ins are configured |
| 5 | `conditional_access_policies_exclusion` | Conditional Access Policies (Exclusion) | If no users are excluded from conditional access policies |
| 6 | `custom_banned_password_list` | Custom Banned Password List | If custom banned password is enabled then users cannot use banned password which is security best practise (example : welcome,Happy,Password etc |
| 7 | `devices_without_compliance_policies` | Device without Compliance Policies | When compliance policy is configured |
| 8 | `emergency_access_accounts` | Emergency Access Account | When it is Present |
| 9 | `entra_tenant_creation_by_non_admin` | Entra - Tenant Creation by Non-Admins | When non-admins are not allowed to create tenants |
| 10 | `entra_third_party_app_integrations` | Entra - Third-Party App Integrations | When it is disabled for users |
| 11 | `global_administrator_accounts` | Global Administrator Accounts | When tenant has more than 2 or less then 5 global admins |
| 12 | `guest_invite_settings` | Guest Invite Settings | When it is set to No one in the organization can invite guest users including admins (most restrictive), Only users assigned to specific admin roles can invite guest users |
| 13 | `guest_users_count` | Guest Users count | When the ratio of guest accounts to total accounts is less than 15% |
| 14 | `restricted_access_to_microsoft_entra_admin_centre` | Restricted Access to Microsoft Entra Admin Centre | Non-Admin Users should not have access to Microsoft Entra Admin Centre |
| 15 | `self_service_password_reset_authentication_method` | Self-Service Password Reset Authentication Method | Enabled to see how many methods registered |
| 16 | `tenant_collaboration_invitations` | Tenant Collaboration Invitation | When it is set to (Allow invitations only to the specified domain, Deny invitations to the specified domains) |
| 17 | `user_consent_for_applications` | User Consent for Applications | When it is not set to Users can consent |
| 18 | `user_information` | User Information | When the user information is complete for all users. |
| 19 | `users_without_mfa` | Users without MFA | When MFA is enabled for all the capable users |
| 20 | `auto_expiration_policy_for_inactive_m365_groups` | Auto-expiration policy for inactive m365 groups | Auto-expiration policy for inactive M365 groups is configured |
| 21 | `customer_lockbox` | Customer Lockbox | Microsoft support staff cannot access your content without your explicit approval. You get a Lockbox request, and only if you approve it can Microsoft proceed |

### Exchange Online

| # | Parameter Key | What It Checks | Pass Condition |
|---:|---|---|---|
| 1 | `external_storage_providers_in_owa` | External Storage providers in OWA | When not enabled, users cannot connect third-party storage services to Outlook Web App and: Attach files from those services Share links to external files via email Access cloud-based documents directly from their emai |
| 2 | `full_calendar_schedules_able_to_be_shared_externally` | Full Calendar Schedules able to be shared Externally | If False, calendar sharing is disabled across the organization, meaning users cannot share their calendars with anyone outside the organization. |
| 3 | `mailbox_storage_usage` | Mailbox Storage usage | When the active storage on mailbox is less than 75% |
| 4 | `mailboxes_status_active_inactive` | Mailbox status (Active/Inactive) | When the number active mailboxes are more than 85% |
| 5 | `number_of_emails_read_received` | Number of Emails read/received | More than 75% of users have read more than 70% of their emails. |
| 6 | `number_of_emails_sent` | Number of emails sent | When the number of emails sent by the users are more than 30 |

### Microsoft Purview

| # | Parameter Key | What It Checks | Pass Condition |
|---:|---|---|---|
| 1 | `audit_logs_enabled` | Audit Logs Enabled | If audit logs enabled this will hunt the results for query |
| 2 | `audit_log_retention_duration` | Audit Log Retention Duration | When policies are set up |
| 3 | `compliance_score_overview` | Compliance Score Overview | When it is more than or equal to 80% |
| 4 | `dlp_rules_configured` | DLP Rules configured | If DLP rules is configured and applied correctly to exchange,sharepoint,teams etc |
| 5 | `information_protection_labels_applied` | Information Protection Labels applied | If labels is configured and applied |
| 6 | `secure_score_percentage` | Secure Score Percentage | When it is more than 70% |
| 7 | `sensitivity_labels_applied_to_teams` | Sensitivity Labels applied to Teams | If labels is configured and applied |
| 8 | `sensitivity_labels_configured_and_applied` | Sensitivity Labels configured and applied | If labels is configured and applied |

### Microsoft Teams

| # | Parameter Key | What It Checks | Pass Condition |
|---:|---|---|---|
| 1 | `active_inactive_teams` | Active/Inactive teams | When a tenant does not have inactive teams |
| 2 | `activer_inactive_teams_users` | Active/Inactive Teams Users | When the number of inactive Teams users are less than 15% for the tenant |
| 3 | `copilot_integration_enabled` | Copilot Integration Enabled | When it is enabled |
| 4 | `guest_access_enabled_disabled` | Guest access Enabled/Disabled | When it is disabled |
| 5 | `meeting_policies_configuration` | Meeting Policies Configuration | When recommended settings are setup |
| 6 | `meeting_recording_retention_policies` | Meeting Recording Retention Policies | When it is enabled |
| 7 | `meeting_transcription_enabled` | Meeting Transcription enabled | When it is enabled |
| 8 | `minimum_number_of_owners` | Minimum number of Owners | When all teams have more than 1 Owner |
| 9 | `orphan_teams` | Orphan Teams | When there are no orphan teams |
| 10 | `teams_channel_email_addresses` | Teams - Channel Email Addresses | This will restrict Teams channels to allow accepting channel emails only from these Restricted Domains |
| 11 | `teams_file_storage_option` | Teams - File Storage Option | When the files are stored within the Microsoft suit |
| 12 | `teams_lobby_bypass` | Teams - Lobby Bypass | Specifies whether participants can bypass the lobby when joining the meeting - Never |
| 13 | `teams_meeting_chat` | Teams - Meeting Chat | Enabled: Participants are allowed to use chat during and after the meeting. |
| 14 | `teams_with_external_users` | Teams with External Users | When it is less than 20% |
| 15 | `third_party_apps_allowed` | Third Party Apps allowed | Disabled- custom apps are unavailable in the organization's app |
| 16 | `teams_with_external_guest_as_owner` | Teams with guest as owner | No Teams have external guests as owners |

### OneDrive for Business

| # | Parameter Key | What It Checks | Pass Condition |
|---:|---|---|---|
| 1 | `external_sharing_settings` | External Sharing Settings | When it is set to New and existing guests or more restrictive |
| 2 | `total_active_users_on_onedrive` | Total Active users on OneDrive | When the total active user on OneDrive are more than than 80% |
| 3 | `days_to_retain_a_deleted_user_s_onedrive` | Days to retain a deleted user's OneDrive | Deleted user's OneDrive retention period is configured |

### SharePoint Online

| # | Parameter Key | What It Checks | Pass Condition |
|---:|---|---|---|
| 1 | `active_sites_count` | Active Sites count | When the number active sites on SharePoint are more than 85% |
| 2 | `active_users_on_sharepoint` | Active Users on SharePoint | When the number active users on SharePoint are more than 85% |
| 3 | `getting_all_sites_with_sensitivity_keywords_on_a_tenant` | Sensitive SharePoint sites excluded from Copilot | This will give accurate result for sensitivity sites if anything exist |
| 4 | `sharepoint_and_onedrive_guest_access_expiry` | SharePoint and OneDrive Guest Access Expiry | SharingExpirationPeriod: The number of days the guest access link will be valid before it expires (if expiration is enabled). |
| 5 | `sharepoint_modern_authentication` | SharePoint - Modern Authentication | When it is enabled |
| 6 | `sharing_settings_external_internal` | Sharing Settings (External/Internal) | When settings enabled |
| 7 | `storage_quota_consumption` | Storage Quota Consumption | When it is less than 90% |
| 8 | `inactive_site_policies` | Inactive Site Policies | Inactive site policies are configured |
| 9 | `site_ownership_policies` | Site Ownership policies | Site ownership policies are configured and sites have accountable owners |
| 10 | `expiration_policy_for_anyone_links` | Expiration Policy for Anyone links | Anyone links expire within the approved duration |
| 11 | `permission_setting_for_anyone_links` | Permission Settings for anyone links | Anyone links are disabled or restricted to view-only least privilege access |

## Scoring

The active scoring write path is `apply_scores()` in `CRA-Tool/app/services/runtime_scoring_service.py`.

The report service also computes readiness from stored findings:

```text
pass_count = number of findings where status/finding is pass
fail_count = number of findings where status/finding is fail
readiness_score = pass_count / total_findings * 100
```

Readiness levels used by report data:

| Score | Readiness Level |
|---:|---|
| 80 or higher | Ready |
| 50 to 79.99 | Needs Improvement |
| Below 50 | Not Ready |

## Licensing Gap Behavior

Licensing information is treated as evidence. The report data builder includes `license_counts`, and the Key Observations section can show license assignment charts from real collected data. If a parameter requires a workload or license-backed signal that is not available, the runtime should preserve the evidence state and finding state instead of inventing a pass. Missing evidence should be visible as a runtime gap, failed collection, unsupported collector, or failed finding depending on the collector output and scoring rule.

## Pillars

Assessment scores are stored on the `assessments` table as:

- `overall_score`
- `identity_score`
- `security_score`
- `compliance_score`
- `collaboration_score`
- `licensing_score`

The report and dashboard may also group service findings into business-facing areas such as Security, Governance, and Best Practice, but the persisted score fields above are the model fields in the backend.
