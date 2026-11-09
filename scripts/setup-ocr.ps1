# Descarga los datos de idioma del OCR (español e inglés) del repositorio oficial de Tesseract.
# Solo la primera vez. Después reinicia el motor para que los detecte.
$ErrorActionPreference = "Stop"
$target = Join-Path $PSScriptRoot "..\backend\tessdata"
New-Item -ItemType Directory -Force $target | Out-Null

foreach ($lang in "spa", "eng") {
    $file = Join-Path $target "$lang.traineddata"
    if (Test-Path $file) {
        Write-Host "$lang.traineddata ya estaba descargado."
        continue
    }
    $url = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/$lang.traineddata"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $file
    Write-Host "$lang.traineddata descargado."
}

Write-Host "OCR listo. Reinicia el motor con .\scripts\start.ps1" -ForegroundColor Green
