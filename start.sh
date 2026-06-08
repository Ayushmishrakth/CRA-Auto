#!/usr/bin/env bash
# CRA Tool — One-Command Startup (Linux / Mac)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/CRA-Tool"
FRONTEND="$ROOT/CRA-frontend"

echo "============================================================"
echo "  CRA Tool — One-Command Startup"
echo "============================================================"
echo ""

# ── Prerequisites ─────────────────────────────────────────────
for cmd in python3 node npm redis-server; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "[ERROR] '$cmd' not found. Install it and re-run."
        exit 1
    fi
done

# ── .env files ────────────────────────────────────────────────
if [ ! -f "$BACKEND/.env" ]; then
    echo "[WARN] CRA-Tool/.env not found — copying from .env.example"
    cp "$BACKEND/.env.example" "$BACKEND/.env"
    echo "       Edit CRA-Tool/.env and fill in your Azure credentials."
    echo ""
fi

if [ ! -f "$FRONTEND/.env" ]; then
    echo "[WARN] CRA-frontend/.env not found — copying from .env.example"
    cp "$FRONTEND/.env.example" "$FRONTEND/.env"
    echo "       Edit CRA-frontend/.env and fill in VITE_AZURE_CLIENT_ID."
    echo ""
fi

# ── Python venv ───────────────────────────────────────────────
if [ ! -f "$BACKEND/venv/bin/python" ]; then
    echo "[1/5] Creating Python virtual environment..."
    cd "$BACKEND"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "[1/5] Python venv found."
    source "$BACKEND/venv/bin/activate"
fi

# ── node_modules ──────────────────────────────────────────────
if [ ! -d "$FRONTEND/node_modules" ]; then
    echo "[2/5] Installing frontend dependencies..."
    cd "$FRONTEND" && npm install
fi
echo "[2/5] node_modules found."

# ── Redis ─────────────────────────────────────────────────────
echo "[3/5] Starting Redis..."
if ! pgrep -x redis-server &>/dev/null; then
    redis-server --daemonize yes --port 6379 --logfile /tmp/cra-redis.log
    sleep 1
    echo "       Redis started (log: /tmp/cra-redis.log)"
else
    echo "       Redis already running."
fi

# ── DB migrations ─────────────────────────────────────────────
echo "[4/5] Running database migrations..."
cd "$BACKEND"
python -m alembic upgrade head

# ── Backend ───────────────────────────────────────────────────
echo "[5/5] Starting services..."
echo ""

cd "$BACKEND"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "       Backend PID $BACKEND_PID — http://localhost:8000"
sleep 2

# ── Celery (skip if CELERY_TASK_ALWAYS_EAGER=True) ────────────
if grep -qi "CELERY_TASK_ALWAYS_EAGER=True" "$BACKEND/.env" 2>/dev/null; then
    echo "       Celery skipped (CELERY_TASK_ALWAYS_EAGER=True in .env)"
else
    celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=prefork &
    CELERY_PID=$!
    echo "       Celery PID $CELERY_PID"
fi

# ── Frontend ──────────────────────────────────────────────────
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!
echo "       Frontend PID $FRONTEND_PID — http://localhost:5173"

echo ""
echo "============================================================"
echo "  All services running."
echo ""
echo "  Backend:   http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo "  Frontend:  http://localhost:5173"
echo ""
echo "  Press Ctrl+C to stop all services."
echo "============================================================"
echo ""

# ── Cleanup on exit ───────────────────────────────────────────
cleanup() {
    echo ""
    echo "Stopping services..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "${CELERY_PID:-}" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    redis-cli shutdown nosave 2>/dev/null || true
    echo "Done."
}

trap cleanup INT TERM
wait
