# Backend Parameter Audit

Generated: 2026-06-03 20:10:47

Authority: `OFFICIAL_CRA_PARAMETER_MASTER_LIST.md` extracted from `CRA-Tool/out/index.html`.

## Count Summary

| Inventory | Count | Status |
| --- | --- | --- |
| Official CRA template | 65 | Authority |
| Active registry parameters.json | 65 | OK |
| Active collectors.json | 65 | OK |
| Active rules.json | 65 | OK |
| Active recommendations.json | 65 | OK |
| Collector manifest | 75 | Contains legacy/orphan entries |
| Database assessment_parameters | 64 | Mismatch |
| Database assessment_rules joined to parameters | 64 | Mismatch |

## Missing Parameters

### Missing From Active Registry

None.

### Missing From Database assessment_parameters

| Parameter Key |
| --- |
| auto_expiration_policy_for_inactive_m365_groups |
| days_to_retain_a_deleted_user_s_onedrive |
| expiration_policy_for_anyone_links |
| inactive_site_policies |
| permission_setting_for_anyone_links |
| site_ownership_policies |
| teams_with_external_guest_as_owner |

### Missing From collectors.json

None.

### Missing From rules.json

None.

### Missing From recommendations.json

None.

## Duplicate Parameters

### Official Template Name Duplicates

None.

### Active Registry Duplicate Keys

None.

## Legacy Parameters

### Legacy Active Registry Parameters

None.

### Legacy Database assessment_parameters

| Parameter Key |
| --- |
| assigned_license |
| checking_sharing_permissions_for_each_sites_on_a_tenant |
| non_admin_users_can_register_applications |
| sensitivity_labels_are_applied |
| teams_anonymous_users |
| teams_external_unmanaged_user_communication |

## Orphaned Parameters

### Collector/Manifest Entries Not In Official CRA List

| Parameter Key | Location |
| --- | --- |
| assigned_license | collector_manifest.json |
| checking_sharing_permissions_for_each_sites_on_a_tenant | collector_manifest.json |
| device_without_compliance_policy | collector_manifest.json |
| non_admin_users_can_register_applications | collector_manifest.json |
| note_for_purview_if_e5_licenses_are_not_available_all_parameters_will_fail | collector_manifest.json |
| restricted_access_to_microsoft_entra_admin_center | collector_manifest.json |
| sensitive_sharepoint_site_excluded_from_copilot_search | collector_manifest.json |
| sensitivity_labels_are_applied | collector_manifest.json |
| teams_anonymous_users | collector_manifest.json |
| teams_external_unmanaged_user_communication | collector_manifest.json |

### Rule Entries Not In Official CRA List

None.

### Recommendation Entries Not In Official CRA List

None.
