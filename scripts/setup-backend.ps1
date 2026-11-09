# Crea el entorno virtual e instala dependencias (solo la primera vez).
$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "..\backend"

Push-Location $backend
try {
    if (-not (Test-Path ".venv")) { python -m venv .venv }
    & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
    if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
    Write-Host "Backend listo. Arrancalo con: .\scripts\start-backend.ps1" -ForegroundColor Green
}
finally { Pop-Location }
