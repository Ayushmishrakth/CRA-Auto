# Report Failure Root Cause Investigation

Date: 2026-06-01  
Scope: `/assessments/:assessmentId/report` and `GET /api/v1/assessments/{assessment_id}/report`  
Constraint followed: no code redesign, no collector implementation, no refactor.

## Executive Finding

`AssessmentReportPage` should not be blank when the backend report endpoint returns a normal `200` response. The React page has loading, error, and empty-data render states.

The backend `GET /api/v1/assessments/{assessment_id}/report` endpoint does **not** require an `assessment_reports` row. It builds live report data from assessment, findings, recommendations, artifacts, and registry data, then returns `status: "not_generated"` when there are no generated PDF/DOCX artifacts.

Live local DB probe using the WealthScape user `deep@wealthscape.in` and latest assessment `26d70226-be91-47aa-a7ca-861dabd2e018` succeeded:

```text
bundle_status not_generated
download_ready False
artifact_count 0
summary: 4 findings, 76 parameters, 72 not collected
analytics_keys: assessment_scores, licensing_readiness, m365_service_scores, not_collected,
pass_fail, pillar_distribution, pillar_scores, readiness_gauge,
security_governance_best_practice, service_distribution, severity_distribution
```

The only live failure reproduced was tenant access failure when the report service was executed as the first DB user, whose `microsoft_tid` does not match the assessment tenant:

```text
EXCEPTION TenantAccessException Tenant is not available to the current user
```

Therefore, if the page is blank in browser, the most likely root causes are:

1. The report page request is failing before render because `getAssessment()` or `getAssessmentReport()` rejects inside `Promise.all`.
2. Frontend error display reads `err.response?.data?.detail`, but backend errors are returned as `error.message`, so the page shows generic Axios text instead of useful backend details.
3. A stale or wrong CRA JWT can produce `401` or `403`; `axiosClient` clears tokens on `401`.
4. A true backend `500` can occur only from unhandled report-building exceptions such as registry validation or schema/response validation, not from incomplete assessment or missing report artifacts.

## 1. Frontend Route And Component

Route mapping:

```text
CRA-frontend/src/routes/AppRoutes.jsx
30: <Route path="/assessments/:assessmentId" element={<AssessmentDetailPage />} />
31: <Route path="/assessments/:assessmentId/evidence" element={<AssessmentEvidencePage />} />
32: <Route path="/assessments/:assessmentId/report" element={<AssessmentReportPage />} />
```

Component: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

### Lines 1-150

```jsx
1 import { useEffect, useState } from "react";
2 import { Link, useParams } from "react-router-dom";
3 import { ArrowLeft, FilePlus2 } from "lucide-react";
4 import {
5   getAssessment,
6   getAssessmentEvidence,
7   getAssessmentFindings,
8   getAssessmentRecommendations,
9   generateAssessmentReport,
10   getAssessmentReport,
11 } from "../api/assessmentApi";
12 import LoadingSpinner from "../components/LoadingSpinner";
13 import ReportCharts from "../components/report/ReportCharts";
14 import ReportDownloadPanel from "../components/report/ReportDownloadPanel";
15 import ReportPageErrorBoundary from "../components/report/ReportPageErrorBoundary";
16 import ReportStatusBadge from "../components/report/ReportStatusBadge";
17 import ReportSummaryCards from "../components/report/ReportSummaryCards";
18
19 function AssessmentReportContent() {
20   const { assessmentId } = useParams();
21   const [assessmentData, setAssessmentData] = useState(null);
22   const [findings, setFindings] = useState([]);
23   const [evidence, setEvidence] = useState([]);
24   const [recommendations, setRecommendations] = useState([]);
25   const [report, setReport] = useState(null);
26   const [loading, setLoading] = useState(true);
27   const [generating, setGenerating] = useState(false);
28   const [error, setError] = useState(null);
29
30   const loadReport = async () => {
31     setLoading(true);
32     setError(null);
33     try {
34       console.log("REPORT_PAGE_MOUNTED");
35       const [
36         assessment,
37         findingData,
38         evidenceData,
39         recommendationData,
40         reportData,
41       ] = await Promise.all([
42         getAssessment(assessmentId),
43         getAssessmentFindings(assessmentId, { limit: 100 }).catch((err) => {
44           console.error("REPORT_FINDINGS_API_ERROR", err.response?.data || err.message);
45           return [];
46         }),
47         getAssessmentEvidence(assessmentId).catch((err) => {
48           console.error("REPORT_EVIDENCE_API_ERROR", err.response?.data || err.message);
49           return { parameters: [] };
50         }),
51         getAssessmentRecommendations(assessmentId).catch((err) => {
52           console.error("REPORT_RECOMMENDATIONS_API_ERROR", err.response?.data || err.message);
53           return [];
54         }),
55         getAssessmentReport(assessmentId),
56       ]);
57       console.log("ASSESSMENT_DATA", assessment);
58       console.log("REPORT_DATA", reportData);
59       setAssessmentData(assessment);
60       setFindings(findingData ?? []);
61       setEvidence(evidenceData?.parameters ?? []);
62       setRecommendations(recommendationData ?? []);
63       setReport(reportData ?? {});
64     } catch (err) {
65       console.error("REPORT_API_ERROR", err.response?.data || err.message);
66       setError(err.response?.data?.detail || err.message);
67       setReport({});
68     } finally {
69       setLoading(false);
70     }
71   };
72
73   useEffect(() => {
74     loadReport();
75   }, [assessmentId]);
76
77   const handleGenerate = async () => {
78     setGenerating(true);
79     setError(null);
80     try {
81       const reportData = await generateAssessmentReport(assessmentId);
82       console.log("REPORT_DATA", reportData);
83       setReport(reportData ?? {});
84     } catch (err) {
85       console.error("REPORT_GENERATE_API_ERROR", err.response?.data || err.message);
86       setError(err.response?.data?.detail || err.message);
87     } finally {
88       setGenerating(false);
89     }
90   };
91
92   if (loading) {
93     return <LoadingSpinner label="Loading report..." />;
94   }
95
96   const safeReport = report ?? {};
97   const summary = safeReport.summary ?? {};
98   const analytics = safeReport.analytics ?? {};
99   const safeFindings = findings ?? [];
100   const safeRecommendations = recommendations ?? [];
101   const safeEvidence = evidence ?? [];
102
103   return (
104     <ReportPageErrorBoundary
105       failedProps={{
106         assessmentId,
107         assessmentData,
108         report: safeReport,
109         findings: safeFindings,
110         evidence: safeEvidence,
111         recommendations: safeRecommendations,
112       }}
113     >
114       <div className="page-stack report-page">
115         <div className="page-header">
116           <div>
117             <Link className="back-link" to={`/assessments/${assessmentId}`}>
118               <ArrowLeft size={16} />
119               Assessment
120             </Link>
121             <h1>Enterprise Report</h1>
122             <p>Executive summary, analytics, and downloadable CRA deliverables.</p>
123           </div>
124           <div className="report-actions">
125             <ReportStatusBadge status={safeReport.status} />
126             <button type="button" className="primary-action" onClick={handleGenerate} disabled={generating}>
127               <FilePlus2 size={16} />
128               {generating ? "Generating..." : "Generate Report"}
129             </button>
130           </div>
131         </div>
132
133         {error && <div className="error-banner">{error}</div>}
134         {generating && <LoadingSpinner label="Generating enterprise report..." />}
135
136         {!error && !safeReport.summary && (
137           <div className="warning-banner">
138             Report data is empty. Generate the report after assessment completion.
139           </div>
140         )}
141
142         <ReportSummaryCards summary={summary} />
143
144         <section className="panel">
145           <div className="panel-header">
146             <div>
147               <h2>Executive Summary Preview</h2>
148               <p>{summary.deployment_recommendation ?? "Generate a report to preview deployment guidance."}</p>
149             </div>
150           </div>
```

### Promise.all Implementation

File: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

```text
35-41: destructures assessment, findings, evidence, recommendations, report
42: getAssessment(assessmentId)
43-46: getAssessmentFindings(assessmentId, { limit: 100 }) with local catch fallback []
47-50: getAssessmentEvidence(assessmentId) with local catch fallback { parameters: [] }
51-54: getAssessmentRecommendations(assessmentId) with local catch fallback []
55: getAssessmentReport(assessmentId)
64-67: shared catch for getAssessment and getAssessmentReport failures
```

High-risk detail: `getAssessment()` and `getAssessmentReport()` do **not** have per-call fallback. Either one rejecting causes the whole page load to enter the shared error branch.

### Loading State

File: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

```text
26: loading initial true
30-32: loadReport sets loading true and clears error
68-69: finally sets loading false
92-94: while loading, only <LoadingSpinner label="Loading report..." /> renders
```

Component:

```text
CRA-frontend/src/components/LoadingSpinner.jsx
1-7: renders .spinner-wrap with spinner and label
```

### Error State

File: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

```text
28: error initial null
64-67: error set to err.response?.data?.detail || err.message
133: {error && <div className="error-banner">{error}</div>}
```

Important mismatch: backend error envelope is `{ error: { code, message, details }, request_id }`, not `{ detail }`. Therefore backend errors display as generic Axios messages such as `Request failed with status code 403`.

### Render State

File: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

```text
96: safeReport = report ?? {}
97: summary = safeReport.summary ?? {}
98: analytics = safeReport.analytics ?? {}
103-168: page should render even with empty report
136-140: empty report warning when no summary and no error
142: ReportSummaryCards receives safe empty summary
165: ReportCharts receives safe empty analytics
166: ReportDownloadPanel receives safe report
```

Render safety checks:

```text
CRA-frontend/src/components/report/ReportSummaryCards.jsx
1-23: uses safeSummary fallback; empty summary does not throw.

CRA-frontend/src/components/report/ReportCharts.jsx
24-30: converts missing analytics arrays to [].

CRA-frontend/src/components/report/ReportDownloadPanel.jsx
22-26: converts missing artifacts to []; disables downloads.

CRA-frontend/src/components/report/ReportPageErrorBoundary.jsx
13-17: logs REPORT_PAGE_RUNTIME_EXCEPTION and props if render throws.
21-27: renders error banner instead of blank page.
```

## 2. Frontend API Implementations

File: `CRA-frontend/src/api/assessmentApi.js`

```jsx
15 export async function getAssessment(assessmentId) {
16   const response = await api.get(`/assessments/${assessmentId}`);
17   return normalizeAssessment(unwrapApiData(response));
18 }

62 export async function generateAssessmentReport(assessmentId) {
63   const response = await api.post(`/assessments/${assessmentId}/generate-report`);
64   return unwrapApiData(response);
65 }

67 export async function getAssessmentReport(assessmentId) {
68   const response = await api.get(`/assessments/${assessmentId}/report`);
69   return unwrapApiData(response);
70 }
```

Axios behavior:

```text
CRA-frontend/src/api/axiosClient.js
4-6: baseURL defaults to http://127.0.0.1:8000/api/v1
8-12: request timeout is 30000 ms
20-24: Authorization Bearer token is attached to non-auth endpoints
44-47: 401 clears tokenStorage
49-53: dev console logs status and response payload
55: rejected promise propagates into AssessmentReportPage Promise.all catch
```

Response unwrap:

```text
CRA-frontend/src/utils/assessmentFormatters.js
3-5: unwrapApiData returns response.data.data, then response.data, then response
```

## 3. Backend Route Trace

Endpoint: `GET /api/v1/assessments/{assessment_id}/report`

Router file: `CRA-Tool/app/api/v1/assessments.py`

```python
252 @router.get(
253     "/assessments/{assessment_id}/report",
254     response_model=SuccessResponse[ReportBundleResponse],
255 )
256 async def get_assessment_report(
257     assessment_id: UUID,
258     request: Request,
259     db: AsyncSession = Depends(get_db),
260     current_user: User = Depends(get_current_active_user),
261 ) -> SuccessResponse[ReportBundleResponse]:
262     payload = await cra_report_service.get_report_bundle(
263         db,
264         current_user=current_user,
265         assessment_id=assessment_id,
266     )
267     return success_response(
268         message="Assessment report retrieved",
269         data=ReportBundleResponse.model_validate(payload),
270         request_id=request.state.request_id,
271     )
```

Service file: `CRA-Tool/app/services/reporting/cra_report_service.py`

```python
85 async def get_report_bundle(
91     report_data = await build_report_data(db, current_user=current_user, assessment_id=assessment_id)
92     result = await db.execute(
93         select(AssessmentReport)
94         .where(AssessmentReport.assessment_id == assessment_id)
95         .order_by(AssessmentReport.generated_at.desc())
96     )
97     artifacts = list(result.scalars().all())
98     return {
99         "assessment_id": assessment_id,
100         "status": "generated" if artifacts else "not_generated",
101         "download_ready": bool(artifacts),
102         "artifacts": [_artifact_payload(item) for item in artifacts],
103         "summary": report_data["summary"],
104         "analytics": report_data["analytics"],
105     }
```

Report data builder:

```python
156 async def build_report_data(
162     assessment = await get_assessment(db, current_user=current_user, assessment_id=assessment_id)
163     findings = await _load_findings(db, assessment.id)
164     recommendations = await _load_recommendations(db, assessment.id, assessment.tenant_id)
165     artifacts = await _load_artifacts(db, assessment.id, assessment.tenant_id)
166     analytics_raw = aggregate_findings(findings)
167     summary = build_summary(assessment=assessment, findings=findings, recommendations=recommendations)
168     narrative = build_narrative(summary=summary, analytics=analytics_raw)
169     parameter_rows = _build_parameter_rows(findings, recommendations, artifacts)
176     analytics = _build_report_analytics(summary=summary, parameter_rows=parameter_rows, assessment=assessment)
178     report_model = _build_report_model(...)
186     return { assessment, summary, analytics, narrative, sections, report_model, metadata }
```

Database queries:

```text
CRA-Tool/app/services/assessment_service.py
143: select(Assessment).where(Assessment.id == assessment_id)

CRA-Tool/app/services/reporting/cra_report_service.py
209-213: select(AssessmentFinding).options(selectinload(parameter)).where(assessment_id)
222-226: select(AssessmentRecommendation).where(assessment_id, tenant_id)
236-240: select(AssessmentArtifact).where(assessment_id, tenant_id)
92-96: select(AssessmentReport).where(assessment_id).order_by(generated_at desc)
```

Response model:

```text
CRA-Tool/app/schemas/report.py
28-34: ReportBundleResponse
29: assessment_id: UUID
30: status: str
31: download_ready: bool
32: artifacts: list[ReportArtifactResponse]
33: summary: dict
34: analytics: dict
```

Tables touched:

```text
assessments
assessment_findings
assessment_recommendations
assessment_artifacts
assessment_reports
assessment_parameters via AssessmentFinding.parameter selectinload
users via auth dependency
refresh_tokens or token/session tables indirectly via token revocation check
```

## 4. HTTP Return Paths

### 200

File: `CRA-Tool/app/api/v1/assessments.py`  
Function: `get_assessment_report`  
Lines: 252-271

Trigger:

```text
Valid Bearer token
Current user is active
Assessment exists
current_user.microsoft_tid == assessment.tenant_id
build_report_data completes
ReportBundleResponse validation succeeds
```

Frontend impact:

```text
Promise.all resolves.
setReport(reportData ?? {}) runs.
Page renders Enterprise Report.
If no assessment_reports rows exist, status is "not_generated" and download buttons are disabled.
```

### 401

File: `CRA-Tool/app/core/auth.py`  
Function: `get_token_payload`, `get_current_user`  
Lines: 39-49, 58-69

Triggers:

```text
Missing Bearer token
Invalid or expired CRA access token
Revoked token
Invalid token payload
Invalid user ID format
User not found
```

Backend handler:

```text
CRA-Tool/app/core/exceptions.py
86-94: HTTPException handler returns { error: { code: "HTTP_ERROR", message } }
```

Frontend impact:

```text
CRA-frontend/src/api/axiosClient.js
44-47: clears tokenStorage on 401

CRA-frontend/src/pages/AssessmentReportPage.jsx
64-67: shared catch sets error to err.response?.data?.detail || err.message
Because backend has error.message not detail, visible message becomes generic Axios text.
```

### 403

Files:

```text
CRA-Tool/app/core/auth.py
74-81: inactive user raises 403

CRA-Tool/app/services/assessment_service.py
55-57: _assert_user_tenant raises TenantAccessException
137-148: get_assessment calls _assert_user_tenant
```

Triggers:

```text
Inactive user account
Current user's microsoft_tid does not match assessment.tenant_id
```

Live reproduced trigger:

```text
User 2a6b0085-31d3-4125-bbd0-161065ce0fd3 tenant 2522b752-1926-4ccb-89a4-c465b37367f8
Assessment 26d70226-be91-47aa-a7ca-861dabd2e018 tenant fe4eff9a-f69c-48c0-921d-8006a6d5beb2
Result: TenantAccessException Tenant is not available to the current user
```

Frontend impact:

```text
getAssessment or getAssessmentReport rejects.
Promise.all catch runs.
Page exits loading and renders an error banner, but text is generic because frontend ignores response.data.error.message.
```

### 404

File: `CRA-Tool/app/services/assessment_service.py`  
Function: `get_assessment`  
Lines: 143-146

Trigger:

```text
Assessment UUID is valid format but not present in assessments table.
```

Frontend impact:

```text
getAssessment and getAssessmentReport can both hit this.
Shared catch sets generic Axios 404 message.
```

### 422

Files:

```text
CRA-Tool/app/api/v1/assessments.py
257: assessment_id: UUID

CRA-Tool/app/core/exceptions.py
97-106: validation_exception_handler
```

Triggers:

```text
assessmentId route param is not parseable as UUID.
BusinessLogicException is not raised by this GET report endpoint, but other assessment endpoints use it.
```

Frontend impact:

```text
getAssessment or getAssessmentReport rejects.
Shared catch sets generic Axios 422 message.
```

### 500

File: `CRA-Tool/app/core/exceptions.py`  
Function: `unhandled_exception_handler`  
Lines: 122-129

Trigger class:

```text
Any unhandled exception inside build_report_data, get_report_bundle, response validation, or serializer payload construction.
```

Concrete possible sources:

```text
CRA-Tool/app/services/registry_service.py
38-42: missing registry JSON file raises RegistryValidationError
44-48: registry list file is not a list raises RegistryValidationError
50-54: scoring file is not object raises RegistryValidationError
60-61: duplicate registry parameter keys raises RegistryValidationError
80-85: missing required parameter fields raises RegistryValidationError
92-97: rules/collectors/recommendations reference unknown or missing parameters raises RegistryValidationError
99-100: scoring registry missing required maps raises RegistryValidationError
130-132: get_registry constructs AssessmentRegistry

CRA-Tool/app/services/reporting/cra_report_service.py
306: _build_parameter_rows calls get_registry()
321-322: assumes every parameter has parameter_key
492-514: _build_report_model indexes required analytics and summary keys
580-589: _artifact_payload assumes generated_at is non-null and has isoformat()

CRA-Tool/app/api/v1/assessments.py
269: ReportBundleResponse.model_validate(payload) can raise if payload shape is invalid
```

Frontend impact:

```text
Shared catch logs REPORT_API_ERROR.
Visible message is generic "Request failed with status code 500" because frontend does not read response.data.error.message.
```

Note: SQLAlchemy failures are handled as `503`, not one of the requested return paths.

## 5. Required Data Condition Verification

### Assessment incomplete

Result: Should not fail by itself.

Evidence:

```text
CRA-Tool/app/services/reporting/cra_report_service.py
162: get_assessment only checks existence and tenant access
167: build_summary handles assessment.overall_score with `assessment.overall_score or 0`
```

Live DB:

```text
Latest assessment status: incomplete
progress_pct: 100
overall_score: null
Report service as WealthScape user returned status not_generated successfully.
```

### No findings

Result: Should not fail by itself.

Evidence:

```text
CRA-Tool/app/services/reporting/cra_risk_engine.py
26-40: aggregate_findings([]) returns zeroed severity/status maps
CRA-Tool/app/services/reporting/cra_summary_service.py
8-26: build_summary uses len(findings) and zeroed analytics
CRA-Tool/app/services/reporting/cra_report_service.py
301-363: _build_parameter_rows still emits registry parameters as not_collected
```

### No recommendations

Result: Should not fail by itself.

Evidence:

```text
CRA-Tool/app/services/reporting/cra_report_service.py
307: rec_by_key can be empty
324-350: missing DB recommendation falls back to registry recommendation
366-375: empty registry recommendation gets fallback text
```

Live DB:

```text
Latest WealthScape assessments have 0 assessment_recommendations rows.
Report service still returned successfully.
```

### No artifacts

Result: Should not fail by itself.

Evidence:

```text
CRA-Tool/app/services/reporting/cra_report_service.py
316-318: artifact_by_key can be empty
327: latest_artifact is None
378-380: _artifact_evidence(None) returns a missing evidence object
```

### No assessment_reports row

Result: Should not fail by itself.

Evidence:

```text
CRA-Tool/app/services/reporting/cra_report_service.py
97: artifacts = []
100: status = "not_generated"
101: download_ready = False
102: artifacts = []
```

Live DB:

```text
Latest assessment 26d70226-be91-47aa-a7ca-861dabd2e018 has 0 assessment_reports rows.
Report service returned status not_generated successfully.
```

## 6. build_report_data / get_report_bundle Exceptions

Search results:

```text
CRA-Tool/app/services/reporting/cra_report_service.py
85: async def get_report_bundle
91: report_data = await build_report_data(...)
156: async def build_report_data
```

No explicit `raise` exists inside `get_report_bundle` or `build_report_data`. Exceptions propagate from called functions.

Exact propagated exceptions:

| File | Function | Line Number | Exception | Trigger |
|---|---|---:|---|---|
| `CRA-Tool/app/services/assessment_service.py` | `_assert_user_tenant` | 55-57 | `TenantAccessException` | Current user's `microsoft_tid` does not equal assessment tenant |
| `CRA-Tool/app/services/assessment_service.py` | `get_assessment` | 143-146 | `NotFoundException` | Assessment id does not exist |
| `CRA-Tool/app/services/registry_service.py` | `_load_json` | 38-42 | `RegistryValidationError` | Missing registry JSON |
| `CRA-Tool/app/services/registry_service.py` | `_load_list` | 44-48 | `RegistryValidationError` | Registry JSON expected as list is not a list |
| `CRA-Tool/app/services/registry_service.py` | `_load_dict` | 50-54 | `RegistryValidationError` | Scoring registry is not an object |
| `CRA-Tool/app/services/registry_service.py` | `_ensure_unique` | 56-62 | `RegistryValidationError` | Duplicate parameter keys |
| `CRA-Tool/app/services/registry_service.py` | `validate` | 64-100 | `RegistryValidationError` | Missing fields, unknown references, absent registry records, or missing scoring maps |
| `CRA-Tool/app/services/reporting/cra_report_service.py` | `_build_parameter_rows` | 321-322 | `KeyError` | Registry parameter lacks `parameter_key` despite validation |
| `CRA-Tool/app/services/reporting/cra_report_service.py` | `_build_report_model` | 492-514 | `KeyError` | Required `analytics` or `summary` keys missing |
| `CRA-Tool/app/services/reporting/cra_report_service.py` | `_artifact_payload` | 580-589 | `AttributeError` | Corrupt `assessment_reports.generated_at` is null/non-datetime |
| `CRA-Tool/app/api/v1/assessments.py` | `get_assessment_report` | 269 | Pydantic validation exception | Payload fails `ReportBundleResponse` schema |

Related but not part of GET report endpoint:

```text
CRA-Tool/app/services/reporting/cra_report_service.py
126-127: get_report_artifact raises FileNotFoundError("Report artifact has not been generated")

This affects report download, not GET /report. The download route catches it and returns 404.
```

## 7. Failure Path Matrix

| Failure Path | File | Function | Line Number | Trigger | Frontend Impact | Fix |
|---|---|---|---:|---|---|---|
| 401 missing/invalid token | `CRA-Tool/app/core/auth.py` | `get_token_payload` | 39-45 | Missing/expired/invalid CRA JWT | Axios clears token; Promise.all rejects; generic error banner or auth redirect | Read backend envelope in frontend: `response.data.error.message`; ensure token refresh/login state is valid |
| 401 revoked token | `CRA-Tool/app/core/auth.py` | `get_token_payload` | 47-49 | Token jti revoked | Same as above | Force fresh login; verify token revocation/session state |
| 401 user not found | `CRA-Tool/app/core/auth.py` | `get_current_user` | 67-69 | JWT sub not found in DB | Same as above | Align login-created user with DB state |
| 403 inactive user | `CRA-Tool/app/core/auth.py` | `get_current_active_user` | 77-81 | `users.is_active` false | Promise.all rejects; generic 403 text | Activate user or block before route with clear UI |
| 403 tenant mismatch | `CRA-Tool/app/services/assessment_service.py` | `_assert_user_tenant` | 55-57 | `current_user.microsoft_tid != assessment.tenant_id` | `getAssessment` or `getAssessmentReport` rejects; report page shows generic error | Ensure assessment belongs to logged-in tenant; prevent links to cross-tenant assessments; show backend error message |
| 404 missing assessment | `CRA-Tool/app/services/assessment_service.py` | `get_assessment` | 143-146 | UUID exists syntactically but no row | Promise.all rejects; generic 404 text | Route only to existing assessments; show specific not-found UI |
| 422 invalid assessment id | `CRA-Tool/app/api/v1/assessments.py` | route param validation | 257 | `assessmentId` is not UUID | Promise.all rejects; generic 422 text | Validate URL param before API calls or render not-found |
| 500 registry missing/invalid | `CRA-Tool/app/services/registry_service.py` | `get_registry` / `validate` | 38-100, 130-132 | Missing/invalid registry JSON | Promise.all rejects; generic 500 text | Fix registry files or map `RegistryValidationError` to clear API error |
| 500 malformed registry parameter | `CRA-Tool/app/services/reporting/cra_report_service.py` | `_build_parameter_rows` | 321-322 | Missing `parameter_key` | Promise.all rejects; generic 500 text | Registry validation should catch and report exact parameter |
| 500 malformed analytics | `CRA-Tool/app/services/reporting/cra_report_service.py` | `_build_report_model` | 492-514 | Missing expected analytics/summary keys | Promise.all rejects; generic 500 text | Keep analytics contract stable or add defaults |
| 500 corrupt report artifact row | `CRA-Tool/app/services/reporting/cra_report_service.py` | `_artifact_payload` | 580-589 | Null/non-datetime `generated_at` | Promise.all rejects; generic 500 text | Validate DB rows or guard serializer |
| 503 database failure | `CRA-Tool/app/core/exceptions.py` | `database_exception_handler` | 109-119 | SQLAlchemy failure | Promise.all rejects; generic 503 text | Inspect DB connectivity/migration state |

## 8. Local Runtime Data Snapshot

Database file:

```text
CRA-Tool/cra.db
Last modified: 2026-06-01 19:20:59
```

Latest assessments:

```text
26d70226-be91-47aa-a7ca-861dabd2e018
tenant: fe4eff9a-f69c-48c0-921d-8006a6d5beb2
status: incomplete
findings: 4
recommendations: 0
artifacts: 7
assessment_reports: 0

f2d61ee7-9ee2-46cf-a261-1780750bff7d
tenant: fe4eff9a-f69c-48c0-921d-8006a6d5beb2
status: incomplete
findings: 4
recommendations: 0
artifacts: 7
assessment_reports: 2
```

Users:

```text
deep@wealthscape.in
id: 92207583-c2f4-450e-b564-07d97a64f94e
microsoft_tid: fe4eff9a-f69c-48c0-921d-8006a6d5beb2
active: true

ayush.mishra@techplustalent.com
id: 2a6b0085-31d3-4125-bbd0-161065ce0fd3
microsoft_tid: 2522b752-1926-4ccb-89a4-c465b37367f8
active: true
```

Live service result:

```text
As deep@wealthscape.in:
get_report_bundle(latest WealthScape assessment) -> success, status not_generated.

As first DB user:
get_report_bundle(latest WealthScape assessment) -> TenantAccessException.
```

## 9. Root Cause Conclusion

The report endpoint can successfully build a report bundle for the latest WealthScape assessment even when:

```text
assessment status is incomplete
overall_score is null
recommendations count is 0
assessment_reports count is 0
```

So the blank screen is not caused by missing generated report artifacts.

The exact backend failure most consistent with a blank/error state after login is a request authorization or tenant ownership failure:

```text
CRA-Tool/app/services/assessment_service.py
55-57: _assert_user_tenant raises TenantAccessException
137-148: get_assessment uses that check
```

The exact frontend weakness that hides the useful root cause is:

```text
CRA-frontend/src/pages/AssessmentReportPage.jsx
66: setError(err.response?.data?.detail || err.message)
86: setError(err.response?.data?.detail || err.message)
```

Backend errors are shaped as:

```json
{
  "error": {
    "code": "TENANT_ACCESS_DENIED",
    "message": "Tenant is not available to the current user"
  },
  "request_id": "..."
}
```

The frontend reads `detail`, so it loses the real backend message and displays generic Axios text.

## 10. Fix List For Later

No code was modified during this investigation. Recommended fixes when implementation is allowed:

1. Update report page error extraction to read `err.response?.data?.error?.message` before `detail` or `err.message`.
2. Add per-call catch/fallback for `getAssessmentReport()` if the design should render report shell even when bundle fetch fails.
3. Prevent cross-tenant assessment links by filtering/listing only current user's tenant assessments.
4. Add explicit UI for `status: "not_generated"` and `download_ready: false`.
5. Add backend logging around `get_report_bundle` with assessment id, current user id, and tenant id.
6. Optionally map `RegistryValidationError` to a clear 500/422 response with details.
