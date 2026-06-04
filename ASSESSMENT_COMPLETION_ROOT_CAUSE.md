# Assessment Completion Root Cause

## Latest Failed Assessment Investigated

| Field | Value |
|---|---|
| assessment_id | `f499ec4c-6b6b-4b05-8991-5f47b3ce0db6` |
| job_id | `41ca3dfe-0e56-43b9-b859-d03ad059f048` |
| current_status | `incomplete` |
| progress_pct | `100.0` |
| job_status | `incomplete` |
| current_stage | `incomplete` |
| job_error | `21 collector(s) failed or were not collected; scoring and recommendations were not generated` |

## Counts At Failure

| Item | Count |
|---|---:|
| Artifacts | 44 |
| Findings | 23 |
| Recommendations | 0 |
| Reports | 0 |
| Collector total | 44 |
| Collector collected | 23 |
| Collector incomplete | 21 |

## Root Cause

The assessment did not complete because `runtime_assessment_service.run_assessment_job()` treated any collector failure as assessment-incomplete and returned before scoring, recommendation generation, and report generation.

The latest failed UI-created job had 21 collector failures. The failures were Graph token acquisition failures from Microsoft Entra ID token endpoint `401 Unauthorized`. Because the runtime returned early, it generated 23 findings, 44 artifacts, 0 recommendations, 0 scores, and no report bundle for that run.

## Failure Classes

| Failure Class | Count |
|---|---:|
| `Client error '401 Unauthorized' for url 'https://login.microsoftonline.com/fe4eff9a-f69c-48c0-921d-8006a6d5beb2/oauth2/v2.0/token'` | 21 |


## What Was Not The Root Cause

| Area | Finding |
|---|---|
| Timeout failures | No collector timeout was recorded. |
| Report generation failure | Report generation was never reached for the failed job. |
| Transaction rollback | No final transaction rollback was recorded; the job intentionally returned as `incomplete`. |
| Infinite collector loop | No infinite loop was found; collectors emitted failed/completed events and the job reached 100%. |

## Fix Applied

- Runtime now emits `assessment.collectors_incomplete` as a warning and continues to scoring, recommendations, and report generation.
- Graph app tokens are cached per tenant/app client to avoid repeated token endpoint calls across collectors in one process.
- Token failures now include Microsoft response body in the collector error text.

## Validation After Fix

| Field | Value |
|---|---|
| assessment_id | `201714d2-45d2-4cc0-b463-ffe60bc1d00f` |
| job_id | `620cb47b-663f-44a2-afe4-eaafe759492d` |
| status | `completed` |
| progress_pct | `100.0` |
| findings | 44 |
| recommendations | 44 |
| reports | 2 |
