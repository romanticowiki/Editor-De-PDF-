# Levanta la interfaz en http://127.0.0.1:5173
$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "..\frontend"

Push-Location $frontend
try {
    if (-not (Test-Path "node_modules")) { throw "Faltan dependencias. Ejecuta primero .\scripts\setup-frontend.ps1" }
    npm run dev -- --open
}
finally { Pop-Location }
