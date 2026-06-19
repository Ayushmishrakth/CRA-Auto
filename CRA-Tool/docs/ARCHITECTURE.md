# Architecture

## Overview

CRA Tool has three main parts:

- A React/Vite frontend in `CRA-frontend`.
- A FastAPI backend in `CRA-Tool/app`.
- A local database and runtime assessment engine that collect Microsoft 365 evidence through Microsoft Graph and PowerShell collectors.

The backend is the authority for users, tenants, assessments, findings, artifacts, reports, scoring, and generated report paths.

## High-Level Diagram

```text
Browser
  |
  | React + MSAL login
  v
CRA-frontend
  |
  | Axios API calls with CRA JWT
  v
FastAPI backend
  |-- Auth service validates Microsoft ID token and issues CRA JWTs
  |-- Tenant deployment service creates/updates app registration and permissions
  |-- Runtime assessment service runs Graph and PowerShell collectors
  |-- Scoring service writes assessment scores and findings
  |-- Report service builds DOCX and PDF reports
  |
  | SQLAlchemy
  v
SQLite database

FastAPI backend
  |
  | Microsoft Graph + PowerShell modules
  v
Microsoft 365 tenant
```

## Backend Entry Points

- FastAPI app: `CRA-Tool/app/main.py`
- API router: `CRA-Tool/app/api/v1/router.py`
- API prefix: `/api/v1`
- WebSocket router: `CRA-Tool/app/api/v1/websocket.py`
- Database session: `CRA-Tool/app/db/session.py`
- Models: `CRA-Tool/app/db/models/`
- Assessment runtime: `CRA-Tool/app/services/runtime_assessment_service.py`
- Scoring: `CRA-Tool/app/services/runtime_scoring_service.py`
- Report service: `CRA-Tool/app/services/reporting/cra_report_service.py`
- DOCX builder: `CRA-Tool/app/services/reporting/report_builder.py`

## Frontend Entry Points

- React entry: `CRA-frontend/src/main.jsx`
- App shell: `CRA-frontend/src/App.jsx`
- Routes: `CRA-frontend/src/routes/AppRoutes.jsx`
- MSAL config: `CRA-frontend/src/auth/msalConfig.js`
- API client: `CRA-frontend/src/api/`
- Auth context: `CRA-frontend/src/context/AuthContext.jsx`
- Assessment context: `CRA-frontend/src/context/AssessmentContext.jsx`

## Authentication Flow

1. The user signs in through Microsoft from the React frontend.
2. MSAL uses the authority from `VITE_MSAL_AUTHORITY`, defaulting to `https://login.microsoftonline.com/common`.
3. The frontend sends the Microsoft ID token to `POST /api/v1/auth/login`.
4. `AuthService` validates the token, extracts Microsoft user and tenant claims, upserts the local `users` row, and creates a connected tenant row if needed.
5. The backend returns a CRA access token and refresh token.
6. The frontend sends the CRA access token as a Bearer token for protected API calls.
7. Protected routes use `get_current_active_user`.

Frontend login scopes:

- `openid`
- `profile`
- `email`

Tenant deployment delegated scopes requested by the frontend:

- `https://graph.microsoft.com/User.Read`
- `https://graph.microsoft.com/Directory.Read.All`
- `https://graph.microsoft.com/Application.ReadWrite.All`
- `https://graph.microsoft.com/AppRoleAssignment.ReadWrite.All`

Runtime app permissions required by the backend permission service include Graph application permissions such as `Application.Read.All`, `Directory.Read.All`, `Group.Read.All`, `User.Read.All`, `Organization.Read.All`, `Reports.Read.All`, `AuditLog.Read.All`, `Policy.Read.All`, `RoleManagement.Read.Directory`, `SecurityEvents.Read.All`, `IdentityRiskyUser.Read.All`, `DeviceManagementManagedDevices.Read.All`, `UserAuthenticationMethod.Read.All`, `Team.ReadBasic.All`, `Sites.Read.All`, `Sites.FullControl.All`, `Files.Read.All`, `SharePointTenantSettings.Read.All`, `InformationProtectionPolicy.Read.All`, and `SecurityActions.Read.All`. The service also handles Exchange `Exchange.ManageAsApp` and Teams application access.

## API Routes

All routes below are registered by `app/main.py` and `app/api/v1/router.py`.

### Root And Health

| Method | Route | Auth |
|---|---|---|
| GET | `/` | No |
| GET | `/health` | No |
| GET | `/health/db` | No |
| GET | `/health/auth` | No |
| GET | `/health/system` | No |
| GET | `/api/v1/health` | No |
| GET | `/api/v1/health/db` | No |
| GET | `/api/v1/health/auth` | No |
| GET | `/api/v1/health/system` | No |

### Auth

| Method | Route | Auth |
|---|---|---|
| POST | `/api/v1/auth/login` | No |
| POST | `/api/v1/auth/refresh` | No |
| POST | `/api/v1/auth/logout` | Bearer token |
| GET | `/api/v1/auth/me` | Yes |

### Dashboard

| Method | Route | Auth |
|---|---|---|
| GET | `/api/v1/dashboard/stats` | Yes |

### Tenants

| Method | Route | Auth |
|---|---|---|
| POST | `/api/v1/tenants/connect` | Yes |
| GET | `/api/v1/tenants` | Yes |
| GET | `/api/v1/tenants/deployment/debug` | Yes |
| GET | `/api/v1/tenants/deployment/runtime-debug` | Yes |
| GET | `/api/v1/tenants/deployment/validate` | Yes, with `X-Graph-Access-Token` |
| GET | `/api/v1/tenants/{tenant_id}` | Yes |
| DELETE | `/api/v1/tenants/{tenant_id}` | Yes |
| GET | `/api/v1/tenants/{tenant_id}/permissions` | Yes |
| POST | `/api/v1/tenants/deployment/start` | Yes |
| POST | `/api/v1/tenants/deployment/validate-consent` | Yes |
| POST | `/api/v1/tenants/deployment/repair` | Yes |
| GET | `/api/v1/tenants/{tenant_id}/assessments` | Yes |

### Assessments

| Method | Route | Auth |
|---|---|---|
| POST | `/api/v1/assessments/start` | Yes |
| GET | `/api/v1/assessments` | Yes |
| GET | `/api/v1/assessment/debug/latest` | Yes |
| GET | `/api/v1/assessments/{assessment_id}` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/findings` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/evidence` | Yes |
| GET | `/api/v1/assessment-failures/{assessment_id}` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/events` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/job` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/recommendations` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/score` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/readiness` | Yes |
| POST | `/api/v1/assessments/{assessment_id}/generate-report` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/report` | Yes |
| GET | `/api/v1/assessment/report-debug/{assessment_id}` | Yes |
| GET | `/api/v1/report-debug/{assessment_id}` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/report/download` | Yes |
| DELETE | `/api/v1/assessments/{assessment_id}` | Yes |
| GET | `/api/v1/assessments/{assessment_id}/results` | Yes |

### Reports

| Method | Route | Auth |
|---|---|---|
| GET | `/api/v1/reports/assessments/{assessment_id}` | Yes |
| POST | `/api/v1/reports/assessments/{assessment_id}/generate` | Yes |
| POST | `/api/v1/reports/assessments/{assessment_id}/customize` | Yes |

### Registry, Parameters, And Admin

| Method | Route | Auth |
|---|---|---|
| GET | `/api/v1/registry/parameters` | Yes |
| POST | `/api/v1/parameters/import` | Yes |
| GET | `/api/v1/parameters/versions` | Yes |
| GET | `/api/v1/admin/parameters` | Admin |
| PUT | `/api/v1/admin/parameters/{id}/rule` | Admin |
| POST | `/api/v1/admin/reset-tenant/{tenant_id}` | Admin |

## Database Schema

The schema below is from the SQLAlchemy models in `CRA-Tool/app/db/models/`.

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | `CHAR(32)` | Primary key |
| `microsoft_oid` | `VARCHAR(64)` | Microsoft object ID |
| `microsoft_tid` | `VARCHAR(64)` | Microsoft tenant ID |
| `email` | `VARCHAR(255)` | User email |
| `display_name` | `VARCHAR(255)` | Display name |
| `role` | `VARCHAR(50)` | User role |
| `is_active` | `BOOLEAN` | Active flag |
| `last_login` | `DATETIME` | Last login |
| `created_at` | `DATETIME` | Created timestamp |
| `updated_at` | `DATETIME` | Updated timestamp |

### `connected_tenants`

| Column | Type | Notes |
|---|---|---|
| `id` | `CHAR(32)` | Primary key |
| `tenant_id` | `VARCHAR(64)` | Microsoft tenant ID |
| `tenant_name` | `VARCHAR(255)` | Tenant display name |
| `application_object_id` | `VARCHAR(64)` | App registration object ID |
| `application_client_id` | `VARCHAR(64)` | App/client ID |
| `service_principal_id` | `VARCHAR(64)` | Service principal ID |
| `encrypted_client_secret` | `VARCHAR(1000)` | Encrypted secret |
| `secret_id` | `VARCHAR(128)` | Secret key ID |
| `secret_expiration` | `DATETIME` | Secret expiry |
| `secret_version` | `VARCHAR(64)` | Secret version |
| `deployment_status` | `VARCHAR(50)` | Deployment state |
| `deployment_step` | `VARCHAR(80)` | Current deployment step |
| `deployment_timestamp` | `DATETIME` | Deployment timestamp |
| `redirect_uri` | `VARCHAR(1000)` | Redirect URI |
| `deployment_diagnostics` | `JSON` | Deployment diagnostics |
| `admin_consent_url` | `VARCHAR(1000)` | Admin consent URL |
| `deployment_error` | `VARCHAR(2000)` | Deployment error |
| `consent_status` | `VARCHAR(50)` | Consent state |
| `consent_granted_by` | `VARCHAR(255)` | Granting user |
| `consent_granted_at` | `DATETIME` | Consent timestamp |
| `granted_permissions` | `JSON` | Granted permissions |
| `status` | `VARCHAR(50)` | Tenant status |
| `last_assessment_at` | `DATETIME` | Last assessment timestamp |
| `created_at` | `DATETIME` | Created timestamp |
| `updated_at` | `DATETIME` | Updated timestamp |

### `assessments`

| Column | Type | Notes |
|---|---|---|
| `id` | `CHAR(32)` | Primary key |
| `tenant_id` | `VARCHAR(64)` | Microsoft tenant ID |
| `triggered_by_user_id` | `CHAR(32)` | Foreign key to `users.id` |
| `status` | `VARCHAR(50)` | Assessment state |
| `progress_pct` | `FLOAT` | Runtime progress |
| `overall_score` | `FLOAT` | Overall score |
| `identity_score` | `FLOAT` | Identity score |
| `security_score` | `FLOAT` | Security score |
| `compliance_score` | `FLOAT` | Compliance score |
| `collaboration_score` | `FLOAT` | Collaboration score |
| `licensing_score` | `FLOAT` | Licensing score |
| `copilot_eligible_user_count` | `INTEGER` | Eligible user count |
| `total_findings` | `INTEGER` | Total findings |
| `critical_findings` | `INTEGER` | Critical findings |
| `high_findings` | `INTEGER` | High findings |
| `report_path` | `VARCHAR(500)` | Generated report path |
| `deleted_at` | `DATETIME` | Soft delete timestamp |
| `created_at` | `DATETIME` | Created timestamp |
| `updated_at` | `DATETIME` | Updated timestamp |

### `assessment_parameters`

| Column | Type | Notes |
|---|---|---|
| `id` | `CHAR(32)` | Primary key |
| `parameter_key` | `VARCHAR(100)` | Registry parameter key |
| `parameter_name` | `VARCHAR(255)` | Display name |
| `category` | `VARCHAR(100)` | Service/category |
| `collection_method` | `VARCHAR(50)` | Graph or PowerShell collection method |
| `collector_module` | `VARCHAR(100)` | Collector module |
| `graph_endpoint` | `VARCHAR(500)` | Graph endpoint when applicable |
| `copilot_relevance` | `VARCHAR(500)` | Copilot relevance text |
| `is_active` | `BOOLEAN` | Active flag |
| `excel_row_reference` | `VARCHAR(50)` | Source/reference row |
| `created_at` | `DATETIME` | Created timestamp |
| `updated_at` | `DATETIME` | Updated timestamp |

### `assessment_findings`

| Column | Type | Notes |
|---|---|---|
| `id` | `CHAR(32)` | Primary key |
| `assessment_id` | `CHAR(32)` | Foreign key to `assessments.id` |
| `parameter_id` | `CHAR(32)` | Foreign key to `assessment_parameters.id` |
| `rule_id` | `CHAR(32)` | Foreign key to `assessment_rules.id` |
| `status` | `VARCHAR(50)` | Finding status |
| `raw_value` | `JSON` | Raw collected value |
| `evaluated_value` | `VARCHAR` | Evaluated value |
| `severity` | `VARCHAR(50)` | Severity |
| `score_contribution` | `FLOAT` | Score contribution |
| `collected_at` | `DATETIME` | Collection timestamp |
| `evaluated_at` | `DATETIME` | Evaluation timestamp |

### `assessment_artifacts`

| Column | Type | Notes |
|---|---|---|
| `id` | `CHAR(32)` | Primary key |
| `tenant_id` | `VARCHAR(64)` | Microsoft tenant ID |
| `assessment_id` | `CHAR(32)` | Foreign key to `assessments.id` |
| `job_id` | `CHAR(32)` | Foreign key to `assessment_jobs.id` |
| `parameter_key` | `VARCHAR(255)` | Registry parameter key |
| `parameter_name` | `VARCHAR(500)` | Display name |
| `service` | `VARCHAR(100)` | Microsoft service |
| `collector_name` | `VARCHAR(255)` | Collector name |
| `graph_endpoint` | `VARCHAR(1000)` | Graph endpoint |
| `artifact_type` | `VARCHAR(50)` | Artifact type |
| `source_script` | `VARCHAR(500)` | PowerShell source script |
| `source_csv` | `VARCHAR(500)` | Source CSV |
| `status` | `VARCHAR(50)` | Collection status |
| `actual_value` | `JSON` | Actual runtime value |
| `expected_value` | `VARCHAR(1000)` | Expected value |
| `raw_evidence_json` | `JSON` | Full evidence payload |
| `collection_timestamp` | `DATETIME` | Collection timestamp |
| `stdout` | `VARCHAR` | Collector stdout |
| `stderr` | `VARCHAR` | Collector stderr |
| `payload` | `JSON` | Additional payload |
| `created_at` | `DATETIME` | Created timestamp |

### `assessment_reports`

| Column | Type | Notes |
|---|---|---|
| `id` | `CHAR(32)` | Primary key |
| `assessment_id` | `CHAR(32)` | Foreign key to `assessments.id` |
| `report_type` | `VARCHAR(20)` | Report type |
| `report_status` | `VARCHAR(50)` | Report state |
| `storage_path` | `VARCHAR(500)` | Report file path |
| `generated_at` | `DATETIME` | Generation timestamp |
| `generated_by` | `CHAR(32)` | Foreign key to `users.id` |
| `metadata_json` | `JSON` | Report metadata |

## Model Relationships

- `users` can trigger many assessments and generate many reports.
- `assessments` have many findings, artifacts, reports, recommendations, events, and jobs.
- `assessment_findings` link an assessment to a parameter and, when available, a scoring rule.
- `assessment_artifacts` link raw runtime evidence to an assessment and job.
- `assessment_reports` link generated report files to an assessment and generating user.
- `connected_tenants` are linked to assessments by `tenant_id` convention.
