# CRA Tool — Copilot Readiness Assessment

Automated platform that audits a Microsoft 365 tenant against 65 security and productivity parameters and produces a scored **Copilot Readiness Report** with prioritised remediation steps.

---

## What it does

The CRA Tool connects to a customer's Microsoft 365 tenant using app-only Graph API calls (and optionally delegated PowerShell sessions), collects real-time configuration data across Entra ID, Security, Compliance, Collaboration, and Licensing domains, applies a weighted scoring model, and generates a PDF / Word report that tells the customer whether they are ready to deploy Microsoft 365 Copilot — and what must be fixed first.

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│  React / Vite  Frontend  (port 3000)               │
│  MSAL SPA auth  →  Axios  →  WebSocket progress   │
└──────────────────────┬─────────────────────────────┘
                       │ HTTP / WS
┌──────────────────────▼─────────────────────────────┐
│  FastAPI  Backend  (port 8000)                     │
│  ┌───────────────┐  ┌───────────────────────────┐  │
│  │  REST API     │  │  Celery Task (async)      │  │
│  │  /api/v1      │  │  assessment_tasks.py      │  │
│  └───────────────┘  └──────────┬────────────────┘  │
│                                │                   │
│  ┌─────────────────────────────▼──────────────┐   │
│  │  Assessment Engine                          │   │
│  │  Graph Collector  (9 params, app-only)     │   │
│  │  PowerShell Collector  (56 params)         │   │
│  │  Findings Engine  →  Scoring Engine        │   │
│  │  Report Generator  (PDF + DOCX)            │   │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  SQLite / PostgreSQL        Redis (Celery broker)  │
└────────────────────────────────────────────────────┘
                       │
          Microsoft 365 tenant (Graph API + PowerShell)
```

**Key libraries:** FastAPI, SQLAlchemy (async), Celery, MSAL, Microsoft Graph SDK, ReportLab (PDF), python-docx, React 18, Vite, Tailwind CSS, Recharts.

---

## Quick Start

### Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.11 | `python --version` |
| Node.js | 18 | `node --version` |
| Redis | 7 | Required even with `CELERY_TASK_ALWAYS_EAGER=True` for WebSocket pub/sub |
| PowerShell | 7 (pwsh) | For Exchange / Teams / Purview collectors |
| PS module: ExchangeOnlineManagement | 3.x | `Install-Module ExchangeOnlineManagement` |
| PS module: MicrosoftTeams | 6.x | `Install-Module MicrosoftTeams` |
| Azure App Registration | — | See Azure Setup below |

### Setup

```bash
# 1 — Clone and enter repo
git clone <repo-url> && cd CRA

# 2 — Backend
cd CRA-Tool
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / Mac
pip install -r requirements.txt
cp .env.example .env           # then fill in .env

# 3 — Initialise database
python -m alembic upgrade head

# 4 — Frontend
cd ../CRA-frontend
npm install
cp .env.example .env

# 5 — Start services (see start.bat / start.sh in project root)
```

### One-command start (Windows)

```bat
start.bat
```

### One-command start (Linux / Mac)

```bash
bash start.sh
```

Both scripts start Redis, the FastAPI backend, Celery worker, and the React dev server.

---

## Azure App Registration

1. **New registration** — any name, supported account types: *Accounts in any organizational directory (Any Azure AD directory — Multitenant)*.
2. **Authentication** → Add a platform → **Single-page application** → Redirect URI: `http://localhost:3000`.
3. **API permissions** → Microsoft Graph → Application permissions → add all permissions below → Grant admin consent.
4. **Certificates & secrets** → New client secret → copy value to `AZURE_CLIENT_SECRET`.
5. Copy the **Application (client) ID** → `AZURE_CLIENT_ID`.

### Required Graph Permissions

| Permission | Type | Used for |
|---|---|---|
| `User.Read.All` | Application | User count, MFA status, guest users |
| `Policy.Read.All` | Application | Conditional Access, SSPR, password policy |
| `AuditLog.Read.All` | Application | Audit log retention, sign-in logs |
| `SecurityEvents.Read.All` | Application | Secure Score |
| `Reports.Read.All` | Application | SharePoint / Teams usage reports |
| `Directory.Read.All` | Application | Tenant settings, admin centre access |
| `IdentityRiskEvent.Read.All` | Application | Risky sign-in policies |

---

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

### Backend (`CRA-Tool/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | JWT signing key (`openssl rand -hex 32`) |
| `DATABASE_URL` | Yes | `sqlite:///./cra.db` | SQLAlchemy URL |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection |
| `CELERY_TASK_ALWAYS_EAGER` | No | `False` | `True` = no Celery worker needed (dev mode) |
| `AZURE_CLIENT_ID` | Yes | — | App registration client ID |
| `AZURE_CLIENT_SECRET` | Yes | — | App registration secret |
| `AZURE_TENANT_ID` | No | `common` | `common` for multi-tenant |
| `AZURE_LOGIN_CLIENT_ID` | No | = `AZURE_CLIENT_ID` | Frontend SPA client ID if different |
| `ORGANIZATION_NAME` | No | — | Shown on generated reports |
| `CRA_EXCHANGE_AUTH_MODE` | No | `skip` | `skip` / `device` / `token` |
| `CRA_TEAMS_AUTH_MODE` | No | `skip` | `skip` / `device` / `token` |
| `CRA_PURVIEW_AUTH_MODE` | No | `skip` | `skip` / `device` / `token` |

### Frontend (`CRA-frontend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Backend URL |
| `VITE_AZURE_CLIENT_ID` | Yes | — | MSAL client ID (same as backend) |
| `VITE_AZURE_TENANT_ID` | No | `common` | Azure tenant ID |
| `VITE_AZURE_REDIRECT_URI` | No | `http://localhost:3000` | Must match Azure portal |

---

## Assessment Coverage

65 parameters across 5 scored domains.

### Entra ID / Identity Access — 19 parameters

| Parameter | Method | Severity | Copilot Blocker |
|---|---|---|---|
| Users without MFA | PowerShell | Critical | No |
| CAP policies for risky sign-ins | PowerShell | Critical | No |
| Conditional Access Policies (Exclusion) | PowerShell | High | No |
| Global Administrator Accounts | PowerShell | High | No |
| Authentication methods enabled | PowerShell | High | No |
| Emergency Access Accounts | Graph | High | No |
| Devices without Compliance Policies | PowerShell | High | No |
| User Consent For Applications | Graph | Medium | No |
| Self-Service Password Reset Auth Method | Graph | Medium | No |
| Restricted Access to Entra Admin Centre | Graph | Medium | No |
| Admin Consent Workflow | PowerShell | Medium | No |
| Guest Invite Settings | PowerShell | Medium | No |
| Tenant Collaboration Invitations | PowerShell | Medium | No |
| Entra – Third Party App Integrations | Graph | Medium | No |
| Account Enabled | PowerShell | Medium | No |
| Custom Banned Password List | Graph | Low | No |
| Entra – Tenant Creation By Non-Admin | PowerShell | Low | No |
| Guest Users Count | PowerShell | Low | No |
| User Information | PowerShell | Info | No |

### Security — 3 parameters

| Parameter | Method | Severity |
|---|---|---|
| Permission Settings for Anyone links | PowerShell | High |
| Auto-expiration policy for M365 Groups | PowerShell | Medium |
| Expiration Policy for Anyone links | PowerShell | Medium |

### Compliance / Purview — 8 parameters

| Parameter | Method | Severity |
|---|---|---|
| Audit Logs Enabled | PowerShell | Critical |
| Secure Score Percentage | Graph | High |
| DLP Rules Configured | PowerShell | High |
| Information Protection Labels Applied | PowerShell | High |
| Sensitivity Labels Configured and Applied | PowerShell | High |
| Audit Log Retention Duration | Graph | High |
| Sensitivity Labels Applied to Teams | PowerShell | Medium |
| Compliance Score Overview | Graph | Info |

### Collaboration — Teams, SharePoint, OneDrive, Exchange — 31 parameters

| Parameter | Method | Severity | Copilot Blocker |
|---|---|---|---|
| Copilot Integration Enabled | PowerShell | Critical | **Yes** |
| Teams – Lobby Bypass | PowerShell | High | No |
| Teams with External Guest as Owner | PowerShell | High | No |
| External Sharing Settings | PowerShell | High | No |
| Sharing Settings (External / Internal) | PowerShell | High | No |
| SharePoint – Modern Authentication | PowerShell | High | No |
| Full Calendar Schedules Shareable Externally | PowerShell | High | No |
| Active / Inactive Teams | PowerShell | High | No |
| Meeting Transcription Enabled | PowerShell | High | No |
| Meeting Policies Configuration | PowerShell | Medium | No |
| Meeting Recording Retention Policies | PowerShell | Medium | No |
| Teams – Meeting Chat | PowerShell | Medium | No |
| Teams – File Storage Option | PowerShell | Medium | No |
| Teams with External Users | PowerShell | Medium | No |
| Active/Inactive Teams Users | PowerShell | Medium | No |
| Orphan Teams | PowerShell | Medium | No |
| Minimum Number of Owners | PowerShell | Medium | No |
| Third-party Apps Allowed | PowerShell | Medium | No |
| Guest Access Enabled / Disabled | PowerShell | Medium | No |
| SharePoint & OneDrive Guest Access Expiry | PowerShell | Medium | No |
| Getting All Sites with Sensitivity Keywords | PowerShell | Medium | No |
| Active Sites Count | Graph | Medium | No |
| Active Users on SharePoint | PowerShell | Medium | No |
| Total Active Users on OneDrive | PowerShell | Medium | No |
| Mailboxes Status (Active / Inactive) | PowerShell | Medium | No |
| External Storage Providers in OWA | PowerShell | Medium | No |
| Teams – Channel Email Addresses | PowerShell | Low | No |
| Storage Quota Consumption | PowerShell | Low | No |
| Mailbox Storage Usage | PowerShell | Low | No |
| Number of Emails Read / Received | PowerShell | Info | No |
| Number of Emails Sent | PowerShell | Info | No |

### Governance + Other — 4 parameters

| Parameter | Domain | Method | Severity |
|---|---|---|---|
| Customer Lockbox | Unclassified | PowerShell | High |
| Days to Retain Deleted User's OneDrive | Governance | PowerShell | Medium |
| Site Ownership Policies | Governance | PowerShell | Medium |
| Inactive Site Policies | Best Practice | PowerShell | Low |

---

## Enabling Exchange / Teams / Purview

By default all three service collectors are set to `skip` — they are omitted silently and their domain scores show **N/A** in results. This prevents browser login popups during automated runs.

To collect real data from these services:

### Device Code Flow (recommended)

Run the following in a separate PowerShell 7 terminal **before** starting the backend, then leave the session open:

```powershell
Connect-ExchangeOnline -Device -ShowBanner:$false
Connect-MicrosoftTeams -UseDeviceAuthentication
```

Then in `.env`:

```env
CRA_EXCHANGE_AUTH_MODE=device
CRA_TEAMS_AUTH_MODE=device
CRA_PURVIEW_AUTH_MODE=device
```

Restart the backend. Collectors will reuse the authenticated session.

### Install required PowerShell modules

```powershell
# Run once as Administrator
Install-Module ExchangeOnlineManagement -Scope CurrentUser -Force
Install-Module MicrosoftTeams -Scope CurrentUser -Force
Install-Module Microsoft.Online.SharePoint.PowerShell -Scope CurrentUser -Force
Install-Module PnP.PowerShell -Scope CurrentUser -Force
```

> If you see `AADSTS500014`, the tenant's Exchange Online service principal is disabled. Contact the Exchange admin or keep `CRA_EXCHANGE_AUTH_MODE=skip`.

---

## Scoring

Scores are calculated using a **weighted domain average with per-parameter severity deductions** model.

### Domain Weights

| Domain | Display Name | Weight |
|---|---|---|
| `collaboration` | Teams / SharePoint / OneDrive / Exchange | 43.4% |
| `identity_access` | Entra ID | 28.9% |
| `compliance` | Purview | 11.8% |
| `security` | Security | 7.9% |
| `governance` | Governance | 4.0% |
| `best_practice` | Best Practices | 1.3% |
| `unclassified` | Other | 2.6% |

### Severity Deductions (per failing parameter)

| Severity | Full Fail | Warning (×0.45) |
|---|---|---|
| Critical | −25 pts | −11.25 pts |
| High | −15 pts | −6.75 pts |
| Medium | −8 pts | −3.6 pts |
| Low | −3 pts | −1.35 pts |
| Info | −1 pt | −0.45 pts |

Each domain starts at 100. Deductions are applied per failing finding, scaled by the parameter's `scoring_weight`. All findings within a domain are averaged, then combined using domain weights.

**Blocker cap:** if any `copilot_blocker: true` parameter fails with a critical finding, the overall score is capped at 59/100.

### Readiness Tiers

| Score | Tier | Meaning |
|---|---|---|
| ≥ 85 | Ready | Safe to deploy Copilot |
| 70 – 84 | Mostly Ready | Minor remediation recommended |
| 50 – 69 | Partially Ready | Remediation required before deployment |
| < 50 | Not Ready | Significant issues must be resolved |

---

## API Reference

Interactive API docs: `http://localhost:8000/docs`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/microsoft` | Exchange Microsoft ID token for CRA JWT |
| `GET` | `/api/v1/dashboard/stats` | Aggregate stats for the dashboard cards |
| `GET` | `/api/v1/assessments` | Paginated assessment list |
| `POST` | `/api/v1/assessments/start` | Start a new assessment |
| `GET` | `/api/v1/assessments/{id}/results` | Full results with findings and recommendations |
| `DELETE` | `/api/v1/assessments/{id}` | Soft-delete an assessment |
| `GET` | `/api/v1/assessments/{id}/report` | Download PDF or DOCX report |
| `WS` | `/ws/assessments/{id}` | Real-time progress updates |

---

## Development Tips

```bash
# Backend with auto-reload
cd CRA-Tool && uvicorn app.main:app --reload --port 8000

# Frontend dev server
cd CRA-frontend && npm run dev

# Skip Celery worker (tasks run synchronously in dev)
# .env:  CELERY_TASK_ALWAYS_EAGER=True

# Interactive API docs
open http://localhost:8000/docs
```
