# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────
# Etapa 1: compilar la interfaz de React (API en el mismo origen).
# ─────────────────────────────────────────────────────────────
FROM node:24-slim AS frontend
WORKDIR /frontend

# Primero solo el manifiesto: aprovecha la caché de capas si no cambian las dependencias.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
# El modo producción usa frontend/.env.production → VITE_API_BASE_URL=/api/v1 (mismo puerto).
RUN npm run build

# ─────────────────────────────────────────────────────────────
# Etapa 2: motor FastAPI + LibreOffice + Tesseract, sirviendo todo en un puerto.
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# LibreOffice convierte Office→PDF (Microsoft Office no existe en Linux); Tesseract hace el OCR.
# --no-install-recommends mantiene la imagen lo más pequeña posible.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer libreoffice-calc libreoffice-impress \
    tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencias de Python primero, para reutilizar la caché.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
# La interfaz compilada llega de la etapa anterior; FastAPI la sirve en «/».
COPY --from=frontend /frontend/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1 \
    PDFEDITOR_ENVIRONMENT=production \
    PDFEDITOR_HOST=0.0.0.0 \
    PDFEDITOR_PORT=8000 \
    PDFEDITOR_FRONTEND_DIST=/app/frontend/dist
# Tesseract instala los datos de idioma en /usr/share/tesseract-ocr/5/tessdata,
# una de las rutas estándar que el backend ya detecta solo.

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
