# Assessment Parameter Reconciliation

Generated: 2026-06-03 20:10:47

## Fresh Assessment Execution

A new live tenant assessment was not started from this audit script because the current workspace does not provide confirmed tenant runtime credentials/session context. I reconciled against the latest completed local assessment in `CRA-Tool/cra.db` instead.

## Latest Local Assessment

| Field | Value |
| --- | --- |
| Assessment ID | 375fd0d955a44b5d8d64dfcb1cd2247a |
| Tenant ID | fe4eff9a-f69c-48c0-921d-8006a6d5beb2 |
| Status | completed |
| Created At | 2026-06-03 14:11:14.632824 |
| Updated At | 2026-06-03 14:12:32.427651 |

## Reconciliation Counts

| Inventory | Count | Expected | Status |
| --- | --- | --- | --- |
| Official parameters | 65 | 65 | OK |
| Active registry parameters | 65 | 65 | OK |
| Database assessment_parameters | 64 | 65 | Mismatch |
| Latest assessment artifact rows | 64 | 65 | Mismatch |
| Latest assessment distinct artifact parameters | 64 | 65 | Mismatch |
| Latest assessment findings | 59 | 65 | Mismatch |
| Latest assessment distinct finding parameters | 59 | 65 | Mismatch |
| Latest assessment recommendations | 59 | 65 | Mismatch |
| Latest assessment distinct recommendation parameters | 59 | 65 | Mismatch |

## Latest Artifact Status Distribution

| Status | Count |
| --- | --- |
| collected | 59 |
| failed | 5 |

## Official Parameters Missing From Latest Assessment Artifacts

| Parameter Key |
| --- |
| auto_expiration_policy_for_inactive_m365_groups |
| days_to_retain_a_deleted_user_s_onedrive |
| expiration_policy_for_anyone_links |
| inactive_site_policies |
| permission_setting_for_anyone_links |
| site_ownership_policies |
| teams_with_external_guest_as_owner |

## Result

The active file registry is synchronized to the official 65-parameter template, but the local database seed/runtime assessment history is still at 64/59 coverage. A re-seed/migration and a new authenticated tenant assessment are required before the success criteria can pass end-to-end.
