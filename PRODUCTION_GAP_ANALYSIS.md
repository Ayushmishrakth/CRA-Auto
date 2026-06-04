# CRA Platform Production Gap Analysis

## Currently Working

- Microsoft login through MSAL popup.
- Backend Microsoft ID token validation.
- CRA JWT issuance and protected API access.
- Tenant row creation on first login.
- CRA Access deployment flow.
- App registration creation and repair.
- Graph application permission configuration.
- Admin consent validation.
- Assessment creation.
- Runtime job lifecycle and event emission.
- Graph collector execution for 7 Entra/user parameters.
- Artifact persistence for selected collectors.
- Finding creation for selected collectors.
- Score calculation when selected collectors all complete.
- Recommendation generation when scoring path completes.
- Report generation service can build PDF/DOCX artifacts from available runtime data.
- Evidence dashboard can read collected artifacts/findings.

## Partially Working

- Collector framework:
  - registry contains 76 parameters
  - runtime selects only 7
  - PowerShell runtime exists but is effectively bypassed for the non-selected parameters

- Report page:
  - backend report service exists
  - frontend route exists
  - blank-screen behavior indicates missing timeout/error surfacing or backend report failure

- Scoring:
  - works only after selected collectors complete
  - does not score partial evidence if any selected collector fails

- Recommendations:
  - generated only from findings
  - most registry parameters receive report placeholder recommendations, not runtime-generated recommendation rows

- Database:
  - runtime tables work
  - production `cra_*` parameter/result tables exist but are not the primary runtime path

## Broken or High Risk

1. Report route can appear blank.
   - Highest-risk frontend call: `getAssessmentReport` in `AssessmentReportPage.jsx`.
   - Error extraction does not match backend error envelope.

2. Assessment completeness is fragile.
   - Any selected collector failure marks the assessment `incomplete`.
   - Incomplete assessments skip scoring/recommendations/report generation.

3. Most collectors do not run.
   - Only 7 / 76 parameters are runtime-selected.

4. PowerShell collectors are not production-ready in current path.
   - Many registry collectors point to PowerShell names, but runtime does not select them.
   - PowerShell execution depends on local scripts, local output files, and local modules.

5. Report storage is local.
   - `storage/reports` is not suitable for horizontal scaling, containers, or cloud hosting without shared storage.

6. Mixed data models.
   - Runtime uses `assessment_findings` and `assessment_artifacts`.
   - Newer production-looking model uses `cra_assessment_results` and `cra_parameter_evidence`.
   - This creates duplicated concepts.

## Missing Collectors

Missing runtime collectors include most of:

- Teams controls
- SharePoint controls
- OneDrive controls
- Exchange controls
- Purview controls
- Security/governance controls
- Licensing controls
- Conditional Access controls
- MFA/authentication method controls
- Device compliance controls

See `COLLECTOR_STATUS.md` for all 76 parameters.

## Missing Graph Permissions

From current code, all required app permissions are now configured:

- `Application.Read.All`
- `Directory.Read.All`
- `Group.Read.All`
- `User.Read.All`
- `Organization.Read.All`
- `Reports.Read.All`
- `AuditLog.Read.All`
- `Policy.Read.All`
- `RoleManagement.Read.Directory`
- `SecurityEvents.Read.All`
- `IdentityRiskyUser.Read.All`
- `DeviceManagementManagedDevices.Read.All`
- `UserAuthenticationMethod.Read.All`
- `Team.ReadBasic.All`
- `Sites.Read.All`
- `Files.Read.All`

Future collectors may need additional permissions, likely:

- Teams policy/configuration permissions depending on selected Graph API.
- SharePoint admin APIs may require SharePoint-specific admin permissions or PowerShell delegated context.
- Purview/DLP APIs may require compliance/security roles beyond Graph application permissions.
- Exchange Online settings may require Exchange PowerShell/application RBAC.

## Missing Report Sections or Weak Report Content

Report model includes many sections, but content quality is limited by missing collectors.

Weak sections:

- M365 Service Scores: many services have no collected rows.
- Licensing Analysis: no current selected license collector.
- User Activity Analysis: mostly absent beyond `/users` profile-derived findings.
- Detailed Findings: most rows become `NOT COLLECTED`.
- Recommendations: many are registry fallback recommendations, not evidence-derived rows.

## Frontend Issues

- Report page has no request timeout or per-call recovery for `getAssessmentReport`.
- Backend errors are inconsistently extracted across pages.
- Report error boundary does not catch async load errors.
- Some pages depend on `user.microsoft_tid` rather than selected tenant, limiting future multi-tenant UX.
- Recharts empty-state UX is weak; empty charts look like empty dark panels.

## Backend Issues

- Runtime collector selection is hard-coded.
- Collector failure policy is fail-closed for scoring/report generation.
- PowerShell and Graph collector paths are mixed in a single runtime service.
- Local Celery/Redis behavior needs explicit deployment documentation.
- Report generation occurs inside assessment runtime; slow PDF/DOCX generation can extend job duration.
- Report generation writes to local filesystem.

## Database Issues

- SQLite is acceptable for local development only.
- PostgreSQL migration should review UUID storage, JSON fields, datetime handling, indexes, and constraints.
- No durable object storage abstraction for report files.
- Runtime tables and `cra_*` tables overlap conceptually.
- Assessment rerun deletes artifacts/findings for that assessment before recollection.

## Biggest Production Blockers

1. Collector coverage: only 7 / 76 parameters are automated in current runtime.
2. Runtime reliability: any selected collector failure blocks scoring/reporting.
3. Report blank-screen/error handling.
4. Local filesystem report storage.
5. SQLite and local PowerShell assumptions.
6. Split data model between runtime findings and CRA result tables.
7. Insufficient observability for report failures in frontend.
