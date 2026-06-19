# Deployment

## Prerequisites

Required local tools:

- Python with a virtual environment
- Node.js and npm
- Redis if running Celery workers locally
- PowerShell
- Microsoft 365 admin access for tenant deployment and consent
- Azure app registration permissions for Microsoft login and tenant runtime collection

Backend dependencies are listed in:

- `CRA-Tool/requirements.txt`
- `CRA-Tool/pyproject.toml`

Frontend dependencies are listed in:

- `CRA-frontend/package.json`

## Environment Files

Backend:

- `CRA-Tool/.env`
- `CRA-Tool/.env.example`

Frontend:

- `CRA-frontend/.env`
- `CRA-frontend/.env.example`

## Important Frontend Auth Variables

The frontend MSAL configuration is in `CRA-frontend/src/auth/msalConfig.js`.

Important Vite variables:

- `VITE_MSAL_CLIENT_ID`
- `VITE_MSAL_AUTHORITY`

Defaults in code:

- Client ID default: `702eb094-c0a3-4950-bdab-ca97d2c256be`
- Authority default: `https://login.microsoftonline.com/common`
- Redirect URI default: `window.location.origin`

For a multi-tenant application, the authority should use `common` or another multi-tenant authority supported by the Azure app registration. The Azure redirect URI must exactly match the browser origin used by the frontend, for example:

- `http://localhost:5173`
- `http://localhost:3000`

Use the port your Vite dev server actually prints.

## Backend Setup

```powershell
cd CRA-Tool
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m alembic upgrade head
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Default backend API URL:

```text
http://localhost:8000
```

## Frontend Setup

```powershell
cd CRA-frontend
npm.cmd install
npm.cmd run dev
```

Vite will print the actual frontend URL. Use that exact origin in Azure redirect URI settings.

## Celery Worker

On Windows, use the solo pool:

```powershell
cd CRA-Tool
venv\Scripts\celery.exe -A app.core.celery_app worker --loglevel=info --pool=solo
```

Redis must be running before Celery can process background jobs.

## Tenant Add / Connect Flow

1. User signs in with Microsoft.
2. Frontend sends the Microsoft ID token to `POST /api/v1/auth/login`.
3. Backend creates or updates the local user and connected tenant.
4. Tenant deployment can be started with `POST /api/v1/tenants/deployment/start`.
5. Deployment validates app registration and permission state.
6. Admin consent is validated with `POST /api/v1/tenants/deployment/validate-consent`.
7. Permissions can be checked with `GET /api/v1/tenants/{tenant_id}/permissions`.

## Run Assessment

1. Confirm the user is logged in.
2. Confirm the tenant is connected and consented.
3. Start assessment:

```text
POST /api/v1/assessments/start
```

4. Track status through:

```text
GET /api/v1/assessments/{assessment_id}
GET /api/v1/assessments/{assessment_id}/job
GET /api/v1/assessments/{assessment_id}/events
```

5. View results:

```text
GET /api/v1/assessments/{assessment_id}/results
GET /api/v1/assessments/{assessment_id}/findings
GET /api/v1/assessments/{assessment_id}/evidence
```

6. Generate report:

```text
POST /api/v1/assessments/{assessment_id}/generate-report
```

## Ports

Common local ports:

| Component | Common Port |
|---|---:|
| Backend FastAPI | 8000 |
| Frontend Vite | 5173 or 3000 |
| Redis | 6379 |
| Celery Flower, if used | 5555 |

The frontend redirect URI is dynamic in code because it uses `window.location.origin`. Azure must contain the exact current frontend origin.

## Known Issues And Checks

- If Microsoft login fails, confirm the Azure redirect URI exactly matches the frontend URL.
- If a multi-tenant login fails, confirm the app registration supports accounts in any organizational directory and the frontend authority is multi-tenant.
- If assessment jobs do not run, confirm Redis is running and the Celery worker is started.
- On Windows, Celery should use `--pool=solo`.
- If a Graph collector fails, check app permissions, admin consent, and the tenant deployment status.
- If a PowerShell collector opens an interactive login prompt, check the service-specific PowerShell auth path.
- If report generation fails, verify the assessment has persisted findings and artifacts before debugging the renderer.
- If a generated PDF is wrong, verify the DOCX first because the current report flow builds DOCX before PDF.
