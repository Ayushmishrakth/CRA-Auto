# CRA Platform Runtime Flow

## End-to-End Flow

```text
User Login
  -> Tenant Connection
  -> Deploy CRA Access
  -> Admin Consent
  -> Assessment Creation
  -> Collector Execution
  -> Artifact Persistence
  -> Finding Creation
  -> Scoring
  -> Recommendation Generation
  -> Report Generation
```

## 1. User Login

Entry points:

- Frontend: `src/pages/LoginPage.jsx`
- Frontend auth: `src/context/AuthContext.jsx`, `src/auth/msalAuth.js`
- Backend API: `POST /api/v1/auth/login`
- Backend route: `app/routes/auth.py`
- Backend service: `app/services/auth_service.py`
- Token validation: `app/core/microsoft.py`

Execution:

1. User clicks Microsoft login.
2. `loginWithMicrosoftPopup` calls MSAL `loginPopup`.
3. Frontend sends Microsoft ID token to `POST /auth/login`.
4. Backend validates token signature, audience, issuer, expiry, `oid`, `tid`, email.
5. Backend upserts `users`.
6. Backend ensures a `connected_tenants` row exists for `tid` if missing.
7. Backend creates CRA access and refresh tokens.
8. Frontend stores CRA JWTs.

Tables touched:

- `users`
- `connected_tenants`
- `user_sessions`
- `refresh_tokens`
- `audit_logs`

External Graph endpoints:

- None directly during backend login; token validation uses Microsoft JWKS from Entra metadata.

Output:

- CRA access token
- CRA refresh token
- current user profile

## 2. Tenant Connection

Entry points:

- Frontend: `src/pages/TenantConnectionPage.jsx`
- Frontend API: `src/api/tenantApi.js`
- Backend API:
  - `GET /api/v1/tenants`
  - `POST /api/v1/tenants/connect`
  - `GET /api/v1/tenants/{tenant_id}`

Service:

- `app/services/tenant_service.py`

Tables touched:

- `connected_tenants`

Output:

- Tenant status and deployment metadata.

## 3. Deploy CRA Access

Entry points:

- Frontend button: `TenantConnectionPage.runDeploy`
- Frontend Graph token: `AuthContext.getTenantDeploymentToken`
- Backend API: `POST /api/v1/tenants/deployment/start`
- Backend service: `tenant_deployment_service.deploy_tenant_access`

Important files:

- `app/services/tenant_deployment_service.py`
- `app/services/graph_app_registration_service.py`
- `app/services/graph_permission_service.py`
- `app/services/graph_service_principal_service.py`
- `app/services/tenant_secret_service.py`

Execution:

1. Frontend acquires delegated Microsoft Graph token with:
   - `User.Read`
   - `Directory.Read.All`
   - `Application.ReadWrite.All`
   - `AppRoleAssignment.ReadWrite.All`
2. Backend validates Graph token tenant, audience, expiry, and scopes.
3. Backend reads `/me` and `/organization`.
4. Backend discovers Microsoft Graph service principal and app role IDs.
5. Backend creates or repairs the CRA app registration.
6. Backend patches redirect URI.
7. Backend patches required Graph app permissions if missing.
8. Backend creates/ensures service principal.
9. Backend creates client secret and stores encrypted secret.
10. Backend builds admin consent URL.

Tables touched:

- `connected_tenants`
- `audit_logs`

Graph endpoints used:

- `/me`
- `/organization`
- `/servicePrincipals?$filter=appId eq '00000003-0000-0000-c000-000000000000'`
- `/applications`
- `/applications/{application_object_id}`
- `/applications/{application_object_id}/addPassword`
- service principal endpoints in `graph_service_principal_service.py`

Output:

- App registration object id
- Application client id
- Service principal id
- Secret metadata
- Admin consent URL
- Deployment diagnostics

## 4. Admin Consent

Entry points:

- Browser navigates to generated Microsoft admin consent URL.
- Frontend route after redirect: `/tenant/deployment-success`
- Backend API: `POST /api/v1/tenants/deployment/validate-consent`
- Backend service: `tenant_deployment_service.validate_admin_consent`

Execution:

1. Admin grants tenant-wide consent in Azure.
2. Frontend returns to `/tenant/deployment-success`.
3. Frontend requests a delegated Graph token again.
4. Backend validates deployment with retry.
5. Backend checks app registration, service principal, secret, required permissions, app role assignments.
6. Tenant becomes `ACTIVE` when all checks pass.

Tables touched:

- `connected_tenants`
- `audit_logs`

Graph endpoints used:

- `/applications/{application_object_id}`
- `/servicePrincipals/{service_principal_id}`
- `/servicePrincipals/{service_principal_id}/appRoleAssignments`
- Microsoft Graph service principal lookup

Output:

- `connected_tenants.status = ACTIVE`
- `consent_status = connected`
- validation diagnostics

## 5. Assessment Creation

Entry points:

- Frontend: `DashboardPage.handleStartAssessment` or `AssessmentsPage.handleRestart`
- API: `POST /api/v1/assessments/start`
- Route: `app/api/v1/assessments.py`
- Service: `app/services/assessment_service.py`

Execution:

1. Backend verifies request tenant equals current user tenant.
2. Backend verifies `connected_tenants.status == ACTIVE`.
3. Backend inserts `assessments` with status `queued`.
4. Backend inserts `assessment_jobs` with status `queued`.
5. Backend audits assessment start.
6. Backend queues Celery task or local background task.

Tables touched:

- `connected_tenants`
- `assessments`
- `assessment_jobs`
- `audit_logs`

Output:

- Assessment id
- Job id
- Initial status/progress

## 6. Collector Execution

Entry point:

- Celery task: `app/tasks/assessment_tasks.py`
- Runtime function: `app/services/runtime_assessment_service.py::run_assessment_job`

Execution:

1. Job loads assessment.
2. Stage becomes `running/starting`.
3. Registry is seeded into `assessment_parameters` and `assessment_rules`.
4. Existing findings/artifacts for the assessment are deleted.
5. Runtime parameter set is selected by `_runtime_parameters`.
6. Current selector only chooses `FIRST_OPERATIONAL_GRAPH_PARAMETERS`.
7. For selected parameters:
   - if key exists in `GRAPH_COLLECTORS`, run Graph collector
   - otherwise run PowerShell engine

Tables touched:

- `assessment_jobs`
- `assessments`
- `assessment_parameters`
- `assessment_rules`
- `assessment_artifacts`
- `assessment_findings`
- `assessment_events`

Graph endpoints used by current collectors:

- `/directoryRoles`
- `/directoryRoles/{id}/members`
- `/users`
- `/policies/authorizationPolicy/authorizationPolicy`

Output:

- runtime events
- collector artifacts
- findings

## 7. Artifact Persistence

Entry point:

- `_persist_artifact` in `app/services/runtime_assessment_service.py`

Tables touched:

- `assessment_artifacts`

Output:

- one artifact row per collector attempt
- raw evidence, raw response, endpoint, status, source script/CSV if available

## 8. Finding Creation

Entry point:

- `_persist_finding` in `app/services/runtime_assessment_service.py`

Tables touched:

- `assessment_findings`

Output:

- normalized finding status
- severity
- raw value
- evaluated value
- score contribution

## 9. Scoring

Entry point:

- `apply_scores` in `app/services/runtime_scoring_service.py`

Tables touched:

- `assessments`

Execution:

1. Reads registry scoring config from `app/config/assessment_registry/scoring.json`.
2. Starts domain scores at 100.
3. Deducts by severity, finding status, and scoring weight.
4. Applies blocker cap if a Copilot blocker fails.
5. Writes scores and finding counts to `assessments`.

Output:

- `overall_score`
- `identity_score`
- `security_score`
- `compliance_score`
- `collaboration_score`
- `licensing_score`
- `total_findings`
- `critical_findings`
- `high_findings`

Important caveat:

- Scoring only runs if all selected collectors complete. If any selected collector fails, runtime marks the assessment `incomplete` and does not score.

## 10. Recommendation Generation

Entry point:

- `generate_recommendations` in `app/services/runtime_recommendation_service.py`

Tables touched:

- `assessment_recommendations`

Execution:

1. Deletes previous recommendations for the assessment.
2. Reads recommendation templates from registry.
3. Generates one recommendation per finding with priority score.

Output:

- recommendation rows
- recommendation websocket events

## 11. Report Generation

Entry points:

- Automatic at end of completed runtime: `cra_report_service.generate_report_bundle`
- Manual from UI: `POST /api/v1/assessments/{assessment_id}/generate-report`
- Report fetch: `GET /api/v1/assessments/{assessment_id}/report`

Tables touched:

- `assessment_reports`
- `assessments`
- `assessment_findings`
- `assessment_recommendations`
- `assessment_artifacts`

Output:

- `storage/reports/{assessment_id}/copilot-readiness-assessment.pdf`
- `storage/reports/{assessment_id}/copilot-readiness-assessment.docx`
- `assessment_reports` rows
- `assessments.report_path`
