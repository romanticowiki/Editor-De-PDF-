"""Miniaturas de páginas para los editores visuales (girar, eliminar, extraer, organizar)."""

import base64
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.services.errors import ToolError
from app.services.pdf_io import open_pdf

_THUMBNAIL_WIDTH_PX = 240
_JPEG_QUALITY = 70
MAX_PREVIEW_PAGES = 400


@dataclass(frozen=True, slots=True)
class PageThumbnail:
    width: float
    height: float
    data_url: str


def render_thumbnails(source: Path, *, name: str) -> list[PageThumbnail]:
    with open_pdf(source, name) as document:
        if document.page_count > MAX_PREVIEW_PAGES:
            raise ToolError(
                f"«{name}» tiene {document.page_count} páginas y el editor visual admite hasta {MAX_PREVIEW_PAGES}. "
                "Usa «Dividir PDF» primero."
            )
        return [_thumbnail(page) for page in document]


def _thumbnail(page: pymupdf.Page) -> PageThumbnail:
    # Acotado también por alto: una página muy alargada no debe generar una miniatura enorme.
    zoom = min(_THUMBNAIL_WIDTH_PX / page.rect.width, (_THUMBNAIL_WIDTH_PX * 2) / page.rect.height)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    encoded = base64.b64encode(pixmap.tobytes(output="jpeg", jpg_quality=_JPEG_QUALITY)).decode("ascii")
    return PageThumbnail(width=page.rect.width, height=page.rect.height, data_url=f"data:image/jpeg;base64,{encoded}")
