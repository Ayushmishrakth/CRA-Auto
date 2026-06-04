# Microsoft 365 Copilot Readiness Assessment Backend

FastAPI backend for the Microsoft 365 Copilot Readiness Assessment (CRA) platform. It handles Microsoft login, tenant onboarding, registry-driven assessment execution, Graph and PowerShell collectors, findings, recommendations, scoring, and report generation.

## What This Repository Contains

- FastAPI API under `/api/v1`
- Microsoft Entra ID login validation
- CRA JWT access and refresh tokens
- Tenant-scoped assessment data
- SQLAlchemy models and Alembic migrations
- 65-parameter CRA assessment registry
- Graph collectors and PowerShell collector runtime
- CSV evidence ingestion
- Findings, recommendations, and readiness scoring
- PDF and DOCX report generation
- Pytest test suite

The React/Vite frontend lives separately in `CRA-frontend`.

## Requirements

- Python 3.11+
- Redis 5+ for Celery and runtime events
- PowerShell 7+ (`pwsh`) for Microsoft 365 collectors
- PostgreSQL for production, or SQLite for local development
- Microsoft 365 PowerShell modules for live tenant collection
- Microsoft Entra app registration with required Graph permissions

## Laptop Transfer Summary

When moving this backend to another laptop, copy the source code and recreate local runtime state.

Copy:

```text
app/
migrations/
scripts/
tests/
.env.example
.gitignore
alembic.ini
pytest.ini
README.md
requirements.txt
```

Do not copy:

```text
.env
venv/
cra.db
tmp-routing-debug.db
artifacts/
storage/
out/
tmp/
*.log
*.docx
*.pdf
```

Create a fresh `.env` from `.env.example` on the new laptop.

## Project Structure

```text
app/
  api/v1/                     API routers
  config/assessment_registry/ Parameters, collectors, rules, recommendations
  core/                       Settings, auth, security, middleware
  db/                         SQLAlchemy models, session, repositories
  powershell/                 Domain collector scripts
  schemas/                    Pydantic schemas
  services/                   Runtime, Graph, reporting, scoring, recommendations
  tasks/                      Celery task entry points
migrations/                   Alembic migrations
scripts/                      Utility scripts
tests/                        Pytest tests
requirements.txt              Backend Python dependencies
.env.example                  Example local configuration
```

## Setup

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Or activate it on macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create local environment configuration:

```bash
cp .env.example .env
```

Update `.env` with your own values:

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `AZURE_CLIENT_ID`
- `AZURE_LOGIN_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_SECRET` when server-side Graph app access is required
- `CRA_FRONTEND_URL`
- `CORS_ORIGINS`

Never commit `.env` or tenant secrets.

## Redis And Celery

Redis is required for normal assessment execution. It is used for:

- Celery assessment jobs
- Celery result storage
- runtime assessment events
- WebSocket progress updates

Recommended local values:

```text
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False
```

Start Redis before starting the API and Celery worker:

```bash
redis-server
```

On Windows, Docker is a simple option:

```powershell
docker run --name cra-redis -p 6379:6379 -d redis:7
```

For basic local testing without Redis, set:

```text
CELERY_TASK_ALWAYS_EAGER=True
```

Use Redis for real assessments.

## Database

Run migrations:

```bash
alembic upgrade head
```

Local SQLite is supported through `.env`:

```text
DATABASE_URL=sqlite:///./cra.db
```

For production, use PostgreSQL:

```text
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

## Run Locally

Start Redis:

```bash
redis-server
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Start the Celery worker:

```bash
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

Optional Flower dashboard:

```bash
celery -A app.core.celery_app.celery_app flower
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Local Development Without Redis

For simple local testing, set this in `.env`:

```text
CELERY_TASK_ALWAYS_EAGER=True
```

This runs assessment tasks inline instead of sending them to a Celery worker.

## New Laptop Startup Order

Use separate terminals:

1. Redis

```bash
redis-server
```

2. Backend API

```bash
cd CRA-Tool
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

3. Celery worker

```bash
cd CRA-Tool
.\venv\Scripts\Activate.ps1
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

4. Frontend from the sibling `CRA-frontend` folder

```bash
npm run dev
```

## Microsoft 365 Collector Prerequisites

Install PowerShell 7 and the Microsoft 365 modules required by the collector scripts:

```powershell
pwsh ./scripts/install_m365_modules.ps1
```

Live assessment collection requires tenant admin consent and workload permissions for Microsoft Graph, Exchange Online, Teams, SharePoint Online, and Purview where applicable.

## Microsoft Entra Configuration

Required backend `.env` values:

```text
AZURE_CLIENT_ID=your-backend-or-shared-app-client-id
AZURE_LOGIN_CLIENT_ID=your-frontend-spa-client-id
AZURE_TENANT_ID=common
CRA_FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

If server-side Microsoft Graph collection uses a confidential app, also configure:

```text
AZURE_CLIENT_SECRET=your-client-secret
AZURE_CLIENT_SECRET_ID=your-secret-id
AZURE_AUTHORITY=https://login.microsoftonline.com/common
AZURE_REDIRECT_URI=http://localhost:3000/auth/callback
```

The frontend SPA redirect URI in Microsoft Entra must match:

```text
http://localhost:3000
```

## Main API Areas

| Area | Endpoint |
| --- | --- |
| Auth | `/api/v1/auth/*` |
| Tenants | `/api/v1/tenants/*` |
| Assessments | `/api/v1/assessments/*` |
| Findings | `/api/v1/assessments/{assessment_id}/findings` |
| Recommendations | `/api/v1/assessments/{assessment_id}/recommendations` |
| Reports | `/api/v1/assessments/{assessment_id}/report/*` |
| Registry | `/api/v1/registry/*` |
| Admin | `/api/v1/admin/*` |

## Assessment Runtime

The assessment engine is registry-driven. Parameter definitions, collector mappings, rules, and recommendations are loaded from:

```text
app/config/assessment_registry/parameters.json
app/config/assessment_registry/collectors.json
app/config/assessment_registry/rules.json
app/config/assessment_registry/recommendations.json
app/config/collector_manifest.json
```

The official CRA catalog contains 65 parameters across:

- Entra ID
- Exchange Online
- Microsoft Purview
- Microsoft Teams
- OneDrive for Business
- SharePoint Online

## Reports

Generated reports are written under:

```text
storage/reports/{assessment_id}/
```

Generated reports, local artifacts, local databases, logs, and tenant evidence are ignored by git.

## Tests

Run the full test suite:

```bash
pytest -q
```

Useful targeted checks:

```bash
pytest -q tests/test_phase8_reports.py
pytest -q tests/test_custom_banned_password_collector.py
pytest -q tests/test_collector_completion_certification.py
```

## Before Pushing To A New Repository

Commit source and configuration templates:

```text
app/
migrations/
scripts/
tests/
.env.example
.gitignore
alembic.ini
pytest.ini
README.md
requirements.txt
```

Do not commit local/generated files:

```text
.env
venv/
cra.db
tmp-routing-debug.db
artifacts/
storage/
out/
tmp/
*.log
*.docx
*.pdf
```

Also avoid committing tenant evidence, generated reports, Redis state, local databases, token caches, and PowerShell transcript logs.

## Frontend

The frontend is a separate React/Vite app. From `CRA-frontend`:

```bash
npm install
npm run dev
```

The backend CORS settings must include the frontend URL, usually:

```text
http://localhost:3000
```
