@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   CRA Tool — One-Command Startup
echo ============================================================
echo.

set ROOT=%~dp0
set BACKEND=%ROOT%CRA-Tool
set FRONTEND=%ROOT%CRA-frontend

REM ── Prerequisites check ─────────────────────────────────────
where redis-server >nul 2>&1 || where redis-cli >nul 2>&1
if errorlevel 1 (
    echo [WARN] redis-server not found on PATH.
    echo        Install Redis for Windows or start it manually.
    echo        Download: https://github.com/microsoftoffice/redis-windows/releases
    echo.
)

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python not found. Install Python 3.11+ and add to PATH.
    pause & exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] node not found. Install Node.js 18+ and add to PATH.
    pause & exit /b 1
)

REM ── Check .env files ─────────────────────────────────────────
if not exist "%BACKEND%\.env" (
    echo [WARN] CRA-Tool\.env not found — copying from .env.example
    copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
    echo        Edit CRA-Tool\.env and fill in your Azure credentials before proceeding.
    echo.
)

if not exist "%FRONTEND%\.env" (
    echo [WARN] CRA-frontend\.env not found — copying from .env.example
    copy "%FRONTEND%\.env.example" "%FRONTEND%\.env" >nul
    echo        Edit CRA-frontend\.env and fill in VITE_AZURE_CLIENT_ID.
    echo.
)

REM ── Check Python venv ─────────────────────────────────────────
if not exist "%BACKEND%\venv\Scripts\python.exe" (
    echo [1/5] Creating Python virtual environment...
    cd /d "%BACKEND%"
    python -m venv venv
    call "%BACKEND%\venv\Scripts\activate.bat"
    pip install -r requirements.txt
) else (
    echo [1/5] Python venv found.
)

REM ── Check node_modules ────────────────────────────────────────
if not exist "%FRONTEND%\node_modules" (
    echo [2/5] Installing frontend dependencies...
    cd /d "%FRONTEND%"
    npm install
) else (
    echo [2/5] node_modules found.
)

REM ── Start Redis ───────────────────────────────────────────────
echo [3/5] Starting Redis...
start "CRA-Redis" /min redis-server --port 6379 2>nul
if errorlevel 1 (
    echo [WARN] Could not start Redis — it may already be running.
)
timeout /t 2 /nobreak >nul

REM ── Run DB migrations ─────────────────────────────────────────
echo [4/5] Running database migrations...
cd /d "%BACKEND%"
call "%BACKEND%\venv\Scripts\activate.bat"
python -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Alembic migration failed. Check CRA-Tool/migrations/ for errors.
    pause & exit /b 1
)

REM ── Start backend ─────────────────────────────────────────────
echo [5/5] Starting services...
echo.
start "CRA-Backend" cmd /k "cd /d %BACKEND% && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

REM ── Start Celery (only if CELERY_TASK_ALWAYS_EAGER is not True) ──
findstr /i "CELERY_TASK_ALWAYS_EAGER=True" "%BACKEND%\.env" >nul 2>&1
if errorlevel 1 (
    start "CRA-Celery" cmd /k "cd /d %BACKEND% && call venv\Scripts\activate.bat && celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo"
    echo        Celery worker started.
) else (
    echo        Celery skipped (CELERY_TASK_ALWAYS_EAGER=True in .env).
)

REM ── Start frontend ────────────────────────────────────────────
start "CRA-Frontend" cmd /k "cd /d %FRONTEND% && npm run dev"

echo.
echo ============================================================
echo   All services started in separate windows.
echo.
echo   Backend:   http://localhost:8000
echo   API docs:  http://localhost:8000/docs
echo   Frontend:  http://localhost:5173
echo ============================================================
echo.
echo   Close the individual service windows to stop each service.
echo   Or press Ctrl+C here to exit this launcher.
echo.
pause
