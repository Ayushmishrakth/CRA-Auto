# Tenant Configuration Diff

## Tenant Records

| Field | Successful Baseline Tenant `fa060b6a-b4c6-46c2-a25b-591646e5c90c` | Post-Reset Tenant `fe4eff9a-f69c-48c0-921d-8006a6d5beb2` | Lost By Reset? |
| --- | --- | --- | --- |
| tenant_name | Nexora Innovations Private Limited | WealthScape | No, different tenant records |
| status | ACTIVE | ACTIVE | No |
| deployment_status | ACTIVE | ACTIVE | No |
| consent_status | connected | connected | No |
| consent_granted_at | 2026-06-02 15:50:26.112415 | 2026-06-03 20:58:13.786765 | No |
| application_client_id | 976c7fa8-4af1-48d4-8bdf-c6df2a35ebbd | 33688cf5-d33b-4483-992a-d3e2ce6e1b15 | No |
| application_object_id | c174b307-1c33-4f28-a9f9-c542589a4a32 | 0ee93cc1-d128-4989-ba52-e12336616048 | No |
| service_principal_id | 93ca96ef-cf90-4649-9ee9-cebeef46d70a | 535abf5d-0c19-4e13-b96e-eb3a402acc99 | No |
| encrypted_client_secret | present | present | No |
| secret_expiration | 2028-06-02 15:49:26.982035 | 2028-06-03 20:57:58.347927 | No |
| granted app role count | 20 | 20 | No |
| required permissions count | 20 | 20 | No |

## Graph Configuration

Both tenant rows contain Microsoft Graph application registration details, app role assignment count `20`, service principal IDs, encrypted client secrets, and consent status `connected`.

## SharePoint Configuration

The post-reset tenant deployment diagnostics do not contain a collector `admin_url`. The latest partial assessment produced `SharePoint admin_url missing; manual validation required` for `active_sites_count`. This is a runtime/collector configuration gap, not an assessment-data reset deletion from the tables inspected.

## Collector Configuration

`app/config/assessment_registry/collectors.json` and `app/config/collector_manifest.json` are tenant-independent files and were not deleted by reset. Current manifest entries remain available. The execution regression is in selected runtime/auth behavior, not a missing manifest file.

## Exact Lost Record Assessment

No tenant deployment, consent, graph app, service principal, encrypted secret, or collector manifest record was found missing after reset. What was intentionally lost is same-tenant historical assessment runtime evidence, so same-tenant before/after proof cannot be produced from DB rows.
