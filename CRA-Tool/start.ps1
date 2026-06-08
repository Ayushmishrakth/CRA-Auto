#!/usr/bin/env pwsh
# CRA Backend Startup Script (Windows / PowerShell)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Python = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Virtual environment not found at venv\. Run: python -m venv venv && venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "=== CRA Backend Startup ===" -ForegroundColor Cyan

# 1. Run DB migrations
Write-Host "`n[1/2] Running Alembic migrations..." -ForegroundColor Yellow
& $Python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Error "Alembic migration failed. Check migrations/ for errors."
    exit 1
}
Write-Host "  DB up to date." -ForegroundColor Green

# 2. Start FastAPI
Write-Host "`n[2/2] Starting FastAPI server on http://0.0.0.0:8000 ..." -ForegroundColor Yellow
Write-Host "  Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop.`n" -ForegroundColor Cyan

& $Python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
