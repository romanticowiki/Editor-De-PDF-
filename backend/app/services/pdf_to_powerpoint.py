"""PDF a PowerPoint: cada página se convierte en una diapositiva.

La página entra como imagen nítida (fiel al diseño original) y su texto se copia
en las notas del orador para poder buscarlo y reutilizarlo.
"""

import io
from pathlib import Path

import pymupdf
from pptx import Presentation
from pptx.slide import SlideLayout
from pptx.util import Emu

from app.services.errors import ToolError
from app.services.pdf_io import open_pdf
from app.services.text import strip_control_chars

_RENDER_DPI = 150
_JPEG_QUALITY = 85
_EMU_PER_POINT = 12_700
_BLANK_LAYOUT_INDEX = 6
# PowerPoint solo admite diapositivas de 1 a 56 pulgadas por lado.
_MIN_SLIDE_POINTS = 72
_MAX_SLIDE_POINTS = 56 * 72
# python-pptx guarda todas las imágenes en memoria hasta el final.
MAX_PAGES = 300


def pdf_to_powerpoint(source: Path, destination: Path, *, name: str) -> None:
    presentation = Presentation()
    layout = presentation.slide_layouts[_BLANK_LAYOUT_INDEX]

    with open_pdf(source, name) as document:
        if document.page_count > MAX_PAGES:
            raise ToolError(f"«{name}» tiene {document.page_count} páginas. Divídelo en partes de hasta {MAX_PAGES}.")

        width, height = _slide_size(document[0].rect)
        presentation.slide_width = Emu(round(width * _EMU_PER_POINT))
        presentation.slide_height = Emu(round(height * _EMU_PER_POINT))
        for page in document:
            _add_page_slide(presentation, layout, page)

    presentation.save(str(destination))


def _slide_size(rect: pymupdf.Rect) -> tuple[float, float]:
    scale = min(1.0, _MAX_SLIDE_POINTS / max(rect.width, rect.height))
    scale = max(scale, _MIN_SLIDE_POINTS / min(rect.width, rect.height))
    return rect.width * scale, rect.height * scale


def _add_page_slide(presentation: Presentation, layout: SlideLayout, page: pymupdf.Page) -> None:
    image = io.BytesIO(page.get_pixmap(dpi=_RENDER_DPI, alpha=False).tobytes(output="jpeg", jpg_quality=_JPEG_QUALITY))

    slide_width, slide_height = presentation.slide_width, presentation.slide_height
    # Encaja la página sin deformarla si su tamaño difiere del de la primera.
    fit = min(slide_width / page.rect.width, slide_height / page.rect.height)
    picture_width, picture_height = round(page.rect.width * fit), round(page.rect.height * fit)

    slide = presentation.slides.add_slide(layout)
    slide.shapes.add_picture(
        image,
        (slide_width - picture_width) // 2,
        (slide_height - picture_height) // 2,
        picture_width,
        picture_height,
    )

    text = strip_control_chars(page.get_text()).strip()
    if text:
        slide.notes_slide.notes_text_frame.text = text
