# Post-Reset Regression Report

## Comparison Baselines

The same-tenant pre-reset assessment rows for `fe4eff9a-f69c-48c0-921d-8006a6d5beb2` are not present because the tenant reset deleted runtime assessment history for that tenant. The closest surviving successful baseline is assessment `71fd7075b4344a44b843f52485170498` for tenant `fa060b6a-b4c6-46c2-a25b-591646e5c90c`. The post-reset completed assessment for the reset tenant is `cf07d3b25b7544b79b73a5a4166cc2e1`. The latest partial/live-validation run is `4a679e90e2064b2baefff2f569f98778`.

| Item | Last Successful Surviving Baseline | Latest Completed After Reset | Latest Partial After Reset |
| --- | --- | --- | --- |
| assessment_id | `71fd7075b4344a44b843f52485170498` | `cf07d3b25b7544b79b73a5a4166cc2e1` | `4a679e90e2064b2baefff2f569f98778` |
| tenant_id | `fa060b6a-b4c6-46c2-a25b-591646e5c90c` | `fe4eff9a-f69c-48c0-921d-8006a6d5beb2` | `fe4eff9a-f69c-48c0-921d-8006a6d5beb2` |
| status | `completed` | `completed` | `running` |
| progress_pct | 100.0 | 100.0 | 29.63 |
| findings | 59 | 65 | 19 |
| artifacts | 64 | 65 | 19 |
| recommendations | 59 | 65 | 0 |
| reports | 2 | 2 | 0 |
| collector_runtime | `graph` | `hybrid_manifest_routed` | `phase7b_powershell` |
| graph_calls | 73 | 2 | n/a |
| collector_failures | 5 | 64 | n/a |

## Status Distribution

| Source | Findings | Artifacts |
| --- | --- | --- |
| Successful baseline | `{'fail': 36, 'licensing_required': 9, 'manual_validation_required': 1, 'not_supported': 1, 'pass': 12}` | `{'collected': 59, 'failed': 5}` |
| Post-reset completed | `{'collection_error': 64, 'pass': 1}` | `{'collected': 1, 'failed': 64}` |
| Post-reset partial | `{'collection_error': 9, 'manual_validation': 8, 'warning': 2}` | `{'collected': 2, 'failed': 17}` |

## What Changed

1. The surviving successful baseline used `collector_runtime=graph`, made `73` Graph calls, and persisted real PASS/FAIL evidence.
2. The post-reset completed runs use `collector_runtime=hybrid_manifest_routed`, start 64 PowerShell collectors, and fail them before stdout/stderr/CSV with empty `NotImplementedError` artifacts.
3. The latest partial live-validation run was launched with `interactive_powershell_disabled=true`, which sets PowerShell auth modes to `disabled`; Teams collectors then fail with `Unsupported Microsoft Teams auth mode 'disabled'`.
4. SharePoint live validation shows `SharePoint admin_url missing; manual validation required.`
5. Exchange live validation shows WAM interactive auth failure: `A window handle must be configured`.

## Reset Impact Finding

The reset removed same-tenant pre-reset runtime evidence, so exact same-tenant before/after evidence cannot be reconstructed from the database. The reset did not remove the `connected_tenants` row, consent status, application client ID, service principal ID, encrypted secret, or granted permission payload for the post-reset tenant.

The regression is therefore not proven as deleted tenant deployment/consent. The proven runtime change is collector execution mode/auth state after reset: Graph-first successful evidence collection is no longer what the completed post-reset assessments are doing for 64 parameters.
