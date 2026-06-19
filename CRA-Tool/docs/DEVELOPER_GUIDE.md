# Developer Guide

## Key Files

Backend:

- `CRA-Tool/app/main.py`
- `CRA-Tool/app/api/v1/router.py`
- `CRA-Tool/app/api/v1/assessments.py`
- `CRA-Tool/app/api/v1/tenants.py`
- `CRA-Tool/app/api/v1/reports.py`
- `CRA-Tool/app/core/config.py`
- `CRA-Tool/app/db/models/`
- `CRA-Tool/app/services/runtime_assessment_service.py`
- `CRA-Tool/app/services/runtime_scoring_service.py`
- `CRA-Tool/app/services/registry_service.py`
- `CRA-Tool/app/services/reporting/cra_report_service.py`
- `CRA-Tool/app/services/reporting/report_builder.py`

Assessment registry:

- `CRA-Tool/app/config/assessment_registry/parameters.json`
- `CRA-Tool/app/config/assessment_registry/collectors.json`
- `CRA-Tool/app/config/assessment_registry/rules.json`
- `CRA-Tool/app/config/assessment_registry/recommendations.json`
- `CRA-Tool/app/config/assessment_registry/scoring.json`

Frontend:

- `CRA-frontend/src/main.jsx`
- `CRA-frontend/src/App.jsx`
- `CRA-frontend/src/routes/AppRoutes.jsx`
- `CRA-frontend/src/auth/msalConfig.js`
- `CRA-frontend/src/api/`
- `CRA-frontend/src/context/AuthContext.jsx`
- `CRA-frontend/src/context/AssessmentContext.jsx`

## Adding A Parameter

1. Add the parameter to `CRA-Tool/app/config/assessment_registry/parameters.json`.
2. Add or update the collector mapping in `collectors.json`.
3. Add or update scoring rules in `rules.json`.
4. Add recommendation text in `recommendations.json` if the parameter needs remediation output.
5. If a new collector is required, add it in the correct service runtime path:
   - Graph collector service code under `CRA-Tool/app/services/graph/` or related collector service files.
   - PowerShell script under `CRA-Tool/app/powershell/<service>/`.
6. Make sure the runtime can map the parameter to a collector in `runtime_assessment_service.py`.
7. Run an assessment and confirm:
   - `assessment_artifacts` has evidence for the parameter.
   - `assessment_findings` has the evaluated finding.
   - Scores are updated by `apply_scores()`.
   - Report generation includes the parameter detail.

## Updating Scoring

The main score write path is:

```text
CRA-Tool/app/services/runtime_scoring_service.py
  -> apply_scores()
```

Rules and scoring configuration are stored in:

```text
CRA-Tool/app/config/assessment_registry/rules.json
CRA-Tool/app/config/assessment_registry/scoring.json
```

When changing scoring:

- Do not patch report output to hide scoring defects.
- Verify the finding status and score contribution in `assessment_findings`.
- Verify the final score fields on `assessments`.
- Keep report rendering separate from scoring logic.

## Debugging A Bad Finding

Use this path:

1. Find the assessment ID.
2. Check the assessment row in `assessments`.
3. Check the parameter key in `parameters.json`.
4. Check runtime evidence in `assessment_artifacts`.
5. Check finding output in `assessment_findings`.
6. Check the rule in `rules.json`.
7. Check `apply_scores()` if the score is wrong.
8. Check report rendering only after the database state is correct.

Useful API routes:

```text
GET /api/v1/assessments/{assessment_id}
GET /api/v1/assessments/{assessment_id}/findings
GET /api/v1/assessments/{assessment_id}/evidence
GET /api/v1/assessment-failures/{assessment_id}
GET /api/v1/assessments/{assessment_id}/results
```

## Debugging Report Issues

Start with data, then rendering:

1. Confirm findings exist.
2. Confirm artifacts exist.
3. Confirm `build_report_data()` contains the required values.
4. Confirm `build_docx_report()` receives the values.
5. Confirm the DOCX file exists.
6. Confirm PDF conversion uses the DOCX output.

Useful files:

- `CRA-Tool/app/services/reporting/cra_report_service.py`
- `CRA-Tool/app/services/reporting/report_builder.py`
- `CRA-Tool/app/services/reporting/chart_generator.py`

Useful routes:

```text
GET /api/v1/assessment/report-debug/{assessment_id}
GET /api/v1/report-debug/{assessment_id}
GET /api/v1/assessments/{assessment_id}/report/download
```

## Development Mode

Backend:

```powershell
cd CRA-Tool
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd CRA-frontend
npm.cmd run dev
```

Celery on Windows:

```powershell
cd CRA-Tool
venv\Scripts\celery.exe -A app.core.celery_app worker --loglevel=info --pool=solo
```

## Production Mode

Production setup depends on the target host. At minimum:

- Use real environment variables instead of local defaults.
- Use HTTPS redirect URIs in Azure app registration.
- Protect JWT secrets and encryption keys.
- Run database migrations before starting the app.
- Run the API behind a production ASGI server process manager.
- Run Redis and Celery workers as managed services.
- Store generated reports in a durable location.

## Tests

Backend tests live in:

```text
CRA-Tool/tests/
```

Run tests:

```powershell
cd CRA-Tool
venv\Scripts\pytest.exe -q
```

Frontend build check:

```powershell
cd CRA-frontend
npm.cmd run build
```

## Rules For Safe Changes

- Read the real code path before changing behavior.
- Do not update report rendering to compensate for incorrect findings.
- Do not invent parameter names; use `parameters.json`.
- Do not invent API routes; use `app/api/v1/router.py` and route modules.
- Preserve persisted assessment data unless the task is specifically a scoring or data migration task.
- Treat missing evidence as a real state to debug.
