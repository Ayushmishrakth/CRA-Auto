# CRA — Microsoft 365 Copilot Readiness Assessment Platform

Repo-wide context for GitHub Copilot (Chat, inline completions, and coding agent). Read this before proposing changes.

## What this project is

CRA assesses a Microsoft 365 tenant's readiness for Microsoft 365 Copilot by collecting live evidence via Microsoft Graph and PowerShell, scoring it against a fixed 65-parameter registry, and producing DOCX/PDF reports. It is a real product with real customer tenants — not a demo.

Two deployable halves in this repo, plus one unrelated vendored reference project:

- `CRA-Tool/` — FastAPI backend (Python 3.11+), SQLAlchemy + Alembic, Celery + Redis, Microsoft Graph + PowerShell collectors, scoring engine, DOCX/PDF report generation.
- `CRA-frontend/` — React 18 + Vite 6 frontend, MSAL browser login, Tailwind 4, Recharts.
- `ms-ara/` — Microsoft's own separate "Automated Readiness Assessment" tool, vendored for reference only. It is **not imported or called by CRA-Tool** (verified: no references outside `docs/README.md`). Don't assume code here is wired into the app.

Full docs live in `CRA-Tool/docs/`: `ARCHITECTURE.md` (routes, DB schema, entry points), `ASSESSMENT_ENGINE.md` (runtime flow, full 65-parameter list, scoring), `PARAMETER_ASSESSMENT_REFERENCE.md`, `DEVELOPER_GUIDE.md`, `DEPLOYMENT.md`. Prefer those over guessing — they're kept accurate.

## Architecture at a glance

```
Browser --React+MSAL--> CRA-frontend --Axios+CRA JWT--> FastAPI backend --SQLAlchemy--> SQLite/Postgres
                                                              |
                                                    Microsoft Graph + PowerShell (pwsh)
                                                              v
                                                     Customer Microsoft 365 tenant
```

Backend entry points:
- App: `CRA-Tool/app/main.py`; router: `CRA-Tool/app/api/v1/router.py` (prefix `/api/v1`); WebSocket: `CRA-Tool/app/api/v1/websocket.py`
- Assessment runtime: `app/services/runtime_assessment_service.py`
- Scoring: `app/services/runtime_scoring_service.py` (`apply_scores()`)
- Reports: `app/services/reporting/cra_report_service.py`, `app/services/reporting/report_builder.py`

Frontend entry points:
- `src/main.jsx` → `src/App.jsx` → `src/routes/AppRoutes.jsx`
- MSAL config: `src/auth/msalConfig.js`; API client: `src/api/axiosClient.js`
- Contexts: `src/context/AuthContext.jsx`, `AssessmentContext.jsx`, `WizardContext.jsx`

## The assessment engine (core domain logic)

The product is **exactly 65 scored parameters** across 6 services: Entra ID (21), Exchange Online (6), Microsoft Purview (8), Microsoft Teams (16), OneDrive for Business (3), SharePoint Online (11). This count is load-bearing — it appears in scoring math, readiness %, dashboard KPIs, and report totals.

Registry (single source of truth) at `CRA-Tool/app/config/assessment_registry/`:
- `parameters.json` — the 65 parameters
- `collectors.json` — collector mapping
- `rules.json` — scoring/evaluation rules
- `recommendations.json` — recommendation text
- `scoring.json` — scoring weights/config

A parameter must appear in **all four** of parameters/rules/collectors/recommendations or `AssessmentRegistry.validate()` fails on load. Do not add a parameter to only one file.

**Do not add `assigned_license` (or other non-official collectors) to the registry.** Several collectors exist in `graph_cra_collector_service.py`'s `GRAPH_COLLECTORS` map (~71 entries) that are intentionally *not* part of the scored 65 — they're auxiliary/orphaned by design. `GRAPH_COLLECTORS` membership ≠ registry membership. The assessment loop only iterates `registry.get_parameters()`.

Runtime flow: `POST /api/v1/assessments/start` → job created → `run_assessment_job()` loads registry → per parameter, picks Graph or PowerShell collector → raw evidence persisted to `assessment_artifacts` → findings evaluated into `assessment_findings` → `apply_scores()` updates `assessments` score columns → recommendations generated → progress events emitted over WebSocket.

Collection methods:
- Graph-backed parameters → `app/services/graph/` + `graph_cra_collector_service.py`
- PowerShell-backed parameters → `app/powershell/{entra,exchange,onedrive,purview,sharepoint,teams}/*_master.ps1`, invoked via `app/services/powershell/powershell_runtime.py`

Missing/failed evidence must surface as a runtime gap or failed finding — **never fabricate a pass** when a collector fails or a required license/workload signal is absent.

## Auth model (two separate auth systems — don't conflate them)

1. **User login** (frontend → backend): MSAL ID token → `POST /api/v1/auth/login` → `AuthService` validates, upserts `users` row → backend issues its own CRA access/refresh JWT. Protected routes use `get_current_active_user`; Bearer token thereafter.
2. **Tenant runtime collection** (backend → customer M365 tenant): app-only auth per service, not delegated:
   - Graph → app + client secret
   - Exchange Online PowerShell → app + access token (`Exchange.ManageAsApp`)
   - Teams PowerShell / SharePoint PnP → **app + certificate**, not client secret. `tenant_certificate_service.py` generates a per-tenant self-signed cert, `tenant_deployment_service.deploy_tenant_access` stores it encrypted on `connected_tenants` (cert columns from migration `17a_tenant_certificate`) and uploads it to the app registration's `keyCredentials` via Graph. Runtime loads the per-tenant DB cert into a temp PFX for `_collect_findings`.

Tenant deployment (`POST /api/v1/tenants/deployment/start`) creates/repairs the Entra app registration, requests Graph application permissions (`Application.Read.All`, `Directory.Read.All`, `Group.Read.All`, `User.Read.All`, `Sites.Read.All`, `Sites.FullControl.All`, etc.), Exchange `Exchange.ManageAsApp`, and Teams application access — but **admin consent and the Teams Administrator role assignment require a one-time interactive Global Admin action**; the backend cannot self-grant these. Don't assume a tenant is fully unattended-ready just because `deployment_status`/`consent_status` looks "connected" — verify actual `keyCredentials`, granted permissions, and role assignments if debugging a live collection failure.

## Database

SQLAlchemy models in `CRA-Tool/app/db/models/`. Key tables: `users`, `connected_tenants`, `assessments`, `assessment_parameters`, `assessment_findings`, `assessment_artifacts`, `assessment_reports`. Full column-level schema is in `docs/ARCHITECTURE.md`. Migrations via Alembic in `CRA-Tool/migrations/versions/` — always add a migration for model changes, never hand-edit `cra.db`.

## Running locally

Four processes, in order: Redis → backend (`CRA-Tool/start.ps1`, runs `alembic upgrade head` then `uvicorn`) → Celery worker (`celery -A app.tasks.assessment_tasks worker --loglevel=info --pool=solo` — `--pool=solo` is required on Windows) → frontend (`npm run dev`, port 3000). Backend API on port 8000, docs at `/docs`. See root `README.md` for full setup/env var reference and `CRA-Tool/.env.example` / `CRA-frontend/.env.example` for required config keys.

## Conventions

- Backend: FastAPI + Pydantic v2 schemas in `app/schemas/`, service-layer logic in `app/services/` (routes stay thin), repositories in `app/db/repositories/`.
- PowerShell collectors follow a `*_master.ps1` per service pattern sharing `app/powershell/common/cra_common.ps1`; they emit CSV parsed by `app/services/csv_ingestion/*_csv_parser.py`.
- Tests live in `CRA-Tool/tests/` (pytest) — run with `pytest -q` from `CRA-Tool/`.
- Frontend uses Tailwind 4 utility classes and `src/styles/design-tokens.css`; charts via Recharts in `src/components/charts/`.
- Numerous root-level `*.md`/`*.txt` files in `CRA-Tool/` (e.g. `LOGO_FIXES_SUMMARY.md`, `FINAL_IMPLEMENTATION_COMPLETE.md`) are historical dev notes, not authoritative docs — prefer `CRA-Tool/docs/` and this file.
