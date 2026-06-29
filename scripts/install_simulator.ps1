# VialPilot — install robot simulator (Windows-safe)
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot\..

$pip = ".\.venv\Scripts\pip"
$python = ".\.venv\Scripts\python"

Write-Host "=== VialPilot Robot Simulator Install ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "Creating venv..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "[1/3] Core app dependencies..." -ForegroundColor Cyan
& $pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: requirements.txt had issues" -ForegroundColor Yellow }

Write-Host "[2/3] Simulator dependencies..." -ForegroundColor Cyan
& $pip install -r requirements-robot-lite.txt
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: some robot deps failed" -ForegroundColor Yellow }

Write-Host "[3/3] Verifying software robot..." -ForegroundColor Cyan
& $python scripts\verify_simulator.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS - VialPilot is ready!" -ForegroundColor Green
    Write-Host "  python app.py" -ForegroundColor Green
    Write-Host "  Dashboard:  http://127.0.0.1:7860/dashboard" -ForegroundColor Green
    Write-Host "  Simulator:  http://127.0.0.1:7860/simulator" -ForegroundColor Green
} else {
    Write-Host "Verification failed - run: pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}