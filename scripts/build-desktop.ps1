# Empaqueta PDF Local como app de escritorio para Windows.
#
# Orquesta los tres pasos:
#   1. Compila la interfaz de React (API en el mismo origen).
#   2. Congela el backend con PyInstaller (incluye la interfaz y los datos del OCR).
#   3. Empaqueta la ventana de Electron con electron-builder → instalador .exe.
#
# Requisitos previos: haber ejecutado setup-backend.ps1 y setup-frontend.ps1, tener Node
# instalado y (opcional) setup-ocr.ps1 para incluir el OCR. Para Mac/Linux, ejecuta la
# parte de Electron en cada sistema (electron-builder no compila para otros SO).

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$electron = Join-Path $root "electron"
$distDesktop = Join-Path $root "dist-desktop"
$python = Join-Path $backend ".venv\Scripts\python.exe"

# Este script borra recursivamente la salida anterior. Comprueba la ruta absoluta antes de hacerlo
# para que un cambio futuro en las variables no pueda ampliar por accidente el alcance del borrado.
$expectedDistDesktop = [System.IO.Path]::GetFullPath((Join-Path $root "dist-desktop"))
$actualDistDesktop = [System.IO.Path]::GetFullPath($distDesktop)
if (-not [string]::Equals($actualDistDesktop, $expectedDistDesktop, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "La ruta de salida no es segura: $actualDistDesktop"
}

if (-not (Test-Path $python)) { throw "Falta el entorno del backend. Ejecuta primero scripts\setup-backend.ps1" }

# ── 1. Interfaz ────────────────────────────────────────────────
Write-Host "[1/3] Compilando la interfaz…" -ForegroundColor Cyan
Push-Location $frontend
try {
    npm ci --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { throw "npm ci falló para el frontend." }
    npm run build   # usa frontend\.env.production (VITE_API_BASE_URL=/api/v1)
    if ($LASTEXITCODE -ne 0) { throw "El build del frontend falló." }
}
finally { Pop-Location }

# ── 2. Backend congelado ───────────────────────────────────────
Write-Host "[2/3] Congelando el backend con PyInstaller…" -ForegroundColor Cyan
# Limpieza robusta: el antivirus puede tener archivos abiertos justo tras un build. Reintenta.
if (Test-Path $distDesktop) {
    foreach ($try in 1..3) {
        try { Remove-Item $distDesktop -Recurse -Force -ErrorAction Stop; break }
        catch {
            if ($try -eq 3) { throw "No se pudo limpiar $distDesktop. Cierra el Explorador/antivirus sobre esa carpeta y reintenta." }
            Start-Sleep -Seconds 2
        }
    }
}

Push-Location $backend
try {
    # El build no modifica el entorno: setup-backend.ps1 debe haber instalado la versión declarada.
    & $python -m PyInstaller --version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falta PyInstaller. Ejecuta primero scripts\setup-backend.ps1" }

    # --onefile: un ÚNICO .exe autoextraíble. Evita el límite de 260 caracteres de ruta (MAX_PATH)
    # de Windows: en --onedir, electron-builder copia miles de archivos con rutas profundísimas
    # (pymupdf\mupdf-devel\..., tzdata\zoneinfo\...) y el empaquetado NSIS falla. Con un solo .exe
    # no hay árbol que copiar. Se extrae a %TEMP% al arrancar (primer inicio algo más lento).
    $pyArgs = @(
        "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
        "--name", "pdf-local-backend",
        "--distpath", $distDesktop,
        "--workpath", (Join-Path $distDesktop "build"),
        "--specpath", $distDesktop,
        # Rutas de origen ABSOLUTAS: con --specpath, PyInstaller resuelve las relativas contra
        # la carpeta del .spec (dist-desktop), no contra backend. En absoluto no hay ambigüedad.
        "--add-data", "$frontend\dist;frontend_dist"
    )
    # Los datos del OCR solo si existen (setup-ocr.ps1).
    $tessdata = Join-Path $backend "tessdata"
    if (Test-Path $tessdata) { $pyArgs += @("--add-data", "$tessdata;tessdata") }

    # Librerías con binarios, modelos o datos que PyInstaller no detecta por sí solo.
    # Las críticas: markitdown usa magika+onnxruntime; pdf2docx usa cv2; pdfminer necesita sus CMap;
    # uvicorn carga sus protocolos por nombre. Sin esto → ModuleNotFoundError en el .exe.
    $collectAll = @(
        "pymupdf", "pikepdf",
        "markitdown", "magika", "onnxruntime",
        "pdfplumber", "pdfminer", "pdf2docx", "cv2",
        "pptx", "docx", "reportlab", "openpyxl", "markdown_it",
        "uvicorn"
    )
    foreach ($pkg in $collectAll) { $pyArgs += @("--collect-all", $pkg) }

    # Módulos que se importan de forma indirecta (COM de Office y protocolos de uvicorn).
    $hiddenImports = @(
        "win32com", "win32com.client", "pythoncom", "pywintypes", "win32timezone",
        "httptools", "websockets"
    )
    foreach ($mod in $hiddenImports) { $pyArgs += @("--hidden-import", $mod) }

    # Módulos que NO usamos y que solo estorban:
    #  - tkinter/_tkinter arrastran Tcl/Tk y su carpeta _tcl_data\tzdata (cientos de archivos
    #    diminutos) que hace fallar el COLLECT en Windows con «directorio no vacío». No hay GUI Tk.
    #  - onnxruntime.quantization necesita el paquete `onnx` (que no usamos).
    $excludes = @("tkinter", "_tkinter", "PIL.ImageTk", "PIL.ImageQt", "onnxruntime.quantization")
    foreach ($mod in $excludes) { $pyArgs += @("--exclude-module", $mod) }

    $pyArgs += (Join-Path $backend "desktop_server.py")

    & $python @pyArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló (código $LASTEXITCODE). Revisa el log de arriba." }

    # electron-builder espera el binario en dist-desktop\backend\pdf-local-backend.exe.
    $frozenExe = Join-Path $distDesktop "pdf-local-backend.exe"
    if (-not (Test-Path $frozenExe)) { throw "PyInstaller no generó $frozenExe. Revisa el log." }
    $backendOut = Join-Path $distDesktop "backend"
    New-Item -ItemType Directory -Force $backendOut | Out-Null
    Move-Item -Force $frozenExe $backendOut
}
finally { Pop-Location }

# ── 3. Ventana de Electron ─────────────────────────────────────
Write-Host "[3/3] Empaquetando la ventana con Electron…" -ForegroundColor Cyan
Push-Location $electron
try {
    npm ci --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { throw "npm ci falló para Electron." }
    npm run dist
    if ($LASTEXITCODE -ne 0) { throw "electron-builder falló. Revisa el log de arriba." }

    # Verifica el paquete real, no solo el manifiesto: recorre los require() locales desde main.js
    # y falla el build si app.asar omitió cualquiera de esos módulos.
    $asar = Join-Path $distDesktop "installers\win-unpacked\resources\app.asar"
    $packageVerifier = Join-Path $root "scripts\verify-electron-package.js"
    node $packageVerifier $asar
    if ($LASTEXITCODE -ne 0) { throw "La verificación de app.asar falló." }
}
finally { Pop-Location }

Write-Host "Listo. El instalador esta en dist-desktop\installers" -ForegroundColor Green
