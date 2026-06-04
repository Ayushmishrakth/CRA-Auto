# Report UX Improvements

Date: 2026-06-01

## Goal

Make the report page reliable and understandable across these states:

```text
generated
not_generated
generation_failed
partial API failure
tenant access failure
```

## Report Status States

File: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

Added dedicated copy for:

```text
generated: report artifacts are available
not_generated: live report data is available, downloads are not yet generated
generation_failed: report data can still be reviewed, generation failed
```

File: `CRA-frontend/src/components/report/ReportStatusBadge.jsx`

Updated badge tone so `generation_failed` and `failed` display as critical.

File: `CRA-frontend/src/index.css`

Added `.info-banner` for non-error report status messaging.

## Diagnostics Panel

Frontend:

```text
CRA-frontend/src/pages/AssessmentReportPage.jsx
```

Backend:

```text
CRA-Tool/app/api/v1/assessments.py
CRA-Tool/app/services/reporting/cra_report_service.py
```

New frontend API:

```text
CRA-frontend/src/api/assessmentApi.js
getAssessmentReportDebug(assessmentId)
```

Backend routes:

```text
GET /api/v1/report-debug/{assessment_id}
GET /api/v1/assessment/report-debug/{assessment_id}
```

The second path is retained for compatibility with the existing route.

Diagnostics shown:

```text
assessment status
tenant id
artifact count
finding count
recommendation count
report count
per-request frontend errors
```

## Partial Data Behavior

The report page no longer requires every API call to succeed before rendering.

Fallbacks:

```text
findings: []
evidence: { parameters: [] }
recommendations: []
report: {}
diagnostics: null
```

Blocking errors are still surfaced for assessment/report failures, but the page shell and diagnostics remain visible when possible.

## User Impact

Before:

```text
One failed API call could make the report page appear blank or show only a generic Axios error.
```

After:

```text
The page renders available report data.
Backend errors are readable.
Download state is explicit.
Diagnostics explain missing artifacts/findings/recommendations.
```

## Verification

Frontend build passed:

```text
npm run build
```

Backend compile passed:

```text
python -m py_compile app/api/v1/assessments.py app/services/reporting/cra_report_service.py app/services/graph_cra_collector_service.py
```

