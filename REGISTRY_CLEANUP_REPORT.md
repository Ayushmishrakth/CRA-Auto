# Registry Cleanup Report

## Before Cleanup

| Source | Count |
|---|---:|
| Approved parameter map | 65 |
| Registry parameters | 76 |
| Database assessment_parameters | 76 |

## Removed Legacy Parameters

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


## After Cleanup

| Source | Count |
|---|---:|
| Registry parameters | 65 |
| Registry rules | 65 |
| Registry collectors | 65 |
| Registry recommendations | 65 |
| Database assessment_parameters | 65 |

## Validation

- Every approved parameter has one registry parameter entry.
- Every approved parameter has one registry rule entry.
- Every approved parameter has one registry collector metadata entry.
- Every approved parameter has one registry recommendation entry.
- No duplicate parameter keys remain in registry or DB.
- No `GRAPH_COLLECTORS` key exists outside the approved registry.

## Runtime Scope

The runtime remains limited to approved parameters that have an app-native collector in `GRAPH_COLLECTORS`. Current executable collector count is 44. The remaining 21 approved parameters stay in inventory but are not executed until collectors are implemented in future phases.
