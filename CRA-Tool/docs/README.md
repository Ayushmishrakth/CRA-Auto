# CRA Tool Documentation

CRA Tool is a Microsoft 365 Copilot Readiness Assessment application. It connects to a Microsoft tenant, runs readiness checks across Entra ID, Exchange Online, Microsoft Purview, Microsoft Teams, OneDrive for Business, and SharePoint Online, stores evidence and findings, and generates DOCX/PDF reports.

## Project Structure

```text
CRA-Auto/
|-- CRA-Tool/                  Backend FastAPI application, assessment engine, DB models, collectors, reports, and tests.
|   |-- app/                   Backend source code.
|   |   |-- api/v1/            FastAPI routers for auth, tenants, assessments, reports, registry, parameters, admin, health, and websockets.
|   |   |-- config/            Assessment registry files: parameters, collectors, rules, recommendations, and scoring.
|   |   |-- core/              Settings, auth helpers, security, Celery, responses, and exceptions.
|   |   |-- db/                SQLAlchemy session, base metadata, and database models.
|   |   |-- powershell/        PowerShell collectors grouped by Microsoft service.
|   |   |-- schemas/           Pydantic request and response schemas.
|   |   |-- services/          Auth, tenant deployment, runtime assessment, scoring, Graph, PowerShell, registry, and reporting services.
|   |   |-- tasks/             Celery task entry points for assessment jobs.
|   |   `-- main.py            FastAPI app setup and router registration.
|   |-- app/config/assessment_registry/
|   |   |-- parameters.json    Source of truth for the 65 assessment parameters.
|   |   |-- collectors.json    Collector mapping.
|   |   |-- rules.json         Rule definitions used during scoring.
|   |   |-- recommendations.json Recommendation text used by the report and API.
|   |   `-- scoring.json      Scoring configuration.
|   |-- migrations/           Alembic migration files.
|   |-- reports/              Generated report output.
|   |-- storage/              Runtime storage used by the backend.
|   |-- tests/                Backend tests.
|   |-- requirements.txt      Python dependencies.
|   |-- pyproject.toml        Python project/tooling metadata.
|   `-- cra.db                Local SQLite database file.
|-- CRA-frontend/             React/Vite frontend application.
|   |-- src/                  Frontend source code.
|   |   |-- api/               Axios clients and API wrappers.
|   |   |-- auth/              MSAL configuration and Microsoft login helpers.
|   |   |-- components/        Shared UI components.
|   |   |-- context/           Auth and assessment React contexts.
|   |   |-- pages/             Dashboard, assessments, reports, settings, and other screens.
|   |   |-- routes/            React route definitions.
|   |   |-- main.jsx           React entry point.
|   |   `-- App.jsx           Main app shell.
|   |-- package.json         Frontend dependencies and scripts.
|   |-- vite.config.js       Vite dev/build config.
|   `-- dist/                Built frontend assets.
|-- ms-ara/                   Microsoft assessment/reference material used by the project.
|-- start.bat                 Windows startup helper.
|-- start.sh                  Shell startup helper.
`-- README.md                 Repository-level readme.
```

## Tech Stack

Backend:

- Python
- FastAPI
- SQLAlchemy
- Alembic
- SQLite for local development, with async database support also present in dependencies.
- Pydantic
- Microsoft Authentication Library (`msal`)
- JWT libraries (`python-jose`, `PyJWT`)
- Celery and Redis for background work
- Microsoft Graph access through `httpx`/`requests`
- PowerShell collector scripts for Microsoft 365 workloads
- `python-docx`, `docxtpl`, `matplotlib`, `Pillow`, and ReportLab/reporting helpers for reports
- Pytest for tests

Frontend:

- React 18
- Vite
- Microsoft MSAL browser/react packages
- React Router
- Axios
- Tailwind CSS
- Recharts
- Lucide React icons
- Framer Motion

## Quick Start

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

Default local URLs:

- Backend API: `http://localhost:8000`
- Frontend: Vite chooses the configured/dev port. In this repository the frontend code reads `window.location.origin` for the redirect URI, so the Azure app registration redirect URI must match the actual browser origin used for login, for example `http://localhost:5173` or `http://localhost:3000`.

## Main Documentation Files

- `ARCHITECTURE.md`: System design, auth flow, API routes, and database schema.
- `ASSESSMENT_ENGINE.md`: Assessment runtime flow, all 65 parameters, scoring, licensing behavior, and pillars.
- `REPORT_GENERATION.md`: DOCX/PDF report flow, page structure, charts, and `report_data` keys.
- `DEPLOYMENT.md`: Prerequisites, environment variables, setup, tenant connection, assessment run, ports, and known issues.
- `DEVELOPER_GUIDE.md`: How to add parameters, update scoring, debug findings, find key files, run tests, and work in dev/prod.
