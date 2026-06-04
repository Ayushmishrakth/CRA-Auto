# Failed Collector Retest Report

Generated: 2026-06-03 21:01:19

Retest assessment: `81fb98a5041341468d2273182cb75c3d`

## Success Criteria

| Metric | Actual | Expected | Status |
| --- | --- | --- | --- |
| Artifacts | 65 | 65 | OK |
| Findings | 65 | 65 | OK |
| Recommendations | 65 | 65 | OK |
| FAILED_COLLECTOR findings | 0 | 0 | OK |

## Retest Status Breakdown

| Status | Count |
| --- | --- |
| fail | 29 |
| licensing_required | 8 |
| manual_validation | 9 |
| pass | 15 |
| warning | 4 |

## Former Failed Collectors

| Parameter | Retest Finding Status | Retest Artifact Status | Result |
| --- | --- | --- | --- |
| audit_log_retention_duration | manual_validation | failed | OK |
| auto_expiration_policy_for_inactive_m365_groups | manual_validation | failed | OK |
| customer_lockbox | manual_validation | failed | OK |
| days_to_retain_a_deleted_user_s_onedrive | manual_validation | failed | OK |
| expiration_policy_for_anyone_links | warning | collected | OK |
| external_storage_providers_in_owa | manual_validation | failed | OK |
| full_calendar_schedules_able_to_be_shared_externally | manual_validation | failed | OK |
| inactive_site_policies | warning | collected | OK |
| permission_setting_for_anyone_links | warning | collected | OK |
| sharepoint_and_onedrive_guest_access_expiry | manual_validation | failed | OK |
| site_ownership_policies | warning | collected | OK |
| teams_with_external_guest_as_owner | manual_validation | failed | OK |

Result: **FAILED_COLLECTOR = 0**. Remaining dependency outcomes are explicit business statuses, primarily MANUAL_VALIDATION or LICENSING_REQUIRED.
