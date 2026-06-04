# Database Sync Report

Generated: 2026-06-03 20:48:36

## Result

| Inventory | Count | Expected | Status |
| --- | --- | --- | --- |
| Official registry parameters | 65 | 65 | OK |
| Database active assessment_parameters | 65 | 65 | OK |
| Database active assessment_rules | 65 | 65 | OK |
| Inactive legacy DB parameters | 6 | Preserved history | OK |

## Missing Active Parameters

None.

## Active Legacy Parameters

None.

## Inactive Legacy Parameters Preserved

| Parameter Key |
| --- |
| assigned_license |
| checking_sharing_permissions_for_each_sites_on_a_tenant |
| non_admin_users_can_register_applications |
| sensitivity_labels_are_applied |
| teams_anonymous_users |
| teams_external_unmanaged_user_communication |

## Seeding Logic

`CRA-Tool/scripts/sync_registry_database.py` and `ensure_registry_seeded()` synchronize active database rows from the registry, update existing official rows, create missing official rows, create/update rules, and mark non-official legacy rows inactive.
