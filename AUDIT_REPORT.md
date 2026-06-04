# CRA Platform Production Audit Report

Date: 2026-05-31  
Scope: `CRA-frontend`, `CRA-Tool`, assessment runtime, parameter registry, tenant deployment, evidence collection, report generation, queueing, persistence, and production readiness.

## Executive Summary

The platform has moved beyond a pure prototype: Microsoft Entra deployment is implemented, assessments are queued through Celery, WebSocket progress exists, PowerShell collectors execute, findings/artifacts/recommendations/reports are persisted, and PDF/DOCX report renderers exist.

The main production gaps are:

1. CRA parameters are still runtime-loaded from static JSON files, not imported/versioned from Excel into database tables.
2. Assessment scoring is registry/severity deduction based, not a full evidence + criteria engine.
3. Evidence is persisted indirectly in `assessment_findings.raw_value` and `assessment_artifacts.payload`, but there is no canonical per-parameter evidence table.
4. The Graph runtime exists but is not the main assessment runtime; the active runtime is `phase7b_powershell`.
5. Frontend has several prototype UI sections and client-side inferred trends/status labels.
6. Report generation uses actual persisted findings where available, but has fallback narrative text and generic recommendations when recommendation data is absent.
7. PostgreSQL is supported via `DATABASE_URL`, but development defaults still point to SQLite.

## Current Architecture

```text
React + MSAL
  -> FastAPI API
    -> SQLAlchemy async database session
      -> SQLite dev / PostgreSQL target
    -> Celery task queue
      -> Redis broker/backend
      -> runtime_assessment_service
        -> PowerShellExecutionEngine
        -> registry JSON
        -> findings/artifacts/events
        -> scoring/recommendations
        -> PDF/DOCX report bundle
    -> WebSocket event stream
```

## Phase 1 Audit Findings

### 1. Hardcoded Data

Backend:

- `scripts/build_registry.py` has hardcoded local default workbook paths under `/home/herb/Downloads/...`. This cannot work reliably in production or on this Windows workspace.
- `app/services/registry_service.py` hardcodes the runtime registry directory to `app/config/assessment_registry`.
- `app/services/runtime_assessment_service.py` hardcodes runtime metadata as `phase7b_powershell`.
- `app/core/config.py` defaults `database_url` to `sqlite:///./cra.db`, Redis to localhost, and Entra tenant to `common`.

Frontend:

- Dashboard displays profile/token architecture panels intended for implementation visibility, not production operators.
- `src/utils/assessmentFormatters.js` hardcodes fake domain trends: `+3.2%`, `+0.8%`, `-1.4%`.
- Several labels infer readiness status client-side instead of using backend-calculated status.

### 2. Mock Data

No deliberate mock evidence is currently allowed in the active PowerShell runtime. `PowerShellExecutionEngine._contract_uses_mock_data()` fails closed when collectors return `mock`, `local_mock`, or `simulated`.

Remaining prototype-like placeholders:

- Frontend shows an `empty-recommendation` fallback card when recommendations are absent.
- Report section builder uses generic fallback text such as `Review and remediate this control` when no recommendation exists.
- Report descriptions fall back to generic Copilot readiness text when parameter narrative is missing.

### 3. Dummy Assessment Scores

The active score calculation is not dummy, but it is not yet a full CRA scoring engine.

Current behavior:

- `runtime_scoring_service.calculate_scores()` starts each domain at 100.
- Failed/warning findings deduct points using severity deductions and registry weights.
- Critical Copilot blockers cap overall score.

Gap:

- Scores are not derived from normalized evidence metrics against explicit pass/fail criteria stored in a versioned parameter database.
- There is no `cra_assessment_results` table with `parameter_id`, `evidence`, `raw_response`, `score`, `status`, and `timestamp`.

### 4. Placeholder Reports

Reports are generated from persisted assessment data and are not static files. However:

- Report narrative has generic fallback wording.
- Missing recommendations produce generic remediation wording.
- Reports do not yet include a formal remediation roadmap model.
- Evidence is embedded from finding/artifact payloads rather than a canonical evidence table.

### 5. Static Pass/Fail Logic

Current pass/fail sources:

- Collector contracts can return a `status`.
- CSV evidence can be reduced to pass/warning/fail from CSV row statuses.
- `app/services/findings/rule_engine.py` supports only simple `min_count`, `max_count`, `equals`, and `forbidden_values`.
- Registry rules are generated from text criteria into shallow expressions.

Gap:

- Natural-language Excel criteria are not compiled into robust typed evaluators.
- Pass/fail criteria are not versioned or persisted as first-class production rules.

### 6. Incomplete APIs

Current API coverage includes:

- Auth: login, refresh, logout, `/auth/me`
- Tenants: connect/list/get/delete, deployment start, deployment validation/debug, permissions
- Assessments: start, get, list by tenant, findings, events, job, score, recommendations, report generate/get/download
- Registry: list parameters from static JSON
- Health: app/db/auth/system
- Reports: status wrapper

Gaps:

- No API to upload/import Excel parameter workbooks.
- No API to list parameter versions.
- No API to activate/rollback parameter versions.
- No API for canonical evidence records.
- No API for assessment result rows independent of findings.
- No API for queue monitoring beyond per-assessment job state.
- No metrics endpoint.

### 7. Missing Database Persistence

Persisted today:

- Tenants, users, sessions, audit logs
- Assessments, jobs, events
- Assessment parameters/rules seeded from registry JSON
- Findings
- Artifacts
- Recommendations
- Report artifacts

Missing for production CRA engine:

- `cra_parameter_versions`
- `cra_parameter_evidence`
- `cra_assessment_results`
- Parameter workbook import metadata
- Criteria compiler metadata
- Evidence collection source identity and Graph endpoint lineage per parameter
- Historical compliance trend aggregates

### 8. Unused / Underused Models and Services

- `GraphRuntime` exists but is not the primary assessment runtime.
- `findings.rule_engine` and `findings.finding_engine` exist but are not the main runtime path.
- `assessment_parameters` and `assessment_rules` are seeded from JSON, not owned by database versioning.
- `/reports/assessments/{assessment_id}` duplicates some report status behavior already exposed under `/assessments/{assessment_id}/report`.

### 9. Broken or Risky Report Flow

Working:

- `runtime_assessment_service` invokes `cra_report_service.generate_report_bundle()` after scoring/recommendations.
- PDF and DOCX artifacts are persisted in `assessment_reports`.

Risks:

- Report files are written to local `storage/reports`, not object storage or a durable shared volume.
- Report generation runs inside the assessment task rather than a separate retryable report job.
- Download endpoint trusts stored file paths and does not verify file existence before `FileResponse`.
- No report template versioning.

## Frontend Audit

Strengths:

- Real MSAL integration.
- API client normalization layer.
- Assessment live updates through WebSocket subscription.
- Pages exist for dashboard, tenant deployment, assessments, assessment details, parameters, reports.
- Uses chart components for readiness/severity/domain views.

Production gaps:

- Dashboard still shows developer-facing panels: profile, token architecture, backend health.
- No full enterprise shell comparable to Azure Portal/Defender with dense navigation and command surfaces.
- No dark/light mode implementation found.
- No dedicated Evidence Viewer page.
- No Recommendations Center page.
- No Tenant Management console beyond deployment connection page.
- Trend values are fabricated in frontend formatting.
- Empty recommendation fallback can look like real content.
- Error/loading/empty states exist but are inconsistent.

## Backend Audit

Strengths:

- FastAPI is modularized under `app/api/v1`.
- Tenant-scoped checks exist.
- Entra deployment validation now verifies Graph identifiers before consent URL generation.
- Celery and Redis config exists.
- Structured domain models exist for jobs/events/findings/artifacts/reports.
- Audit service exists.

Production gaps:

- SQLite remains the default.
- Parameter registry is file-based at runtime.
- No Excel upload/import API.
- No canonical evidence/result tables.
- Microsoft Graph collection is not the default runtime path.
- Health check has xfailed test coverage for migration status.
- Search/sort behavior has known xfailed coverage.

## Assessment Engine Audit

Current flow:

```text
POST /assessments/start
  -> create Assessment + AssessmentJob
  -> enqueue Celery run_assessment_task
  -> runtime_assessment_service.run_assessment_job
  -> seed parameters/rules from JSON
  -> execute PowerShell collectors
  -> persist artifacts/findings/events
  -> score
  -> recommendations
  -> report bundle
  -> completed
```

Gaps:

- Engine runs every registry parameter; no parameter version lock per assessment.
- No explicit `AssessmentResult` row per parameter.
- Collector failures stop scoring/report generation by marking assessment incomplete.
- Scoring uses findings after collectors, not typed criteria evaluation from parameter definitions.

## Parameter Loading Audit

Current state:

- `scripts/build_registry.py` can compile Excel workbooks into JSON registries.
- Runtime explicitly says Excel parsing stays in the script.
- No workbook files are present in the workspace.
- Registry API reads JSON, not database rows.

Required production design:

```text
Excel upload/import
  -> parse workbook
  -> normalize rows
  -> validate required columns
  -> create cra_parameter_versions row
  -> upsert cra_parameters
  -> create criteria/evidence mapping rows
  -> activate version
  -> assessment jobs lock to active version
```

## Tenant Deployment Audit

Strengths:

- Validates Graph token audience, scopes, tenant, and organization.
- Verifies App Registration object ID and client ID through Graph.
- Recovers stale/deleted app registrations.
- Generates consent URL from verified Graph appId.
- Adds dedicated deployment validation endpoint.

Remaining production work:

- Store deployment validation events in audit logs in addition to diagnostics JSON.
- Add alerting/metrics for stale deployment recovery.
- Ensure all app registration creation failures include Graph correlation/request IDs.

## Evidence Collection Audit

Current evidence sources:

- PowerShell collector stdout contract.
- CSV files generated by scripts.
- Artifact payloads.
- Finding raw values.

Production gaps:

- Graph evidence collection is not the main path.
- Raw Graph responses are not stored in canonical evidence records.
- Evidence schemas differ by collector and are not versioned.
- No evidence retention policy.

## Target Database Schema

Existing tables should remain, but production CRA requires these canonical additions:

```text
cra_parameter_versions
  id uuid pk
  version string unique
  source_filename string
  source_hash string
  imported_by uuid fk users.id
  imported_at timestamptz
  is_active bool
  validation_report jsonb

cra_parameters
  id uuid pk
  version_id uuid fk cra_parameter_versions.id
  parameter_key string
  display_name string
  domain string
  category string
  technology string
  severity string
  weight numeric
  pass_criteria text
  fail_criteria text
  criteria_expression jsonb
  collector_type string
  graph_endpoint string nullable
  powershell_mapping string nullable
  portal_mapping text nullable
  expected_output text nullable
  copilot_relevance text nullable
  is_active bool
  source_ref jsonb
  unique(version_id, parameter_key)

cra_parameter_evidence
  id uuid pk
  assessment_id uuid fk assessments.id
  tenant_id string
  parameter_id uuid fk cra_parameters.id
  collector_type string
  graph_endpoint string nullable
  evidence jsonb
  raw_response jsonb
  source string
  collected_at timestamptz
  status string
  error text nullable

cra_assessment_results
  id uuid pk
  assessment_id uuid fk assessments.id
  tenant_id string
  parameter_id uuid fk cra_parameters.id
  evidence_id uuid fk cra_parameter_evidence.id
  score numeric
  status string
  severity string
  recommendation text
  gap_analysis text
  evaluated_at timestamptz
  criteria_snapshot jsonb
```

## Target API Inventory

Keep existing APIs and add:

```text
POST /api/v1/parameters/import
GET  /api/v1/parameters/versions
GET  /api/v1/parameters/versions/{version_id}
POST /api/v1/parameters/versions/{version_id}/activate
GET  /api/v1/parameters
GET  /api/v1/parameters/{parameter_id}

GET  /api/v1/assessments/{assessment_id}/evidence
GET  /api/v1/assessments/{assessment_id}/evidence/{parameter_id}
GET  /api/v1/assessments/{assessment_id}/results
GET  /api/v1/assessments/{assessment_id}/risk-matrix

GET  /api/v1/jobs
GET  /api/v1/jobs/{job_id}
POST /api/v1/jobs/{job_id}/retry

GET  /api/v1/metrics
GET  /api/v1/health/migrations
```

## Assessment Flow Diagram

```text
User starts assessment
  -> API validates ACTIVE tenant
  -> lock active parameter version
  -> create assessment job
  -> Celery worker starts
  -> collect Graph evidence by parameter
  -> persist cra_parameter_evidence
  -> evaluate criteria
  -> persist cra_assessment_results
  -> compute weighted scores
  -> generate recommendations/gap analysis
  -> generate report job
  -> emit WebSocket progress throughout
  -> completed
```

## Report Flow Diagram

```text
Assessment completed
  -> load assessment metadata
  -> load cra_assessment_results
  -> load cra_parameter_evidence
  -> build executive summary
  -> build risk matrix
  -> build recommendations and roadmap
  -> render PDF
  -> render DOCX
  -> persist report artifacts
  -> expose download links
```

## UI Redesign Plan

Production navigation:

- Overview Dashboard
- Assessments
- Assessment Wizard
- Live Assessment Progress
- Evidence Viewer
- Reports
- Recommendations Center
- Tenants
- Parameters
- Admin/Operations

Required visual model:

- Azure/Defender-like left navigation.
- Dense command bars.
- Tables with filtering, sorting, grouping.
- Risk and score charts backed by API data only.
- Dark/light mode via CSS variables and persisted preference.
- No developer panels in production dashboard.

## Missing Components List

1. Excel parameter import API and DB models.
2. Active parameter version locking per assessment.
3. Canonical evidence/result tables.
4. Graph-first collector runtime.
5. Criteria compiler/evaluator for imported pass/fail rules.
6. Evidence viewer API and UI.
7. Report job separation and retry.
8. Durable report storage abstraction.
9. Metrics endpoint.
10. Migration health endpoint.
11. Queue monitoring dashboard.
12. Dark/light theme system.
13. Production tenant management console.

## Refactoring Plan

1. Introduce CRA parameter DB models and migrations.
2. Move JSON registry behind a compatibility adapter.
3. Add Excel import service using uploaded workbook bytes.
4. Seed current JSON registry into DB only as migration/bootstrap data, not mock data.
5. Replace `runtime_scoring_service` with evidence criteria scoring.
6. Add Graph collector classes by domain: Identity, Device, Data, Security, Compliance.
7. Persist all raw evidence and normalized evidence.
8. Generate reports from `cra_assessment_results`, not findings/artifacts fallbacks.
9. Redesign frontend around production workspaces.
10. Add operational telemetry, metrics, retry dashboards, and deployment checks.

## Production Deployment Checklist

- Rotate all exposed Azure client secrets.
- Set `DATABASE_URL` to PostgreSQL.
- Run Alembic migrations on startup/deploy.
- Set Redis/Celery URLs to managed Redis.
- Disable `DEBUG`.
- Set strong `SECRET_KEY`.
- Configure allowed CORS origins.
- Use tenant-specific Entra authority for production where applicable.
- Use persistent storage for report artifacts.
- Add structured JSON logs.
- Add metrics scraping.
- Add health checks for database, Redis, Celery, Graph token acquisition, migrations.
- Add backup/retention policy for evidence and reports.
- Add RBAC for admin/import/report access.
- Add audit logging for parameter imports, version activation, assessment starts, report downloads.

## Immediate Next Implementation Slice

The safest next implementation is Phase 2 foundation:

1. Add `cra_parameter_versions`, `cra_parameters`, `cra_parameter_evidence`, and `cra_assessment_results`.
2. Add Alembic migration.
3. Add Excel import service and API.
4. Import only real uploaded workbooks. Do not synthesize rows.
5. Update assessment runtime to lock active parameter version.

No Excel workbook currently exists in this workspace, so parameter import cannot be executed yet.
