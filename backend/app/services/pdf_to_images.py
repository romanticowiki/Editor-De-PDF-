"""PDF a imágenes JPG/PNG con el rasterizador de MuPDF."""

from enum import StrEnum
from pathlib import Path

import pymupdf

from app.services.errors import ToolError
from app.services.packaging import OutputEntry, PackedOutput, pack_outputs
from app.services.pdf_io import open_pdf


class ImageFormat(StrEnum):
    PNG = "png"
    JPG = "jpg"


class ImageQuality(StrEnum):
    SCREEN = "screen"
    STANDARD = "standard"
    HIGH = "high"


_DPI: dict[ImageQuality, int] = {ImageQuality.SCREEN: 96, ImageQuality.STANDARD: 150, ImageQuality.HIGH: 300}
_JPEG_QUALITY = 90
# Tope por lado: una página gigante a 300 ppp agotaría la memoria.
_MAX_SIDE_PIXELS = 10_000
MAX_PAGES = 500


def pdf_to_images(
    source: Path,
    directory: Path,
    *,
    image_format: ImageFormat,
    quality: ImageQuality,
    stem: str,
    name: str,
) -> PackedOutput:
    with open_pdf(source, name) as document:
        if document.page_count > MAX_PAGES:
            raise ToolError(f"«{name}» tiene {document.page_count} páginas. Divídelo en partes de hasta {MAX_PAGES}.")

        digits = max(3, len(str(document.page_count)))
        # Generador: cada página se rasteriza y se escribe antes de pasar a la siguiente.
        entries = (
            _render_page(page, image_format, _DPI[quality], f"{stem}-pagina-{page.number + 1:0{digits}d}.{image_format}")
            for page in document
        )
        return pack_outputs(entries, directory, archive_stem=f"{stem}-imagenes")


def _render_page(page: pymupdf.Page, image_format: ImageFormat, dpi: int, filename: str) -> OutputEntry:
    longest_side = max(page.rect.width, page.rect.height)
    safe_dpi = min(dpi, int(_MAX_SIDE_PIXELS * 72 / longest_side))
    pixmap = page.get_pixmap(dpi=safe_dpi, alpha=False)
    if image_format is ImageFormat.PNG:
        data = pixmap.tobytes(output="png")
    else:
        data = pixmap.tobytes(output="jpeg", jpg_quality=_JPEG_QUALITY)
    return OutputEntry(name=filename, data=data)
