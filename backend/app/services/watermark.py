"""Marca de agua de texto, centrada y ajustada al tamaño de cada página."""

import math
from enum import StrEnum
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from app.services.errors import ToolError
from app.services.stamping import ensure_latin_text, stamp_pages
from app.services.text import strip_control_chars


class WatermarkLayout(StrEnum):
    DIAGONAL = "diagonal"
    HORIZONTAL = "horizontal"


class WatermarkOpacity(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    STRONG = "strong"


_ALPHA: dict[WatermarkOpacity, float] = {
    WatermarkOpacity.LIGHT: 0.15,
    WatermarkOpacity.MEDIUM: 0.3,
    WatermarkOpacity.STRONG: 0.5,
}
_FONT = "Helvetica-Bold"
_GRAY = (0.35, 0.35, 0.35)
_MAX_FONT_SIZE = 140
# Fracción del ancho (o de la diagonal) que ocupa el texto.
_SPAN = 0.7


def watermark_pdf(
    source: Path,
    destination: Path,
    *,
    text: str,
    layout: WatermarkLayout,
    opacity: WatermarkOpacity,
    name: str,
) -> None:
    label = ensure_latin_text(strip_control_chars(text), what="La marca de agua")
    if not label:
        raise ToolError("Escribe el texto de la marca de agua.")

    def draw(canvas: Canvas, width: float, height: float, _index: int, _total: int) -> None:
        span = math.hypot(width, height) if layout is WatermarkLayout.DIAGONAL else width
        font_size = min(_MAX_FONT_SIZE, span * _SPAN / stringWidth(label, _FONT, 1))

        canvas.saveState()
        canvas.setFillColorRGB(*_GRAY, alpha=_ALPHA[opacity])
        canvas.setFont(_FONT, font_size)
        canvas.translate(width / 2, height / 2)
        if layout is WatermarkLayout.DIAGONAL:
            canvas.rotate(math.degrees(math.atan2(height, width)))
        # Centrado óptico: baja el texto ~1/3 de su altura para que quede en el centro visual.
        canvas.drawCentredString(0, -font_size * 0.35, label)
        canvas.restoreState()

    stamp_pages(source, destination, name=name, draw=draw, varies_per_page=False)
