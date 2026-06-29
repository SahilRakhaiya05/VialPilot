# Restart VialPilot — frees port 7860 or uses next free port
Set-Location $PSScriptRoot\..

function Test-PortFree([int]$Port) {
    return -not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

# Try to stop python processes started from this project folder
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*cerebras*app.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 2

$port = 7860
if (-not (Test-PortFree $port)) {
    Write-Host "Port 7860 still in use (close old terminal with Ctrl+C)" -ForegroundColor Yellow
    $port = 7861
    Write-Host "Starting on port $port instead..." -ForegroundColor Yellow
}

$env:APP_MODE = "production"
$env:ENABLE_PIPELINE_ANALYZER = "false"
$env:PORT = "$port"

Write-Host "Starting VialPilot on http://127.0.0.1:$port" -ForegroundColor Green
Write-Host "Dashboard:       http://127.0.0.1:$port/dashboard" -ForegroundColor Green
Write-Host "Robot Simulator: http://127.0.0.1:$port/simulator" -ForegroundColor Green
.\.venv\Scripts\python app.py