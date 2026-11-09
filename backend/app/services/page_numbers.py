"""Numeración de páginas."""

from enum import StrEnum
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

from app.services.stamping import stamp_pages


class NumberPosition(StrEnum):
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"
    TOP_RIGHT = "top-right"


class NumberStyle(StrEnum):
    NUMBER = "number"  # 3
    PAGE_OF_TOTAL = "page-of-total"  # Página 3 de 10
    FRACTION = "fraction"  # 3 / 10


_FONT = "Helvetica"
_FONT_SIZE = 10
_MARGIN_POINTS = 28
_INK = (0.2, 0.2, 0.2)


def page_label(style: NumberStyle, number: int, total: int) -> str:
    match style:
        case NumberStyle.NUMBER:
            return str(number)
        case NumberStyle.PAGE_OF_TOTAL:
            return f"Página {number} de {total}"
        case NumberStyle.FRACTION:
            return f"{number} / {total}"


def number_pages(source: Path, destination: Path, *, position: NumberPosition, style: NumberStyle, name: str) -> None:
    def draw(canvas: Canvas, width: float, height: float, index: int, total: int) -> None:
        label = page_label(style, index + 1, total)
        canvas.setFont(_FONT, _FONT_SIZE)
        canvas.setFillColorRGB(*_INK)

        at_top = position is NumberPosition.TOP_RIGHT
        y = height - _MARGIN_POINTS - _FONT_SIZE if at_top else _MARGIN_POINTS
        if position is NumberPosition.BOTTOM_CENTER:
            canvas.drawCentredString(width / 2, y, label)
        else:
            canvas.drawRightString(width - _MARGIN_POINTS, y, label)

    stamp_pages(source, destination, name=name, draw=draw, varies_per_page=True)
