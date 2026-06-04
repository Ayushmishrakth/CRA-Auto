# Parameter Sync Audit

## Inventory Counts

| Source | Count |
|---|---:|
| Approved parameter map | 65 |
| Registry parameters | 65 |
| Database assessment_parameters | 65 |
| Runtime Graph collectors | 44 |
| Runtime registered but not implemented collectors | 21 |

## Duplicate Parameters

| Source | Duplicates |
|---|---|
| Approved parameter map | None detected by row number/name extraction |
| Registry | None |
| Database | None |

## Cleanup Applied

Removed 11 legacy/non-approved parameters from registry JSON and unreferenced DB rows:

- `restricted_access_to_microsoft_entra_admin_center`
- `days_to_retain_a_deleted_user_s_onedrive`
- `inactive_site_policies`
- `site_ownership_policies`
- `auto_expiration_policy_for_inactive_m365_groups`
- `device_without_compliance_policy`
- `expiration_policy_for_anyone_links`
- `permission_setting_for_anyone_links`
- `sensitive_sharepoint_site_excluded_from_copilot_search`
- `teams_with_external_guest_as_owner`
- `note_for_purview_if_e5_licenses_are_not_available_all_parameters_will_fail`


## Missing Runtime Collectors

These approved parameters remain in the 65-parameter specification but do not yet have app-native Graph collectors. They are not executed by the stabilized runtime until implemented:

- `audit_log_retention_duration`
- `audit_logs_enabled`
- `checking_sharing_permissions_for_each_sites_on_a_tenant`
- `compliance_score_overview`
- `custom_banned_password_list`
- `customer_lockbox`
- `dlp_rules_configured`
- `emergency_access_accounts`
- `external_sharing_settings`
- `external_storage_providers_in_owa`
- `full_calendar_schedules_able_to_be_shared_externally`
- `getting_all_sites_with_sensitivity_keywords_on_a_tenant`
- `information_protection_labels_applied`
- `secure_score_percentage`
- `sensitivity_labels_applied_to_teams`
- `sensitivity_labels_are_applied`
- `sensitivity_labels_configured_and_applied`
- `sharepoint_and_onedrive_guest_access_expiry`
- `sharepoint_modern_authentication`
- `sharing_settings_external_internal`
- `storage_quota_consumption`


## Result

Parameter inventory now matches the approved assessment specification: 65 registry rows and 65 database rows.
