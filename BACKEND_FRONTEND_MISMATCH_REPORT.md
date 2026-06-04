# Backend Frontend Mismatch Report

## Backend Counts

| Source | Count |
| --- | ---: |
| assessment_findings rows | 65 |
| assessment_artifacts rows | 65 |
| assessment_recommendations rows | 65 |
| assessment_reports rows | 2 |
| API `/assessments/{id}/evidence` expected parameter rows | 65 |

## Backend Status Distribution

| Status | Findings | Artifacts |
| --- | ---: | ---: |
| PASS / collected | 1 | 1 |
| COLLECTION_ERROR / failed | 64 | 64 |

## Frontend Rendering Path

| Page | Data Source | Default Filter | Expected Rows Rendered For This Assessment |
| --- | --- | --- | ---: |
| Assessment Detail | `getAssessmentEvidence()` then `payload.parameters` | `ALL` | 65 |
| Evidence Page | `getAssessmentEvidence()` then `payload.parameters` | `All` | 65 |
| Findings fallback | `getAssessmentFindings()` context fallback only if evidence rows absent | none | 65 |

## Filtering Audit

| Status | Hidden By Default? | Notes |
| --- | --- | --- |
| FAIL | No | Included in `ALL`/`All`; has explicit filter. |
| WARNING | No by default | Included in `ALL`/`All`; no explicit dropdown/segmented option on current detail/evidence pages. |
| LICENSING_REQUIRED | No | Included in `ALL`/`All`; has explicit filter. |
| MANUAL_VALIDATION | No | Included in `ALL`/`All`; has explicit filter. |
| COLLECTION_ERROR | No | Included in `ALL`/`All`; has explicit filter. |
| FAILED / FAILED_COLLECTOR | No by default if returned | Not explicit on Evidence page; current API maps persisted finding status `collection_error` to `COLLECTION_ERROR`. |

## Conclusion

There is no evidence in the code path that the frontend default view intentionally hides non-PASS controls. The persisted backend data contains 65 findings and the evidence API is designed to return all 65 registry parameters. If the user sees only one PASS, that is because only one collector produced successful evidence; the remaining 64 rows are collection errors, not PASS outcomes.
