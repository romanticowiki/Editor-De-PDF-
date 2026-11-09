# Arranca todo: el motor local en otra ventana y la interfaz en esta.
$ErrorActionPreference = "Stop"

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-backend.ps1`""
& "$PSScriptRoot\start-frontend.ps1"
