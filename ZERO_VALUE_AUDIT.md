# Zero Value Audit

Assessment: `cac733c4af644a3f9ceaafc49d1f020d`
Generated: `2026-06-04T00:48:49`

Parameters with zero/null/empty/default signals: `23`.

| Parameter | Key | Service | Collector | Status | Zero/Empty Signals | Actual Value |
| --- | --- | --- | --- | --- | --- | --- |
| Admin Consent Workflow | admin_consent_workflow | Entra ID | graph.admin_consent_workflow | fail | requestDurationInDays=0; version=0; reviewers=empty array | {"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#policies/adminConsentRequestPolicy/$entity", "isEnabled": false, "notifyReviewers": false, "remindersEnabled": false, "requestDurationInDays": 0, "reviewers": [], "version": 0} |
| Auto-expiration policy for M365 Groups | auto_expiration_policy_for_inactive_m365_groups | Entra ID | graph.auto_expiration_policy_for_inactive_m365_groups | fail | policy_count=0; active_policy_count=0 | {"active_policy_count": 0, "policy_count": 0} |
| CAP policies for risky sign-ins | cap_policies_for_risky_sign_ins | Entra ID | graph.cap_policies_for_risky_sign_ins | fail | risky_policy_count=0; policies=empty array | {"policies": [], "risky_policy_count": 0} |
| Conditional Access Policies (Exclusion) | conditional_access_policies_exclusion | Entra ID | graph.conditional_access_policies_exclusion | pass | policies_with_exclusions=0; exclusions=empty array | {"exclusions": [], "policies_with_exclusions": 0} |
| Emergency Access Accounts | emergency_access_accounts | Entra ID | graph.emergency_access_accounts | fail | emergency_access_accounts=0 | {"emergency_access_accounts": 0, "global_admin_members": 2} |
| Guest users count | guest_users_count | Entra ID | graph.guest_users_count | pass | guest_count=0; guest_ratio_percent=0 | {"guest_count": 0, "guest_ratio_percent": 0.0, "total_users": 14} |
| Tenant Collaboration Invitations | tenant_collaboration_invitations | Entra ID | graph.tenant_collaboration_invitations | fail | partner_count=0; default=empty object | {"default": {}, "partner_count": 0} |
| Mailbox Storage usage | mailbox_storage_usage | Exchange Online | graph.mailbox_storage_usage | pass | mailbox_count=0; over_threshold=0; storage_usage_ratio=0 | {"mailbox_count": 0, "over_threshold": 0, "storage_usage_ratio": 0.0} |
| Mailboxes Status (Active/Inactive) | mailboxes_status_active_inactive | Exchange Online | graph.mailboxes_status_active_inactive | fail | active_mailboxes=0; inactive_mailboxes=0; active_ratio=0 | {"active_mailboxes": 0, "active_ratio": 0.0, "inactive_mailboxes": 0} |
| Number of emails read/received | number_of_emails_read_received | Exchange Online | graph.number_of_emails_read_received | fail | read_ratio=0; engaged_users=0; total_users=0 | {"engaged_users": 0, "read_ratio": 0.0, "total_users": 0} |
| Number of emails sent | number_of_emails_sent | Exchange Online | graph.number_of_emails_sent | fail | average_sent_per_user=0; total_users=0 | {"average_sent_per_user": 0.0, "total_users": 0} |
| Sensitivity Labels applied to Teams | sensitivity_labels_applied_to_teams | Microsoft Purview | graph.sensitivity_labels_applied_to_teams | fail | labeled_teams=0 | {"labeled_teams": 0, "total_teams": 1} |
| Active /Inactive teams | active_inactive_teams | Microsoft Teams | graph.active_inactive_teams | pass | active_team_count=0; inactive_team_count=0 | {"active_team_count": 0, "inactive_team_count": 0} |
| Activer/Inactive Teams users | activer_inactive_teams_users | Microsoft Teams | graph.activer_inactive_teams_users | pass | active_users=0; inactive_users=0; inactive_ratio=0 | {"active_users": 0, "inactive_ratio": 0.0, "inactive_users": 0} |
| Minimum number of owners | minimum_number_of_owners | Microsoft Teams | graph.minimum_number_of_owners | pass | teams_with_less_than_2_owners=0 | {"teams_with_less_than_2_owners": 0, "total_teams": 1} |
| Orphan Teams | orphan_teams | Microsoft Teams | graph.orphan_teams | pass | orphan_team_count=0 | {"orphan_team_count": 0, "total_teams": 1} |
| Teams with external guest as owner | teams_with_external_guest_as_owner | Microsoft Teams | graph.teams_with_external_guest_as_owner | pass | teams_with_external_guest_owner=0 | {"teams_with_external_guest_owner": 0, "total_teams": 1} |
| Teams with external users | teams_with_external_users | Microsoft Teams | graph.teams_with_external_users | pass | teams_with_external_users=0; external_team_ratio=0 | {"external_team_ratio": 0.0, "teams_with_external_users": 0, "total_teams": 1} |
| Total active users on OneDrive | total_active_users_on_onedrive | OneDrive for Business | graph.total_active_users_on_onedrive | fail | active_users=0; total_users=0; active_ratio=0 | {"active_ratio": 0.0, "active_users": 0, "total_users": 0} |
| Inactive site policies | inactive_site_policies | SharePoint | graph.inactive_site_policies | pass | site_count=0; inactive_site_count=0; inactive_site_percent=0 | {"inactive_site_count": 0, "inactive_site_percent": 0.0, "site_count": 0} |
| Active Sites count | active_sites_count | SharePoint Online | graph.active_sites_count | fail | active_site_count=0; total_sites=0; active_ratio=0 | {"active_ratio": 0.0, "active_site_count": 0, "total_sites": 0} |
| Active users on SharePoint | active_users_on_sharepoint | SharePoint Online | graph.active_users_on_sharepoint | fail | active_users=0; total_users=0; active_ratio=0 | {"active_ratio": 0.0, "active_users": 0, "total_users": 0} |
| Storage Quota consumption | storage_quota_consumption | SharePoint Online | graph.storage_quota_consumption | pass | sites_over_90_percent=0; site_count=0; max_storage_quota_ratio=0 | {"max_storage_quota_ratio": 0.0, "site_count": 0, "sites_over_90_percent": 0} |