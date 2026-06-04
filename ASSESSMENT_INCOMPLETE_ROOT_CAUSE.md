# Assessment Incomplete Root Cause

Date: 2026-06-01

## Latest Assessment Investigated

Assessment:

```text
26d70226-be91-47aa-a7ca-861dabd2e018
tenant_id: fe4eff9a-f69c-48c0-921d-8006a6d5beb2
status: incomplete
progress_pct: 100
```

Job:

```text
job_id: d8e1869d-060d-455f-a004-cc079265b65c
status: incomplete
error_message: 3 collector(s) failed or were not collected; scoring and recommendations were not generated
```

Runtime metadata:

```text
collector_total: 7
collector_collected: 4
collector_incomplete: 3
collector_failures: 3
collector_timeouts: 0
collector_retries: 0
graph_calls: 5
findings_created: 4
scores_created: 0
```

## Exact Collector Failures

All three failed collectors used the same malformed Microsoft Graph endpoint:

```text
https://graph.microsoft.com/v1.0/policies/authorizationPolicy/authorizationPolicy?$select=id,allowInvitesFrom,defaultUserRolePermissions
```

Graph returned:

```text
400 Bad Request
```

Failed parameters:

| Parameter | Collector | Failure |
|---|---|---|
| `entra_tenant_creation_by_non_admin` | `powershell.entra_tenant_creation_by_non_admin` | 400 from malformed authorization policy endpoint |
| `entra_third_party_app_integrations` | `powershell.entra_third_party_app_integrations` | 400 from malformed authorization policy endpoint |
| `guest_invite_settings` | `powershell.guest_invite_settings` | 400 from malformed authorization policy endpoint |

## Runtime Logic Causing Incomplete Status

File: `CRA-Tool/app/services/runtime_assessment_service.py`

Collector failures are counted here:

```text
481-513: collector_result errors increment collector_failures
605-631: raised exceptions increment collector_failures
633-640: collector_incomplete = collector_failures + collector_timeouts
```

Assessment is marked incomplete here:

```text
680: findings = await _collect_findings(...)
681: incomplete_count = job.metadata_payload["collector_incomplete"]
682-728: if incomplete_count, assessment.status = "incomplete"
689-691: error_message says scoring and recommendations were not generated
720-728: function returns before scoring and recommendations
```

Because `collector_incomplete` was `3`, the runtime intentionally skipped:

```text
apply_scores(...)
generate_recommendations(...)
```

That is why:

```text
overall_score: null
recommendation_count: 0
assessment.status: incomplete
```

## Fix Applied

File: `CRA-Tool/app/services/graph_cra_collector_service.py`

Changed the existing authorization policy collector endpoint from:

```text
/policies/authorizationPolicy/authorizationPolicy
```

to:

```text
/policies/authorizationPolicy
```

Also corrected persisted `graph_endpoint` strings for the three affected collectors.

This is a targeted bug fix to existing collectors, not a new collector implementation.

## Expected Result On Next Assessment

With `Policy.Read.All` already granted, the three authorization policy collectors should stop failing with `400 Bad Request`.

If no other collector fails:

```text
collector_incomplete: 0
assessment proceeds to scoring
recommendations are generated
assessment.status becomes completed
```

Existing incomplete assessments are historical rows and will not automatically change status.

## Verification

Backend touched files compile:

```text
python -m py_compile app/api/v1/assessments.py app/services/reporting/cra_report_service.py app/services/graph_cra_collector_service.py
```

Report debug probe for the latest historical assessment returned:

```text
assessment_status: incomplete
tenant_id: fe4eff9a-f69c-48c0-921d-8006a6d5beb2
artifact_count: 7
finding_count: 4
recommendation_count: 0
report_count: 0
```

