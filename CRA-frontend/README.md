# CRA Frontend

React + MSAL React client for the CRA FastAPI backend.

## Requirements

- Node.js 20+
- npm
- Running CRA backend from `../CRA-Tool`
- Backend Redis and Celery worker running when starting real assessments

## Why two tokens?

| Token | Who issues it | Used for |
|-------|---------------|----------|
| **Microsoft ID token** | Entra ID | Sent once to `POST /auth/login` |
| **CRA JWT** | CRA backend | Every API call (`Authorization: Bearer`) |

MSAL handles Microsoft login in the browser. The backend never sees Microsoft passwords.

## Install & run

```bash
cd CRA-frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:3000

**Backend must be running:**

```bash
cd ../CRA-Tool
source venv/bin/activate
uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
cd ..\CRA-Tool
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

## Transfer to a New Laptop

Copy or push the source code and lock file:

```text
src/
.env.example
.gitignore
index.html
package.json
package-lock.json
README.md
TROUBLESHOOTING.md
vite.config.js
```

Do not copy generated/local files:

```text
node_modules/
dist/
.env
*.log
```

On the new laptop:

```bash
cd CRA-frontend
npm ci
cp .env.example .env
npm run dev
```

Update `.env` with the new backend URL or Microsoft app registration values when they differ from the old laptop.

Required frontend `.env` values:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_MSAL_CLIENT_ID=your-frontend-spa-client-id
VITE_MSAL_AUTHORITY=https://login.microsoftonline.com/common
VITE_MSAL_REDIRECT_URI=http://localhost:3000
```

Before testing assessments, make sure these backend services are running:

- Redis
- FastAPI backend
- Celery worker

## Azure App Registration

1. **SPA** platform redirect URI: `http://localhost:3000`
2. Enable **ID tokens** (implicit flow not required for popup; MSAL uses auth code + PKCE)
3. API permissions: `openid`, `profile`, `email`
4. Client ID must match `VITE_MSAL_CLIENT_ID` and backend `AZURE_CLIENT_ID`

## Test flow

1. Click **Login with Microsoft**
2. Complete Microsoft popup
3. Frontend sends `id_token` → backend returns CRA JWT
4. Dashboard loads profile from `GET /auth/me`
5. **Logout** clears CRA tokens and MSAL session

## Folder structure

```
src/
├── api/           # Axios client + auth API calls
├── auth/          # MSAL config & instance
├── components/    # ProtectedRoute, LoadingSpinner
├── context/       # AuthProvider (global auth state)
├── layouts/       # MainLayout with header
├── pages/         # Login, Dashboard
├── routes/        # React Router
├── services/      # Auth business helpers
└── utils/         # CRA token localStorage
```
