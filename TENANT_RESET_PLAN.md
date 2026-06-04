# Tenant Reset Plan

## Objective

Reset runtime-generated CRA assessment data for a selected tenant while preserving tenant-independent configuration, application users, connected tenant configuration, parameter definitions, rules, registry metadata, and collector manifests.

## Selected Tenant

- Tenant ID: `fe4eff9a-f69c-48c0-921d-8006a6d5beb2`
- Tenant Name: `WealthScape`

## Runtime Tables Identified

The following tables store tenant assessment runtime data and are in scope for reset:

| Table | Scope | Reset Behavior |
| --- | --- | --- |
| `assessments` | Assessment run records | Delete rows for selected `tenant_id` |
| `assessment_jobs` | Runtime job records | Delete rows for selected `tenant_id` and assessment IDs |
| `assessment_events` | Assessment event stream | Delete rows for selected `tenant_id` and assessment IDs |
| `assessment_artifacts` | Collector artifacts | Delete rows for selected `tenant_id` and assessment IDs |
| `assessment_findings` | PASS/FAIL/control findings | Delete rows linked to selected tenant assessment IDs |
| `assessment_recommendations` | Runtime recommendations | Delete rows for selected `tenant_id` and assessment IDs |
| `assessment_reports` | Generated report records | Delete rows linked to selected tenant assessment IDs |
| `audit_logs` | Application audit history | Delete only assessment-related logs for selected tenant |
| `cra_parameter_evidence` | Legacy parameter evidence | Validate zero or delete tenant-scoped rows if present |
| `cra_assessment_results` | Legacy assessment results | Validate zero or delete tenant-scoped rows if present |

## Preserved Tables And Data

The reset must preserve:

- `assessment_parameters`
- `assessment_rules`
- `app/config/assessment_registry/*.json`
- `app/config/collector_manifest.json`
- `connected_tenants`
- `users`
- authentication/session records not directly tied to assessment history
- tenant app registration and consent configuration

## Backend Operation

Endpoint:

`POST /api/v1/admin/reset-tenant/{tenant_id}`

The reset operation:

1. Selects all assessment IDs belonging to the selected tenant.
2. Counts runtime rows before deletion.
3. Deletes dependent runtime rows in foreign-key-safe order.
4. Deletes only assessment-related audit logs for the tenant.
5. Deletes generated report files under `storage/reports`.
6. Deletes generated artifact directories under `artifacts`.
7. Preserves all registry, rule, collector, tenant, and user data.

## Frontend Operation

Location:

`Settings -> Tenant Administration`

Action:

`Reset Assessment Data`

Confirmation message:

`This will permanently delete all CRA assessment results for this tenant. Registry definitions and configuration will be preserved.`

After success, the frontend clears assessment context for the tenant and refreshes the tenant assessment list.

