# CRA Platform System Architecture

Discovery date: 2026-06-01

## High-Level Shape

CRA Platform is a React + FastAPI application for Microsoft 365 Copilot readiness assessment.

The current architecture is:

- Frontend: `CRA-frontend`, React, Vite, MSAL React, Axios, Recharts.
- Backend: `CRA-Tool`, FastAPI, SQLAlchemy async ORM, Celery runtime hook, Microsoft Graph integration.
- Database: SQLite via SQLAlchemy today; schema is migration-managed and mostly portable to PostgreSQL.
- Identity: Microsoft Entra ID for login, internal CRA JWT for API access, Microsoft Graph delegated token for tenant deployment, Graph application permissions for runtime collectors.

## Frontend Structure

Entry files:

- `CRA-frontend/src/main.jsx`: React bootstrap.
- `CRA-frontend/src/App.jsx`: provider composition.
- `CRA-frontend/src/routes/AppRoutes.jsx`: route table.
- `CRA-frontend/src/layouts/MainLayout.jsx`: authenticated shell.

Routes:

| Route | Component | Purpose |
|---|---|---|
| `/login` | `LoginPage.jsx` | Microsoft popup login and CRA JWT bootstrap |
| `/dashboard` | `DashboardPage.jsx` | tenant status, assessment summary, start assessment |
| `/tenant` | `TenantConnectionPage.jsx` | deploy/repair CRA access, grant/validate consent |
| `/tenant/deployment-success` | `TenantConnectionPage.jsx` | post-consent validation redirect |
| `/assessments` | `AssessmentsPage.jsx` | assessment list and restart |
| `/assessments/:assessmentId` | `AssessmentDetailPage.jsx` | active assessment, findings, timeline, execution |
| `/assessments/:assessmentId/evidence` | `AssessmentEvidencePage.jsx` | evidence dashboard |
| `/assessments/:assessmentId/report` | `AssessmentReportPage.jsx` | enterprise report preview/download |
| `/parameters` | `ParametersPage.jsx` | registry/parameter browser |

API layer:

- `src/api/axiosClient.js`: base URL, CRA JWT bearer injection, 401 token clearing.
- `src/api/authApi.js`: auth endpoint wrapper.
- `src/api/tenantApi.js`: tenant/deployment endpoints.
- `src/api/assessmentApi.js`: assessment, evidence, report, download endpoints.
- `src/api/registryApi.js`: registry endpoints.

Auth layer:

- `src/auth/msalConfig.js`: MSAL client, login scopes, tenant deployment Graph scopes.
- `src/auth/msalAuth.js`: login popup, logout popup, Graph access token acquisition.
- `src/context/AuthContext.jsx`: session bootstrap, Microsoft ID token exchange, CRA JWT state.
- `src/utils/tokenStorage.js`: stores CRA access/refresh tokens.

Assessment state:

- `src/context/AssessmentContext.jsx`: assessment list, active assessment, findings, recommendations, scores, websocket status.
- `src/services/websocketService.js`: runtime event subscriptions.

Report UI:

- `src/pages/AssessmentReportPage.jsx`
- `src/components/report/ReportSummaryCards.jsx`
- `src/components/report/ReportCharts.jsx`
- `src/components/report/ReportDownloadPanel.jsx`
- `src/components/report/ReportPageErrorBoundary.jsx`
- `src/components/report/ReportStatusBadge.jsx`

## Backend Structure

FastAPI entry:

- `CRA-Tool/app/main.py`: app creation, middleware, exception handlers, API router, websocket router.
- `CRA-Tool/app/api/v1/router.py`: includes `health`, `auth`, `tenants`, `assessments`, `reports`, `registry`, `parameters`, `admin`.

Routers:

| Router | File | Responsibility |
|---|---|---|
| Auth | `app/routes/auth.py` via `app/api/v1/auth.py` | Microsoft login, refresh, logout, profile |
| Tenants | `app/api/v1/tenants.py` | tenant CRUD, deployment, consent validation, debug |
| Assessments | `app/api/v1/assessments.py` | start/list/detail/findings/evidence/events/job/score/report |
| Reports | `app/api/v1/reports.py` | additional report surface |
| Registry | `app/api/v1/registry.py` | registry metadata |
| Parameters | `app/api/v1/parameters.py` | CRA parameter metadata |
| Websocket | `app/api/v1/websocket.py` | assessment and tenant live events |

Core services:

| Service | File | Responsibility |
|---|---|---|
| Auth | `app/services/auth_service.py` | validate Microsoft ID token, upsert user, issue CRA JWT |
| Tenant deployment | `app/services/tenant_deployment_service.py` | app registration, service principal, secret, consent URL, validation |
| App registration | `app/services/graph_app_registration_service.py` | create/patch/read Entra app registration |
| Graph permissions | `app/services/graph_permission_service.py` | required Graph application/delegated permissions |
| Assessment orchestration | `app/services/assessment_service.py` | start/list/read assessment data |
| Runtime engine | `app/services/runtime_assessment_service.py` | collector execution, artifacts, findings, scoring, recommendations, report generation |
| Graph collectors | `app/services/graph_cra_collector_service.py` | implemented Graph collectors |
| PowerShell runtime | `app/services/powershell/powershell_runtime.py` | registry-driven PowerShell collector execution |
| Scoring | `app/services/runtime_scoring_service.py` | score calculation from findings |
| Recommendations | `app/services/runtime_recommendation_service.py` | recommendation creation from registry metadata |
| Reporting | `app/services/reporting/cra_report_service.py` | report data model, PDF/DOCX artifacts |

## Assessment Engine

Assessment start:

- API: `POST /api/v1/assessments/start`
- Route: `app/api/v1/assessments.py`
- Service: `app/services/assessment_service.py`
- Creates `assessments` and `assessment_jobs`
- Queues `app.tasks.assessment_tasks.run_assessment_task`, or local background execution when Celery eager mode is enabled.

Runtime:

- Main function: `run_assessment_job` in `app/services/runtime_assessment_service.py`
- Stages: `starting`, `collecting`, `evaluating`, `scoring`, `generating_recommendations`, `completed`
- Emits events through `app/services/event_bus.py`
- Persists:
  - raw collector artifacts in `assessment_artifacts`
  - normalized findings in `assessment_findings`
  - score fields on `assessments`
  - recommendations in `assessment_recommendations`
  - generated report files in `assessment_reports`

Current runtime selector:

- `FIRST_OPERATIONAL_GRAPH_PARAMETERS` in `runtime_assessment_service.py`
- This intentionally limits runtime collection to 7 Graph-backed parameters.
- All other 69 registry parameters are not currently executed.

## Microsoft Integration

Login:

- Frontend MSAL gets an ID token.
- Backend validates ID token against Entra JWKS in `app/core/microsoft.py`.
- Backend issues CRA JWT from `app/core/security.py`.

Graph deployment token:

- Frontend gets delegated Microsoft Graph access token using `tenantDeploymentRequest` in `src/auth/msalConfig.js`.
- Backend validates token audience, tenant, expiry, and delegated scopes in `tenant_deployment_service._assert_graph_token`.

App registration:

- `deploy_tenant_access` creates or repairs the Entra app registration.
- Required permissions come from `REQUIRED_APPLICATION_PERMISSIONS` in `app/services/graph_permission_service.py`.
- Consent URL is generated by `app/services/graph_consent_service.py`.

Runtime Graph token:

- Graph collectors use client credentials against the tenant app:
  - token endpoint: `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token`
  - scope: `https://graph.microsoft.com/.default`

Required application permissions currently configured:

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
