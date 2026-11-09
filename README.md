# EPDF

EPDF es una aplicación de escritorio para Windows que permite editar, organizar y convertir
documentos PDF desde una sola interfaz. El procesamiento se realiza en el equipo del usuario con
FastAPI, React y Electron.

> **Privacidad por defecto:** ninguna herramienta envía documentos completos a servicios externos.
> Traducir PDF es la única función conectada a un tercero: transmite texto a Groq solo después de
> una confirmación explícita y únicamente cuando el usuario configura su propia clave.

## Qué ofrece

- Editor visual con texto, correcciones, dibujo, imágenes, firmas y formularios.
- Organización, división, unión, compresión, OCR, censura y PDF/A.
- Conversión entre PDF, Office, imágenes, Markdown y otros formatos compatibles.
- Aplicación instalable para Windows y alternativa local mediante Docker.

EPDF está en desarrollo activo. La conversión PDF → Word produce contenido editable, pero la
fidelidad de diseños complejos depende de la estructura del documento original; los experimentos
del laboratorio no sustituyen todavía al motor estable.

## Arrancar (Windows / PowerShell)

```powershell
.\scripts\setup-backend.ps1    # solo la primera vez
.\scripts\setup-frontend.ps1   # solo la primera vez
.\scripts\setup-ocr.ps1        # solo la primera vez: datos de idioma del OCR (~6 MB)
.\scripts\start.ps1            # motor + interfaz; abre http://127.0.0.1:5173
```

## Distribución (Windows)

Dos formas de usar la app; elige una.

**A) Docker (para usuarios técnicos)** — la app aislada en un contenedor, con LibreOffice y OCR
incluidos. Necesita **Docker Desktop**. Un solo puerto:

```powershell
docker compose up --build      # luego abre http://localhost:8000
```

La imagen compila la interfaz y la sirve desde FastAPI (mismo origen). Compose publica el puerto
exclusivamente en `127.0.0.1:8000`; no cambies esa dirección por `0.0.0.0` ni por `8000:8000` si
quieres mantener la API fuera de la red local. Docker Engine anterior a 28.0.0 tuvo una limitación
con puertos publicados en localhost que podía permitir acceso desde el mismo segmento de red; usa
una versión actual de Docker Desktop y conserva también el firewall del sistema operativo.
Para activar Traducir PDF, define `PDFEDITOR_GROQ_API_KEY` en tu entorno antes de levantarlo.

**B) App instalada (.exe, para usuarios finales)** — ventana nativa con Electron (Chromium), con el
mismo aspecto que en el navegador. El backend se congela con PyInstaller (incluye el frontend y los
datos del OCR); Electron lo arranca en un puerto libre, espera a que responda y lo cierra al salir.

```powershell
.\scripts\build-desktop.ps1     # genera el instalador en dist-desktop\installers
```

En el `.exe`, la conversión con Microsoft Office funciona porque el propio ejecutable se relanza como
worker COM; el contenedor Docker usa LibreOffice en su lugar.

## Herramientas

| Categoría | Herramienta | Motor |
|---|---|---|
| Organizar | Unir PDF | pypdf |
| Organizar | Dividir PDF (cada página, rangos, bloques) | PyMuPDF |
| Organizar | Organizar, Girar, Eliminar y Extraer páginas (editor visual) | PyMuPDF |
| Optimizar | Comprimir PDF (3 niveles) | PyMuPDF (`rewrite_images`, `garbage=4`, subset de fuentes) |
| Optimizar | PDF a PDF/A-2b | pikepdf + perfil sRGB (ver nota) |
| Convertir desde PDF | PDF a Word / Excel / PowerPoint | pdf2docx · pdfplumber + openpyxl · PyMuPDF + python-pptx |
| Convertir desde PDF | PDF a JPG / PNG (una imagen o ZIP) | PyMuPDF |
| Convertir a PDF | Word, Excel, PowerPoint, OpenOffice, RTF | Microsoft Office o LibreOffice instalados |
| Convertir a PDF | TXT, HTML, EPUB | PyMuPDF (MuPDF) |
| Convertir a PDF | JPG / PNG a PDF (respeta la rotación EXIF) | PyMuPDF + Pillow |
| Editar y proteger | OCR (capa de texto invisible) | Tesseract integrado en PyMuPDF (ver nota) |
| Editar y proteger | Traducir PDF (es · en · fr · de · ko) | Groq (servicio externo, ver nota) |
| Editar y proteger | Marca de agua · Numerar páginas | ReportLab + pypdf |
| Editar y proteger | Censurar (borrado real + limpieza de metadatos) | PyMuPDF |
| Editar y proteger | Rellenar formularios y aplanarlos | PyMuPDF |
| Para IA | Documento a Markdown | MarkItDown |
| Para IA | Markdown a PDF / Word / PowerPoint | markdown-it-py + MuPDF Story · python-docx · python-pptx |

**Office a PDF** usa el software que ya tengas: Microsoft Office (vía COM, en un subproceso aislado,
con macros desactivadas y tiempo máximo) o LibreOffice (`PDFEDITOR_LIBREOFFICE_PATH` para forzarlo).

**PDF a Word** detiene la conversión completa si pdf2docx falla en una página, para no entregar un
DOCX incompleto como si fuera correcto. «Permitir Word parcial» es un reintento manual y opcional:
puede omitir páginas problemáticas y marca la descarga con el sufijo `-parcial`.

**OCR** no necesita instalar Tesseract: solo los datos de idioma (`spa.traineddata`, `eng.traineddata`).
`scripts\setup-ocr.ps1` los descarga de `tesseract-ocr/tessdata_fast` a `backend/tessdata/`, y el `.env`
ya apunta ahí (`PDFEDITOR_TESSDATA_DIR=tessdata`). También se buscan en `TESSDATA_PREFIX` o `C:\Program Files\Tesseract-OCR\tessdata`.
Sin ellos, la herramienta aparece como «Necesita Tesseract».

**Traducir PDF** es la única herramienta que **envía texto fuera del equipo**: manda el contenido a la
API de Groq. Está desactivada salvo que pongas tu clave en `backend/.env` (`PDFEDITOR_GROQ_API_KEY`,
gratis en <https://console.groq.com/keys>); sin clave aparece como «Necesita configurar Groq». Conserva
el diseño borrando el texto original de cada bloque y reinsertando la traducción; los escaneos sin texto
deben pasar antes por OCR. Antes de enviar nada exige aceptar expresamente este tratamiento; solo se
transmite el texto necesario, no el nombre del archivo ni sus metadatos. El resto de herramientas siguen
siendo 100 % locales.

**Resistencia ante archivos maliciosos**: los formatos ZIP (docx, xlsx, pptx, epub…) se inspeccionan
antes de procesarlos y se rechazan las bombas de descompresión (tamaño ya descomprimido y ratio de
compresión, ajustables con `PDFEDITOR_MAX_ARCHIVE_UNCOMPRESSED_MB` y `PDFEDITOR_MAX_ARCHIVE_RATIO`).
El nombre que envía el navegador nunca se usa como ruta y cualquier error interno responde con un
mensaje genérico, sin trazas ni rutas.

**PDF/A**: se rechazan los PDF con fuentes sin incrustar o adjuntos, y se corrigen automáticamente
cifrado, JavaScript, metadatos XMP y perfil de color. Para certificación formal, valida el
resultado con [veraPDF](https://verapdf.org).

**Concurrencia**: PyMuPDF no admite varios hilos a la vez, así que por defecto se procesa un
documento cada vez (`PDFEDITOR_MAX_CONCURRENT_JOBS=1`); el resto espera turno.

## Estructura

```
backend/app/
├── main.py                 # create_app(): middlewares, motores y rutas
├── core/                   # config, tipos de archivo (firmas), carpetas temporales
├── api/
│   ├── router.py           # registro único de rutas
│   ├── routes/             # UN archivo por herramienta
│   ├── uploads.py          # validación y recepción de archivos (compartida)
│   ├── execution.py        # JobRunner: concurrencia, timeout y errores → HTTP
│   └── responses.py        # descarga con nombre seguro, ZIP y limpieza del temporal
├── services/               # lógica pura por herramienta (sin HTTP)
│   └── markdown_export/    # un exportador por formato
├── engines/                # programas externos (Office / LibreOffice, OCR)
├── schemas/                # modelos Pydantic de entrada/salida JSON
└── middleware/             # rate limit, tamaño de subida, cabeceras de seguridad

frontend/src/
├── tools/catalog.ts        # catálogo: añadir herramienta = una entrada
├── tools/fields.ts         # opciones reutilizables (niveles, rangos, posiciones…)
├── pages/                  # Inicio (menú central) y página de herramienta
├── components/
│   ├── tool/               # vista genérica «un archivo» y piezas comunes
│   ├── multi/              # lista ordenable de varios archivos
│   ├── pages/              # editor visual de páginas (miniaturas + arrastrar)
│   ├── form/               # rellenador de formularios
│   └── catalog/ ui/ layout/ toast/ dropzone/
├── hooks/                  # estado: trabajo, archivo, cola, análisis, tema, rutas
├── lib/                    # lógica pura con tests (campos, editor de páginas, archivos)
├── services/               # HTTP: apiClient, toolService, pages, forms, engines
└── copy/messages.ts        # todo el texto visible
```

## Añadir una herramienta (ej. «Proteger con contraseña»)

1. **Backend:** `services/protect.py` → `api/routes/protect.py` (reutiliza `receive_upload`, `JobRunner`, `file_response`) → registrarla en `api/router.py` → `tests/test_protect.py`.
2. **Frontend:** una entrada `kind: "file"` en `tools/catalog.ts`, con sus `fields` en `tools/fields.ts`. La vista, la validación, la descarga, los errores y el menú salen solos.

## Tests

```powershell
cd backend;  .\.venv\Scripts\python.exe -m pytest -q
cd frontend; npm test; npm run typecheck
# Conversión real con Office/LibreOffice (abre el programa):
$env:PDF_LOCAL_OFFICE_TESTS = "1"; .\.venv\Scripts\python.exe -m pytest tests/test_to_pdf.py -k real_engine
```

El inventario de dependencias, licencias declaradas y hallazgos de auditoría de la distribución está
en [`DEPENDENCIES_AND_LICENSES.md`](DEPENDENCIES_AND_LICENSES.md). No sustituye una revisión legal.
