# Dependencias, licencias y revisión de distribución

Inventario de Fase 0, generado el 7 de noviembre de 2026 desde los metadatos instalados y los
`package-lock.json` actuales. Es información técnica para preparar una revisión de distribución;
**no constituye asesoría ni una declaración de cumplimiento legal**.

## Componentes principales

| Componente | Versión observada | Licencia declarada en metadatos | Uso |
|---|---:|---|---|
| PyMuPDF / MuPDF | 1.28.2 | GNU AGPL 3.0 o licencia comercial de Artifex | Edición, renderizado, OCR y conversiones PDF |
| pdf2docx | 0.5.13 | MIT | PDF a Word |
| pypdf | 6.18.1 | BSD-3-Clause | Unión y superposición de PDF |
| pikepdf | 10.13.0.post1 | MPL-2.0 | PDF/A y saneamiento estructural |
| pdfplumber | 0.11.10 | No indicada en el metadato instalado | PDF a Excel; requiere verificación manual |
| Pillow | 12.3.0 | MIT-CMU | Imágenes y orientación EXIF |
| ReportLab | 5.0.1 | BSD; consultar `license.txt` del paquete | Marcas de agua y numeración |
| FastAPI | 0.141.1 | MIT | API local |
| Uvicorn | 0.53.0 | BSD-3-Clause | Servidor ASGI |
| Pydantic | 2.13.5 | MIT | Validación de configuración y payloads |
| python-multipart | 0.0.32 | Apache-2.0 | Subidas multipart |
| python-docx | 1.2.0 | MIT | DOCX y exportación Markdown |
| python-pptx | 1.0.2 | MIT | PowerPoint |
| openpyxl | 3.1.5 | MIT | Excel |
| MarkItDown | 0.1.7 | MIT | Documento a Markdown |
| markdown-it-py | 4.2.0 | No indicada en el metadato instalado | Parseo Markdown; requiere verificación manual |
| pywin32 | 312 | PSF | Automatización de Microsoft Office |
| PyInstaller | 6.22.3 | GPL-2.0-or-later con excepción de distribución | Backend congelado |
| React / React DOM | 19.3.0 | MIT | Interfaz |
| Motion | 13.3.0 | MIT | Animaciones |
| dnd-kit core | 6.3.1 | MIT | Arrastrar y ordenar |
| Lucide React | 1.46.0 | ISC | Iconos |
| Vite | 8.3.0 | MIT | Build frontend |
| TypeScript | 7.0.2 | Apache-2.0 | Tipado y compilación |
| Tailwind CSS | 4.3.3 | MIT | Estilos |
| Electron | 44.10.2 | MIT | Contenedor de escritorio |
| electron-builder | 26.18.0 | MIT | Instalador NSIS |

## Motores y servicios externos

- **Tesseract OCR:** se distribuye bajo Apache-2.0. El ejecutable incorpora datos de idioma cuando
  existen en `backend/tessdata`; deben conservarse sus avisos correspondientes.
- **LibreOffice:** la imagen Docker instala paquetes del sistema. La distribución y los avisos de
  LibreOffice y sus componentes deben revisarse sobre la imagen final, no solo sobre este repositorio.
- **Microsoft Office:** no se incluye; EPDF automatiza una instalación local que debe contar con su
  propia licencia válida.
- **Groq:** no se distribuye como dependencia. La traducción transmite únicamente bloques de texto
  después del consentimiento explícito y queda sujeta a los términos y política del proveedor.

## Resultado de verificaciones automáticas

- `pip check`: sin dependencias Python rotas.
- `pip-audit 2.10.1`, ejecutado desde un entorno temporal contra el `.venv` existente: 74 registros
  (69 identificadores únicos) en `certifi`, `Pillow`, `pypdf`, `setuptools` y `urllib3`. No se actualizó
  Python ni ninguna librería Python porque queda expresamente fuera del alcance de Fase 0C. El detalle
  y la diferencia con la imagen Docker, que resuelve versiones más nuevas, están en el informe 0C.
- `npm audit` del frontend: 4 grupos, 2 altos y 2 moderados (`vite`, `vitest`, `@vitest/mocker` y
  `source-map-js`). Son dependencias de desarrollo y no se modificaron fuera del alcance autorizado.
- `npm audit` de Electron después de la actualización controlada: 6 grupos moderados, 0 altos y
  0 críticos. Los seis derivan del mismo aviso de `minimatch` en la cadena de build de
  electron-builder; no forman parte del comportamiento de la aplicación instalada.
- La línea base recuperada de Electron 33.4.11 / electron-builder 25.1.8 reporta hoy 18 grupos
  (1 crítico, 13 altos y 4 moderados). El recuento original observado fue 19; la base de avisos de npm
  cambió entre ambas consultas. No se oculta la diferencia ni se fuerza `npm audit fix`.

## Requisitos antes de distribuir

1. Decidir si la distribución de PyMuPDF/MuPDF se hará cumpliendo AGPL-3.0 o mediante licencia
   comercial de Artifex; esta es la revisión legal más importante del paquete actual.
2. Firmar el instalador y los ejecutables de Windows antes de distribución pública; el build local de
   Fase 0C no tiene certificado de firma y electron-builder lo informa expresamente.
3. Generar un SBOM y recopilar los textos de licencia de dependencias transitivas del ejecutable final.
4. Abrir una fase separada para actualizar y bloquear las dependencias Python vulnerables detectadas,
   con pruebas de fidelidad PDF; no mezclarla con la actualización de Electron.
5. Repetir los inventarios sobre el artefacto final: PyInstaller y electron-builder pueden incluir
   componentes transitivos que no aparecen como imports directos.
