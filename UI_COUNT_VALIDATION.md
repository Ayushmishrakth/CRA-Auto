# UI Count Validation

## Dashboard

Source: `CRA-frontend/src/pages/DashboardPage.jsx`

The dashboard uses assessment summary fields from `fetchTenantAssessments`, including `total_findings`, `critical_findings`, and `high_findings`. It displays assessment result counts, not parameter inventory counts.

## Assessment Detail

Source: `CRA-frontend/src/pages/AssessmentDetailPage.jsx`

The detail page calls `getAssessmentEvidence(assessmentId)` and uses `evidencePayload.parameters` as collector evidence rows. It displays collected evidence/result rows, not the full approved parameter inventory.

## Evidence Page

Source: `CRA-frontend/src/pages/AssessmentEvidencePage.jsx`

The evidence page calls `getAssessmentEvidence(assessmentId)`. Its `coverage.total_parameters` and `payload.parameters` come from backend evidence coverage. Before cleanup this reflected the 76-row registry; after cleanup it reflects the approved 65-row registry.

## Report Page

Source: `CRA-frontend/src/pages/AssessmentReportPage.jsx`

The report page shows:

- findings from `getAssessmentFindings`
- recommendations from `getAssessmentRecommendations`
- evidence rows from `getAssessmentEvidence`
- report artifacts from `getAssessmentReport` / `generateAssessmentReport`

It does not directly display parameter inventory count except through evidence rows.

## Parameters Page

Source: `CRA-frontend/src/pages/ParametersPage.jsx`

The Parameters page calls `/registry/parameters` through `registryApi.js`. Before cleanup it displayed 76 registry rows. After cleanup it displays 65 approved parameters.

## Conclusion

The UI was not consistently showing the same concept everywhere. Dashboard shows assessment result counts; Parameters shows registry inventory; Evidence/Report show evidence/result rows. The main parameter-count problem was the 76-row registry, now corrected to 65 approved rows.
