# CRA Platform Database Analysis

## Current Database

The project currently uses SQLAlchemy async ORM with SQLite configured by default in `app/core/config.py`.

Migration system:

- Alembic: `CRA-Tool/alembic.ini`
- Migration env: `CRA-Tool/migrations/env.py`
- Model import registry: `app/db/base.py`

The schema is intended to be portable to PostgreSQL, but there are areas to review before production migration:

- JSON storage abstraction is custom (`app/db/types.py`).
- SQLite datetime behavior may differ from PostgreSQL.
- Report file paths are local filesystem paths, not object storage references.

## Tables

| Table | Model | Purpose |
|---|---|---|
| `users` | `app/db/models/user.py` | Microsoft Entra user identities |
| `connected_tenants` | `app/db/models/tenant.py` | Tenant deployment and consent state |
| `user_sessions` | `app/db/models/user_session.py` | CRA JWT session tracking and revocation |
| `refresh_tokens` | `app/db/models/refresh_token.py` | refresh token rotation/revocation |
| `audit_logs` | `app/db/models/audit_log.py` | login, tenant, assessment audit events |
| `assessments` | `app/db/models/assessment.py` | assessment run header and scores |
| `assessment_jobs` | `app/db/models/assessment_job.py` | async runtime job state |
| `assessment_events` | `app/db/models/assessment_event.py` | runtime event stream |
| `assessment_parameters` | `app/db/models/assessment_parameter.py` | materialized registry parameters for findings |
| `assessment_rules` | `app/db/models/assessment_rule.py` | materialized registry rules |
| `assessment_findings` | `app/db/models/assessment_finding.py` | normalized parameter findings |
| `assessment_artifacts` | `app/db/models/assessment_artifact.py` | raw collector evidence and telemetry |
| `assessment_recommendations` | `app/db/models/assessment_recommendation.py` | generated remediation guidance |
| `assessment_reports` | `app/db/models/assessment_report.py` | generated PDF/DOCX artifacts |
| `cra_parameter_versions` | `app/db/models/cra_parameter.py` | imported CRA parameter version metadata |
| `cra_parameters` | `app/db/models/cra_parameter.py` | production parameter catalog |
| `cra_parameter_evidence` | `app/db/models/cra_parameter.py` | production evidence model, currently separate from runtime artifact path |
| `cra_assessment_results` | `app/db/models/cra_parameter.py` | production result model, currently separate from runtime findings path |

## Key Relationships

Auth:

- `users.id -> user_sessions.user_id`
- `users.id -> refresh_tokens.user_id`
- `users.id -> audit_logs.user_id`

Tenant:

- `connected_tenants.tenant_id` is a unique natural key.
- Most assessment runtime rows are scoped by tenant id, but not all use formal FK constraints to `connected_tenants`.

Assessment:

- `assessments.triggered_by_user_id -> users.id`
- `assessment_jobs.assessment_id -> assessments.id`
- `assessment_events.assessment_id -> assessments.id`
- `assessment_findings.assessment_id -> assessments.id`
- `assessment_artifacts.assessment_id -> assessments.id`
- `assessment_recommendations.assessment_id -> assessments.id`
- `assessment_reports.assessment_id -> assessments.id`

Parameter/finding:

- `assessment_findings.parameter_id -> assessment_parameters.id`
- `assessment_findings.rule_id -> assessment_rules.id`
- `assessment_rules.parameter_id -> assessment_parameters.id`

CRA parameter engine:

- `cra_parameters.version_id -> cra_parameter_versions.id`
- `cra_parameter_evidence.parameter_id -> cra_parameters.id`
- `cra_assessment_results.parameter_id -> cra_parameters.id`
- `cra_assessment_results.evidence_id -> cra_parameter_evidence.id`

## Assessment Data Model

Runtime assessment data flows through the older runtime tables:

```text
assessments
  -> assessment_jobs
  -> assessment_events
  -> assessment_artifacts
  -> assessment_findings
  -> assessment_recommendations
  -> assessment_reports
```

The newer production parameter engine tables exist but are not the primary runtime path:

```text
cra_parameter_versions
  -> cra_parameters
  -> cra_parameter_evidence
  -> cra_assessment_results
```

This creates an architectural split:

- Runtime execution uses `assessment_parameters`, `assessment_rules`, `assessment_findings`, and `assessment_artifacts`.
- Production-looking model names use `cra_parameters`, `cra_parameter_evidence`, and `cra_assessment_results`.
- Report generation currently reads runtime findings/artifacts, not `cra_assessment_results`.

## Important Indexes

Tenant/runtime:

- `ix_assessments_tenant_status_created_at`
- `ix_assessment_jobs_tenant_status`
- `ix_assessment_jobs_assessment_created`
- `ix_assessment_artifacts_assessment_parameter`
- `ix_assessment_artifacts_tenant_created`
- `ix_assessment_recommendations_tenant_created`
- `ix_assessment_recommendations_assessment_created`
- `ix_audit_logs_tenant_event_created_at`

Reports:

- `ix_assessment_reports_assessment_type`
- `ix_assessment_reports_status`

CRA parameter engine:

- `uq_cra_parameters_version_key`
- `ix_cra_parameter_evidence_assessment_parameter`
- `uq_cra_assessment_results_assessment_parameter`

## Database Risks

1. Split parameter/result model:
   Runtime findings and the newer `cra_assessment_results` tables can diverge.

2. Local filesystem reports:
   `assessment_reports.storage_path` points at local `storage/reports`, which is not production-safe for multiple workers/containers.

3. Tenant id as string scope:
   Tenant scoping is mostly application-enforced. PostgreSQL migration should review FK strategy and row-level security requirements.

4. Deleting assessment findings/artifacts before collection:
   `_collect_findings` deletes previous findings/artifacts for the assessment before running collectors. If a rerun fails, prior evidence is lost.

5. Incomplete assessment behavior:
   If any selected collector fails, scoring/recommendations/report generation are skipped. This can leave assessment rows without scores.
