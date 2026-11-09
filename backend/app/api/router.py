"""Punto único de registro de rutas. Cada herramienta PDF nueva se añade aquí."""

from fastapi import APIRouter

from app.api.routes import (
    compress,
    document_to_pdf,
    editor,
    forms,
    health,
    images_to_pdf,
    markdown,
    markdown_export,
    merge,
    ocr,
    office_to_pdf,
    page_numbers,
    pages,
    pdf_to_excel,
    pdf_to_images,
    pdf_to_powerpoint,
    pdf_to_word,
    pdfa,
    redact,
    split,
    tools,
    translate,
    watermark,
)

api_router = APIRouter()

for module in (
    health,
    tools,
    # Organizar
    merge,
    split,
    pages,
    # Optimizar
    compress,
    pdfa,
    # Convertir desde PDF
    pdf_to_word,
    pdf_to_excel,
    pdf_to_powerpoint,
    pdf_to_images,
    # Convertir a PDF
    office_to_pdf,
    document_to_pdf,
    images_to_pdf,
    # Editar y proteger
    ocr,
    translate,
    editor,
    watermark,
    page_numbers,
    redact,
    forms,
    # IA
    markdown,
    markdown_export,
):
    api_router.include_router(module.router)
