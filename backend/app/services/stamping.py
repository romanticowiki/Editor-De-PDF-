"""Capas dibujadas con ReportLab y fusionadas sobre cada página con pypdf.

Base común de las marcas de agua y la numeración: cada herramienta solo define qué dibujar.
"""

import io
from collections.abc import Callable
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas

from app.services.errors import ToolError
from app.services.pdf_io import damaged_message, ensure_readable_pdf, open_pdf_reader, user_facing_errors

# (lienzo, ancho, alto, índice de página, total de páginas)
DrawLayer = Callable[[Canvas, float, float, int, int], None]


def ensure_latin_text(text: str, *, what: str) -> str:
    """Las fuentes estándar de PDF solo cubren el alfabeto latino (Windows-1252)."""
    clean = text.strip()
    try:
        clean.encode("cp1252")
    except UnicodeEncodeError as exc:
        raise ToolError(f"{what} solo admite letras del alfabeto latino, números y signos comunes.") from exc
    return clean


def stamp_pages(source: Path, destination: Path, *, name: str, draw: DrawLayer, varies_per_page: bool) -> None:
    ensure_readable_pdf(source, name)
    reader = open_pdf_reader(source, name)
    writer = PdfWriter()
    total = len(reader.pages)
    # Si la capa no depende de la página, se dibuja una vez por tamaño y se reutiliza.
    cache: dict[tuple[float, float], PageObject] = {}

    try:
        with user_facing_errors(damaged_message(name)):
            for index, page in enumerate(reader.pages):
                # Normaliza los giros: la capa se dibuja en el mismo sentido en que se ve la página.
                page.transfer_rotation_to_content()
                box = page.cropbox
                width, height = float(box.width), float(box.height)

                overlay = None if varies_per_page else cache.get((width, height))
                if overlay is None:
                    overlay = _render_layer(width, height, lambda canvas: draw(canvas, width, height, index, total))
                    if not varies_per_page:
                        cache[(width, height)] = overlay

                page.merge_translated_page(overlay, float(box.left), float(box.bottom))
                writer.add_page(page)

            with destination.open("wb") as out:
                writer.write(out)
    finally:
        writer.close()


def _render_layer(width: float, height: float, draw: Callable[[Canvas], None]) -> PageObject:
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(width, height))
    draw(canvas)
    canvas.showPage()
    canvas.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]
