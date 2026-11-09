# Publicar EPDF en GitHub

Esta guía prepara un repositorio público sin incluir documentos personales, secretos, dependencias
instaladas ni resultados locales. No reemplaza la revisión final de los archivos que formarán el
primer commit.

## Identidad recomendada

**Nombre del repositorio:** `epdf`

**Descripción corta de GitHub:**

> Editor y conversor de PDF de escritorio para Windows, con procesamiento local mediante React,
> FastAPI, PyMuPDF y Electron.

**Topics:** `pdf`, `pdf-editor`, `pdf-converter`, `electron`, `react`, `fastapi`, `pymupdf`,
`python`, `typescript`, `windows`, `privacy-first`, `offline-first`.

La descripción comunica primero el trabajo que resuelve, después la plataforma y finalmente la
base técnica. Evita promesas absolutas de fidelidad o privacidad: la traducción usa Groq cuando el
usuario la activa.

## Qué debe publicarse

- `backend/app/`, `backend/tests/`, manifiestos y requisitos de Python.
- `frontend/src/`, configuración, `package.json` y `package-lock.json`.
- Código de Electron, sus pruebas, `package.json`, lock e iconos de compilación.
- `scripts/`, `Dockerfile`, `docker-compose.yml` y archivos `.env.example` sin valores secretos.
- Pruebas y experimentos reproducibles que usen datos sintéticos.
- `README.md`, inventario de dependencias y documentación pública.

Los lockfiles deben publicarse: permiten reproducir exactamente las dependencias de JavaScript.

## Qué no debe publicarse

- `backend/.env`, claves API, certificados, contraseñas o tokens.
- PDFs, DOCX u otros documentos de usuarios, aunque parezcan ejemplos útiles.
- `backend/.venv/`, `node_modules/`, cachés, `frontend/dist/` o `dist-desktop/`.
- Instaladores, ejecutables, ZIP de respaldo, logs, temporales y archivos de `output/`.
- Capturas, métricas e informes que contengan nombres, rutas o datos personales.
- Resultados locales de UAT y laboratorios. Publica después una versión sanitizada si aporta valor.

El `.gitignore` raíz aplica estas exclusiones. Un `.gitignore` evita futuras incorporaciones, pero
no elimina secretos que ya hayan entrado al historial.

## Decidir la licencia antes de publicar

- **MIT:** permite usar, modificar y redistribuir el código conservando el aviso de autoría.
- **GPL-3.0:** permite lo mismo, pero exige que las obras derivadas distribuidas mantengan la misma
  licencia.
- **Sin licencia:** GitHub puede mostrar el código, pero terceros no reciben permiso para copiarlo,
  modificarlo o redistribuirlo.

No añadas una licencia por inercia. La elección depende de cómo quieres permitir que otras personas
usen EPDF.

## Revisión previa

1. Rota cualquier clave que haya aparecido en archivos locales o registros de trabajo.
2. Confirma que los dos archivos `.env.example` no contengan valores reales.
3. Revisa la lista exacta de archivos que Git propone añadir.
4. Busca secretos y rutas personales otra vez.
5. Ejecuta tests, typecheck y build.
6. Crea el primer commit solo cuando la lista esté limpia.

## Secuencia de publicación

Ejecuta estos comandos desde la raíz del proyecto después de crear un repositorio vacío en GitHub.
No marques la opción de crear README, `.gitignore` o licencia en GitHub si esos archivos ya existen
localmente.

```powershell
git init
git branch -M main
git add --dry-run .
git status --short --ignored
git add .
git commit -m "Initial EPDF release"
git remote add origin https://github.com/TU-USUARIO/epdf.git
git push -u origin main
```

Antes de `git commit`, inspecciona lo preparado con `git diff --cached --stat` y
`git diff --cached`. Para binarios, verifica al menos el nombre, el origen y la licencia.

## Releases

El instalador no debe vivir en el historial Git. Publícalo como archivo adjunto de una GitHub
Release, junto con versión, suma SHA-256, requisitos de Windows, cambios y limitaciones conocidas.
Si el ejecutable aún no está firmado, indícalo de forma visible para que el aviso de Windows no
sorprenda a quien lo descargue.
