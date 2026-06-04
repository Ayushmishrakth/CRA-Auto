# Frontend Stabilization Report

Date: 2026-06-01

## Scope

Stabilized assessment and report loading without redesigning the frontend architecture.

## Changes Made

### Standard API Error Extraction

File: `CRA-frontend/src/utils/apiErrors.js`

Added `extractApiError(error, fallback)` and kept `getApiErrorMessage` as an alias.

Supported backend shapes:

```text
response.data.error.message
response.data.detail
response.data.message
error.message
fallback
```

This fixes the previous issue where backend errors like `TENANT_ACCESS_DENIED` were hidden behind generic Axios messages.

### AssessmentReportPage Reliability

File: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

The previous page used one `Promise.all` where `getAssessment()` or `getAssessmentReport()` could reject and collapse the whole page load.

Updated behavior:

```text
getAssessment is recovered with a meaningful error
getAssessmentFindings has fallback []
getAssessmentEvidence has fallback { parameters: [] }
getAssessmentRecommendations has fallback []
getAssessmentReport has fallback {}
getAssessmentReportDebug has fallback null
```

The page now renders partial report data when possible and records per-request diagnostics instead of treating every failed child call as a full blank-page failure.

### Assessment Detail Reliability

File: `CRA-frontend/src/context/AssessmentContext.jsx`

Changed `fetchAssessment()` so the assessment shell is loaded first, then secondary data loads with per-request fallbacks:

```text
findings -> []
recommendations -> []
score -> null
events -> []
job -> null
```

Also clears stale active assessment state at the start of a new assessment route load.

### Tenant Validation

Files:

```text
CRA-frontend/src/pages/AssessmentDetailPage.jsx
CRA-frontend/src/pages/AssessmentEvidencePage.jsx
CRA-frontend/src/pages/AssessmentReportPage.jsx
CRA-frontend/src/pages/AssessmentsPage.jsx
CRA-frontend/src/pages/DashboardPage.jsx
```

Validation added or tightened:

```text
Detail page checks loaded assessment tenant against signed-in user tenant.
Evidence page loads assessment first and blocks mismatched tenant render.
Report page records tenant mismatch as a diagnostics error.
Assessments list filters rows to current user tenant.
Dashboard summaries and recent rows filter to current user tenant.
```

Backend already enforces tenant access through `assessment_service.get_assessment()` and `_assert_user_tenant()`.

## Verification

Frontend production build passed:

```text
npm run build
```

Result:

```text
3059 modules transformed
✓ built
```

Build warning:

```text
Some chunks are larger than 500 kB after minification.
```

This is an existing bundle-size warning, not a stabilization failure.

## Remaining Risk

Report and assessment pages now recover from partial data failures, but a hard auth failure still depends on the app-level login/session flow. That is expected behavior.

