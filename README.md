# CRA Project Transfer Guide

This workspace contains the Microsoft 365 Copilot Readiness Assessment platform.

- `CRA-Tool`: FastAPI backend, database migrations, Celery runtime, Redis integration, Microsoft Graph collectors, PowerShell collectors, scoring, recommendations, and report generation.
- `CRA-frontend`: React/Vite frontend with Microsoft MSAL login and dashboard UI.

Use this guide when moving the tool from one laptop to another or pushing it to a new Git repository.

## What To Copy

Copy or push the source code only.

Keep:

```text
CRA-Tool/
CRA-frontend/
README.md
```

Do not copy local runtime files:

```text
CRA-Tool/venv/
CRA-Tool/.env
CRA-Tool/cra.db
CRA-Tool/tmp-routing-debug.db
CRA-Tool/artifacts/
CRA-Tool/storage/
CRA-Tool/out/
CRA-Tool/tmp/
CRA-Tool/*.log
CRA-Tool/*.docx
CRA-Tool/*.pdf
CRA-frontend/node_modules/
CRA-frontend/dist/
CRA-frontend/.env
CRA-frontend/*.log
```

Important: `.env` files contain tenant/app secrets and must be recreated from `.env.example` on the new laptop.

## Required Software On New Laptop

Install these before running the project:

- Git
- Python 3.11 or newer
- Node.js 20 or newer
- npm
- Redis 5 or newer
- PowerShell 7 or newer, command name `pwsh`
- Microsoft 365 PowerShell modules, installed by the backend script
- PostgreSQL for production, or SQLite for local development

## Redis Requirement

Redis is used by the backend for:

- Celery assessment job queue
- Celery result backend
- Runtime event fanout
- WebSocket assessment progress events

Default local Redis URL:

```text
redis://localhost:6379/0
```

Start Redis before running normal assessments.

Linux/macOS:

```bash
redis-server
```

Windows options:

- Use Docker Desktop:

```powershell
docker run --name cra-redis -p 6379:6379 -d redis:7
```

- Or use WSL and run:

```bash
sudo apt update
sudo apt install redis-server
redis-server
```

If Redis is not available and you only want basic local testing, set this in `CRA-Tool/.env`:

```text
CELERY_TASK_ALWAYS_EAGER=True
```

For real background assessment execution, use Redis and keep:

```text
CELERY_TASK_ALWAYS_EAGER=False
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Backend Setup

From the new laptop:

```bash
cd CRA-Tool
python -m venv venv
```

Activate the virtual environment.

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install Python dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create local environment config:

```bash
cp .env.example .env
```

On Windows PowerShell, if `cp` is unavailable:

```powershell
Copy-Item .env.example .env
```

Update `CRA-Tool/.env`:

```text
SECRET_KEY=generate-a-new-long-random-value
DATABASE_URL=sqlite:///./cra.db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
AZURE_CLIENT_ID=your-backend-or-shared-entra-app-client-id
AZURE_LOGIN_CLIENT_ID=your-frontend-spa-client-id
AZURE_TENANT_ID=common
CRA_FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

If server-side Microsoft Graph collection uses a confidential app, also set:

```text
AZURE_CLIENT_SECRET=your-client-secret
AZURE_CLIENT_SECRET_ID=your-secret-id
AZURE_AUTHORITY=https://login.microsoftonline.com/common
AZURE_REDIRECT_URI=http://localhost:3000/auth/callback
```

Run database migrations:

```bash
alembic upgrade head
```

Install Microsoft 365 PowerShell modules:

```powershell
pwsh ./scripts/install_m365_modules.ps1
```

Start the backend API:

```bash
uvicorn app.main:app --reload
```

Start the Celery worker in a second terminal:

```bash
cd CRA-Tool
.\venv\Scripts\Activate.ps1
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

On macOS/Linux:

```bash
cd CRA-Tool
source venv/bin/activate
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

Optional Flower dashboard:

```bash
celery -A app.core.celery_app.celery_app flower
```

Backend URLs:

- API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`

## Frontend Setup

From a new terminal:

```bash
cd CRA-frontend
npm ci
```

Create local frontend env:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Update `CRA-frontend/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_MSAL_CLIENT_ID=your-frontend-spa-client-id
VITE_MSAL_AUTHORITY=https://login.microsoftonline.com/common
VITE_MSAL_REDIRECT_URI=http://localhost:3000
```

Start frontend:

```bash
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

## Microsoft Entra App Registration Checklist

In Azure Portal / Microsoft Entra admin center:

1. Create or reuse a SPA app registration for the frontend login.
2. Add SPA redirect URI:

```text
http://localhost:3000
```

3. Set frontend `.env` `VITE_MSAL_CLIENT_ID` to the SPA client ID.
4. Set backend `.env` `AZURE_LOGIN_CLIENT_ID` to the same SPA client ID.
5. If using server-side Graph collection, configure backend confidential app credentials and admin consent.
6. Confirm required Microsoft Graph application permissions are granted by an administrator.
7. Confirm tenant admin consent is completed before running live assessments.

## Normal Startup Order

Use four terminals:

1. Redis (Docker — recommended on Windows)

```powershell
docker run -d -p 6379:6379 --name redis redis:latest
```

Or via WSL:

```bash
sudo apt install redis-server && redis-server
```

2. Backend API (runs migrations then starts FastAPI on port 8000)

```powershell
cd CRA-Tool
.\start.ps1
```

`start.ps1` automatically runs `alembic upgrade head` then starts the server.
API docs: `http://localhost:8000/docs`

3. Celery worker (required for background assessment execution)

```powershell
cd CRA-Tool
venv\Scripts\python -m celery -A app.tasks.assessment_tasks worker --loglevel=info --pool=solo
```

> `--pool=solo` is required on Windows.

4. Frontend

```powershell
cd CRA-frontend
npm run dev
```

Frontend: `http://localhost:3000`

## Validation After Transfer

Backend:

```bash
cd CRA-Tool
pytest -q
alembic upgrade head
```

Frontend:

```bash
cd CRA-frontend
npm run build
```

Login validation:

1. Open `http://localhost:3000`.
2. Login with Microsoft.
3. Confirm backend returns CRA JWT.
4. Confirm dashboard loads.
5. Start a fresh assessment only after Redis, Celery worker, backend API, and frontend are all running.

## Common Issues

### Backend starts but assessment does not run

Check Redis and Celery:

```powershell
docker run -d -p 6379:6379 --name redis redis:latest
venv\Scripts\python -m celery -A app.tasks.assessment_tasks worker --loglevel=info --pool=solo
```

Confirm `.env`:

```text
CELERY_TASK_ALWAYS_EAGER=False
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Microsoft login fails

Check:

- `CRA-frontend/.env` `VITE_MSAL_CLIENT_ID`
- `CRA-frontend/.env` `VITE_MSAL_REDIRECT_URI`
- `CRA-Tool/.env` `AZURE_LOGIN_CLIENT_ID`
- Entra SPA redirect URI is exactly `http://localhost:3000`
- Backend `CORS_ORIGINS` includes `http://localhost:3000`

### PowerShell collectors fail

Check:

- PowerShell 7 is installed: `pwsh --version`
- Microsoft 365 modules are installed:

```powershell
pwsh ./scripts/install_m365_modules.ps1
```

- Tenant admin consent and workload permissions are completed.

### Reports are missing

Check:

- `CRA_WORD_TEMPLATE_PATH` points to an existing template file.
- `storage/` is writable locally.
- Assessment completed before generating the report.

## Git Push Checklist

Before pushing to a new repository:

```bash
git status
```

Make sure these are not staged:

```text
.env
venv/
cra.db
artifacts/
storage/
out/
tmp/
node_modules/
dist/
*.log
*.docx
*.pdf
```

Make sure these are included:

```text
README.md
CRA-Tool/.gitignore
CRA-Tool/.env.example
CRA-Tool/requirements.txt
CRA-Tool/alembic.ini
CRA-Tool/pytest.ini
CRA-Tool/app/
CRA-Tool/migrations/
CRA-Tool/scripts/
CRA-Tool/tests/
CRA-frontend/.gitignore
CRA-frontend/.env.example
CRA-frontend/package.json
CRA-frontend/package-lock.json
CRA-frontend/src/
CRA-frontend/index.html
CRA-frontend/vite.config.js
```
