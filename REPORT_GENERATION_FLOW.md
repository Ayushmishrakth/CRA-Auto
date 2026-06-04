# CRA Report Generation Flow

## Report Routes

Frontend route:

- `/assessments/:assessmentId/report`
- Component: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

Backend endpoints:

| Method | Endpoint | Backend Function |
|---|---|---|
| `GET` | `/api/v1/assessments/{assessment_id}` | `assessment_service.get_assessment` |
| `GET` | `/api/v1/assessments/{assessment_id}/findings` | `assessment_service.get_findings` |
| `GET` | `/api/v1/assessments/{assessment_id}/evidence` | `assessment_service.get_evidence` |
| `GET` | `/api/v1/assessments/{assessment_id}/recommendations` | `assessment_service.get_recommendations` |
| `GET` | `/api/v1/assessments/{assessment_id}/report` | `cra_report_service.get_report_bundle` |
| `POST` | `/api/v1/assessments/{assessment_id}/generate-report` | `cra_report_service.generate_report_bundle` |
| `GET` | `/api/v1/assessments/{assessment_id}/report/download?report_type=pdf` | `cra_report_service.get_report_artifact` |
| `GET` | `/api/v1/assessments/{assessment_id}/report/download?report_type=docx` | `cra_report_service.get_report_artifact` |

## Automatic Generation Path

Runtime path:

```text
POST /assessments/start
  -> assessment_service.start_assessment
  -> run_assessment_task
  -> runtime_assessment_service.run_assessment_job
  -> collectors
  -> apply_scores
  -> generate_recommendations
  -> cra_report_service.generate_report_bundle
  -> assessment completed
```

Files:

- `app/api/v1/assessments.py`
- `app/services/assessment_service.py`
- `app/tasks/assessment_tasks.py`
- `app/services/runtime_assessment_service.py`
- `app/services/reporting/cra_report_service.py`
- `app/services/reporting/cra_pdf_renderer.py`
- `app/services/reporting/cra_docx_renderer.py`

Important behavior:

- Automatic report generation happens only after collectors complete, scores are created, and recommendations are generated.
- If collectors are incomplete, runtime returns early with `assessment.status = incomplete`; report generation is skipped.

## Manual Generation Path

Frontend:

- `AssessmentReportPage.jsx`
- `handleGenerate`
- calls `generateAssessmentReport(assessmentId)` in `src/api/assessmentApi.js`

Backend:

- `POST /api/v1/assessments/{assessment_id}/generate-report`
- `cra_report_service.generate_report_bundle`

Tables read:

- `assessments`
- `assessment_findings`
- `assessment_recommendations`
- `assessment_artifacts`

Tables written:

- deletes existing `assessment_reports` for the assessment
- inserts PDF row
- inserts DOCX row
- updates `assessments.report_path`

Files written:

- `storage/reports/{assessment_id}/copilot-readiness-assessment.pdf`
- `storage/reports/{assessment_id}/copilot-readiness-assessment.docx`

## Report Data Model

`cra_report_service.build_report_data` loads:

- assessment header and scores
- findings with parameter relationships
- recommendations
- artifacts
- registry parameters
- registry recommendations

It builds:

- `summary`
- `analytics`
- `narrative`
- `sections`
- `report_model`
- `metadata`

Important implementation:

- `_build_parameter_rows` iterates every registry parameter, not only collected findings.
- Parameters without findings become `status = not_collected`.
- Missing artifacts become evidence `{ status: "missing" }`.
- This means the report can still produce a full skeleton even when most collectors are missing.

## Frontend Report Page Runtime

`AssessmentReportPage.loadReport` calls five APIs in parallel:

1. `getAssessment`
2. `getAssessmentFindings`
3. `getAssessmentEvidence`
4. `getAssessmentRecommendations`
5. `getAssessmentReport`

Partial failures:

- Findings/evidence/recommendations are individually caught and default to empty values.
- `getAssessment` and `getAssessmentReport` are not individually caught; either one failing trips the outer catch.

Render tree:

```text
AssessmentReportPage
  -> ReportPageErrorBoundary
  -> ReportStatusBadge
  -> ReportSummaryCards
  -> ReportCharts
  -> ReportDownloadPanel
```

## Report Blank Screen Investigation

Observed risk points:

1. `AssessmentReportPage.jsx:41-56`
   - `Promise.all` requires both `getAssessment` and `getAssessmentReport` to succeed.
   - A backend 500/401/422 from report bundle or assessment fetch sends the page to outer catch.

2. `AssessmentReportPage.jsx:66`
   - Error extraction uses `err.response?.data?.detail || err.message`.
   - Backend app errors use `{ error: { message } }`, so some backend errors can render as empty/unclear UI feedback.

3. `AssessmentReportPage.jsx:92-94`
   - While waiting for a slow/hung backend report endpoint, the page only shows the loading spinner.
   - If the spinner blends into the dark background or the request hangs, this appears like a blank dark screen.

4. `ReportPageErrorBoundary.jsx`
   - The error boundary is inside `AssessmentReportContent` return.
   - It catches render errors below line 104, but it cannot catch async API errors or exceptions thrown before the return.

5. `ReportCharts.jsx:34-71`
   - Uses Recharts `ResponsiveContainer`.
   - Safe arrays prevent data-shape crashes.
   - Empty arrays render empty charts, not a full blank screen.

Most likely root cause from code review:

- The blank page is most likely caused by the report endpoint request not completing or failing before content loads, especially `getAssessmentReport(assessmentId)` in `AssessmentReportPage.jsx:55`.
- If the assessment is `incomplete` or report data generation hits backend errors, the frontend error display does not reliably surface backend `{ error.message }`.
- The exact frontend line that blocks rendering is `AssessmentReportPage.jsx:41-56`, with the highest-risk call at line 55.

Backend lines to inspect when reproducing:

- `cra_report_service.get_report_bundle`: `app/services/reporting/cra_report_service.py:85-105`
- `cra_report_service.build_report_data`: `app/services/reporting/cra_report_service.py:156-205`
- `_build_parameter_rows`: same file below line 230

## Report Sections

Backend report model includes:

- Executive Summary
- Readiness Score
- Pillar Scores
- M365 Service Scores
- Severity Distribution
- Findings Summary
- Detailed Findings
- Recommendations
- Licensing Analysis
- User Activity Analysis
- Conclusion

Missing/weak sections today:

- True charts are represented as data tables in PDF/DOCX, not rendered images.
- Licensing analysis is mostly empty unless license-related parameters are collected.
- User activity analysis depends on collected user/activity parameters.
- Detailed findings are mostly `NOT COLLECTED` because only 7 collectors run.
