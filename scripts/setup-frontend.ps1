# Instala las dependencias de la interfaz (solo la primera vez).
$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "..\frontend"

Push-Location $frontend
try {
    npm ci --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { throw "npm ci falló." }
    Write-Host "Interfaz lista. Arranca todo con: .\scripts\start.ps1" -ForegroundColor Green
}
finally { Pop-Location }
