# CRA Microsoft Login — Troubleshooting

## Quick checklist

| Check | Expected |
|-------|----------|
| Frontend `.env` `VITE_MSAL_CLIENT_ID` | `702eb094-c0a3-4950-bdab-ca97d2c256be` |
| Backend `.env` `AZURE_CLIENT_ID` | Same as frontend |
| Backend `AZURE_TENANT_ID` | `common` (multi-tenant) |
| Azure platform | **SPA** (not Web) |
| Redirect URI | `http://localhost:3000` |
| API permissions | `openid`, `profile`, `email`, `User.Read` (+ admin consent) |
| Backend running | http://127.0.0.1:8000/docs opens |
| Restart after `.env` change | Stop and restart `npm run dev` and uvicorn |

## Common errors

### Popup blocked

**Message:** `Login popup was blocked`

**Fix:** Browser settings → allow popups for `localhost:3000`.

### Invalid Microsoft ID token (backend 401)

**Causes:**

1. Frontend and backend **Client ID mismatch**
2. Token expired before POST to backend (retry login)
3. Wrong app registration (different tenant app)

**Fix:** Align `VITE_MSAL_CLIENT_ID` and `AZURE_CLIENT_ID`, restart both servers.

### Cannot reach CRA backend (network)

**Fix:**

```bash
cd cra-backend && source venv/bin/activate
uvicorn app.main:app --reload
```

### AADSTS50011 redirect URI mismatch

**Fix:** In Azure Portal → Authentication → SPA → add `http://localhost:3000`.

### AADSTS65001 consent required

**Fix:** Azure Portal → API permissions → Grant admin consent for `User.Read`.

### No ID token from MSAL

**Fix:** Scopes must include `openid`. App registration must expose ID tokens for SPA.

## Test flow

1. Open http://localhost:3000
2. Click **Login with Microsoft**
3. Sign in with work account
4. Dashboard shows email from `GET /auth/me`
5. Logout clears session and returns to login

## Verify backend directly

After login in browser DevTools → Network → find `POST /auth/login` → copy `id_token` from request (do not share publicly).

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"id_token":"<paste>"}'
```

Expect `access_token` and `refresh_token` in JSON.
