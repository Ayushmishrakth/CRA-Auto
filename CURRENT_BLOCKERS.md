# CRA Platform Current Blockers

## Executive Summary

The platform has a working authentication, tenant deployment, consent, and initial assessment pipeline. The main blockers are not login or Graph app registration anymore. The current blockers are collector coverage, incomplete-assessment behavior, report-page reliability, and production infrastructure assumptions.

## Blocker 1: Report Page Blank Screen

Affected route:

- `/assessments/:assessmentId/report`

Frontend file:

- `CRA-frontend/src/pages/AssessmentReportPage.jsx`

Likely blocking line:

- `AssessmentReportPage.jsx:55`
- `getAssessmentReport(assessmentId)` is part of a `Promise.all`.

Why this blocks:

- If `getAssessmentReport` hangs or backend report data generation fails, the page remains loading or falls into a weak error state.
- The page catches findings/evidence/recommendation API failures individually, but not `getAssessment` or `getAssessmentReport`.
- Backend error envelope is `{ error: { message } }`; frontend currently checks `err.response?.data?.detail`, so some errors do not show clearly.

Backend files involved:

- `app/api/v1/assessments.py`
- `app/services/reporting/cra_report_service.py`

Immediate investigation steps:

1. Open browser console and network tab for `/assessments/{id}/report`.
2. Check whether `GET /api/v1/assessments/{id}/report` returns, hangs, 401s, 404s, 422s, or 500s.
3. Check backend logs around `cra_report_service.build_report_data`.
4. Check `GET /api/v1/assessment/report-debug/{assessment_id}` for missing sections and counts.

No fix applied in this discovery pass.

## Blocker 2: Only 7 Collectors Run

Runtime gate:

- `app/services/runtime_assessment_service.py`
- `FIRST_OPERATIONAL_GRAPH_PARAMETERS`
- `_runtime_parameters`

Current selected parameters:

- `global_administrator_accounts`
- `guest_users_count`
- `account_enabled`
- `user_information`
- `guest_invite_settings`
- `entra_tenant_creation_by_non_admin`
- `entra_third_party_app_integrations`

Impact:

- 69 / 76 parameters are not evaluated.
- Most report sections are incomplete or `NOT COLLECTED`.
- Scores are based only on a tiny control subset.

## Blocker 3: Fail-Closed Runtime Prevents Scoring

File:

- `app/services/runtime_assessment_service.py`

Behavior:

- If any selected collector fails or is not collected, runtime marks the assessment `incomplete`.
- It returns before scoring, recommendations, and report generation.

Impact:

- No complete score.
- No generated recommendation rows.
- Report may be missing generated artifacts.

## Blocker 4: Report Generation Depends on Local Filesystem

File:

- `app/services/reporting/cra_report_service.py`

Current storage:

- `storage/reports/{assessment_id}/copilot-readiness-assessment.pdf`
- `storage/reports/{assessment_id}/copilot-readiness-assessment.docx`

Impact:

- Not safe for multi-worker or container deployments.
- Downloads fail if API instance serving request does not have the file.

## Blocker 5: Split Data Model

Runtime model:

- `assessment_artifacts`
- `assessment_findings`
- `assessment_recommendations`
- `assessment_reports`

Production parameter model:

- `cra_parameters`
- `cra_parameter_evidence`
- `cra_assessment_results`

Impact:

- Future code can accidentally read from the wrong result model.
- Reporting currently reads runtime findings/artifacts, not `cra_assessment_results`.

## Blocker 6: PowerShell Collector Path Is Not Production Ready

Files:

- `app/services/powershell/powershell_runtime.py`
- `app/powershell/*/*_master.ps1`
- `app/config/collector_manifest.json`

Issues:

- Local script execution.
- Local module dependencies.
- Local CSV output.
- Runtime currently bypasses most PowerShell parameters anyway.

## Blocker 7: SQLite Development Database

Current:

- SQLite by default.

Production target:

- PostgreSQL.

Required before production:

- Test migrations against PostgreSQL.
- Review JSON field behavior.
- Review UUID storage.
- Review indexes and query plans.
- Move report artifacts to object/shared storage.

## Blocker 8: Frontend Error Handling Is Inconsistent

Examples:

- Some pages read `err.response?.data?.detail`.
- Backend app errors return `err.response.data.error.message`.
- Shared helper exists in `src/utils/apiErrors.js`, but not all pages use it.

Impact:

- Users see blank or unhelpful errors.
- Report blank screen is harder to diagnose.

## Recommended Next Investigation Order

1. Reproduce report blank screen with browser Network tab and backend logs.
2. Run `GET /api/v1/assessment/report-debug/{assessment_id}` for the failing assessment.
3. Confirm assessment status is `completed` vs `incomplete` vs `failed`.
4. Confirm rows exist in:
   - `assessment_artifacts`
   - `assessment_findings`
   - `assessment_recommendations`
   - `assessment_reports`
5. Decide whether runtime should score/report partial collector results.
6. Expand collector implementation beyond the 7 Graph collectors.
7. Normalize report page API error handling.
