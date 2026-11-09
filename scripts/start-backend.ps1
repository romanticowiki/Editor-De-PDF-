# Levanta la API local en http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "..\backend"

Push-Location $backend
try {
    if (-not (Test-Path ".venv")) { throw "Falta el entorno. Ejecuta primero .\scripts\setup-backend.ps1" }
    & ".\.venv\Scripts\python.exe" run.py
}
finally { Pop-Location }
