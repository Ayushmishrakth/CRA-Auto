# Frontend Parameter Audit

Generated: 2026-06-03 20:10:47

Authority count expected by UI: **65 official CRA parameters**.

## Surface Audit

| Surface | Files | Finding | Status |
| --- | --- | --- | --- |
| Dashboard | src/pages/DashboardPage.jsx | Uses `coverage.total_parameters ?? visibleRows.length` for Parameters Assessed. Compatible with 65 only when backend coverage is 65. | Partial pass |
| Assessment Page | src/pages/AssessmentDetailPage.jsx | Displays parameter name/status/actual/expected/severity, but still exposes raw evidence JSON and uses parameter_key internally. | Fail for Step 6 hiding requirement |
| Evidence Page | src/pages/AssessmentEvidencePage.jsx | Displays actual/expected/status, but includes a Raw toggle that renders JSON from evidence/artifact_json. | Fail for Step 6 hiding requirement |
| Recommendations Page | src/pages/AssessmentReportPage.jsx / dashboard blockers | Recommendations depend on backend payloads and do not independently reconcile all 65 official parameters. | Needs backend-aligned data |
| Report Page | src/pages/AssessmentReportPage.jsx | Consumes report/evidence/analytics; frontend count depends on API payload. | Partial pass |
| Parameters Page | src/pages/ParametersPage.jsx | Displays parameter_key, collection method, PowerShell/script details via How To Check, source files, and technical search terms. | Fail for hidden internal names requirement |
| Execution Panel | src/components/assessment/AssessmentExecutionPanel.jsx | Shows collector events, runtime, collector failures/timeouts, stdout labels, and payload collector/parameter_key. | Operational page exposes internal collector names |
| Findings Table | src/components/assessment/FindingsTable.jsx | Expanded details show Collector and raw evidence JSON/code. | Fail for Step 6 hiding requirement |

## Count/Visibility Findings

- The UI does not maintain its own official 65-parameter master list. It relies on backend payloads from registry, evidence, recommendations, and report APIs.
- Dashboard can show 65 only when backend `coverage.total_parameters` is 65.
- Parameters page will show 65 only when `/registry/parameters` returns the active registry, but it currently exposes technical fields (`parameter_key`, collection method, PowerShell mapping/source refs).
- Assessment/Evidence pages can show fewer than 65 when runtime artifacts/findings are missing. Latest local DB assessment currently has 64 artifact parameter rows and 59 finding parameter rows.
- Raw JSON and collector/runtime names are exposed in multiple frontend components, so Step 6 is not satisfied yet.

## Required Frontend Synchronization Work

- Assessment page should render one row per official/business parameter returned by a reconciled backend endpoint.
- Hide collector names, `parameter_key`, Graph endpoints, PowerShell mapping, source script/source CSV, internal IDs, and raw JSON from business-facing parameter views.
- Keep collector/runtime/debug details only in an admin/debug view if needed, not in Dashboard, Assessment, Evidence, Recommendations, or Report business pages.
- Dashboard summary should use authoritative coverage fields: total parameters, passed, failed, licensing required, manual validation, coverage percentage, readiness score, and service breakdown.
