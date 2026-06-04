# CRA Project Transfer Guide

This folder contains two separate apps:

- `CRA-Tool`: FastAPI backend, database migrations, Celery runtime, PowerShell collectors, and reporting.
- `CRA-frontend`: Vite/React frontend with MSAL login.

## What to Move

Move the source folders and lock/setup files. Do not move local dependencies, secrets, generated reports, caches, or databases.

Keep:

```text
CRA-Tool/
CRA-frontend/
```

Skip:

```text
CRA-Tool/venv/
CRA-Tool/.env
CRA-Tool/cra.db
CRA-Tool/artifacts/
CRA-Tool/storage/
CRA-frontend/node_modules/
CRA-frontend/dist/
CRA-frontend/.env
```

## New Laptop Setup

Backend:

```bash
cd CRA-Tool
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd CRA-frontend
npm ci
cp .env.example .env
npm run dev
```

Windows PowerShell activation for the backend:

```powershell
cd CRA-Tool
.\venv\Scripts\Activate.ps1
```

Before live Microsoft 365 collection, install PowerShell 7 and run:

```powershell
cd CRA-Tool
pwsh .\scripts\install_m365_modules.ps1
```

Local URLs:

- Frontend: http://localhost:3000
- Backend API: http://127.0.0.1:8000
- Backend docs: http://127.0.0.1:8000/docs
