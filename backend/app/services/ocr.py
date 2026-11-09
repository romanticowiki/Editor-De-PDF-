"""OCR: añade una capa de texto invisible sobre las páginas escaneadas.

La página original no se toca (no se rasteriza ni pierde calidad): encima de cada palabra
reconocida se escribe texto invisible, así se puede buscar, seleccionar y copiar.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pymupdf

from app.engines.ocr import OcrEngine, RecognizedWord
from app.services.errors import ToolError
from app.services.pdf_io import open_pdf


class OcrLanguage(StrEnum):
    SPANISH = "spa"
    ENGLISH = "eng"
    SPANISH_AND_ENGLISH = "spa+eng"


@dataclass(frozen=True, slots=True)
class OcrResult:
    pages_recognized: int


_OCR_DPI = 300
# Por debajo de estos caracteres la página se considera escaneada.
_EXISTING_TEXT_THRESHOLD = 20
_MIN_FONT_SIZE = 1.0
_INVISIBLE = 3  # render mode PDF: ni relleno ni trazo
_FONT = pymupdf.Font("helv")
MAX_OCR_PAGES = 100


def ocr_pdf(source: Path, destination: Path, *, engine: OcrEngine, language: OcrLanguage, name: str) -> OcrResult:
    with open_pdf(source, name) as document:
        if document.page_count > MAX_OCR_PAGES:
            raise ToolError(f"«{name}» tiene {document.page_count} páginas. Divídelo en partes de hasta {MAX_OCR_PAGES}.")

        recognized = 0
        for page in document:
            if len(page.get_text().strip()) >= _EXISTING_TEXT_THRESHOLD:
                continue  # ya tiene texto real: no lo duplicamos
            words = engine.recognize(page, language=language.value, dpi=_OCR_DPI)
            if words:
                inject_invisible_words(page, words)
                recognized += 1

        if recognized == 0:
            raise ToolError(f"«{name}» ya tiene texto seleccionable o no encontramos texto que reconocer.")
        document.save(destination, garbage=3, deflate=True)
    return OcrResult(pages_recognized=recognized)


def inject_invisible_words(page: pymupdf.Page, words: Iterable[RecognizedWord]) -> None:
    writer = pymupdf.TextWriter(page.rect)
    added = 0
    for word in words:
        unit_width = _FONT.text_length(word.text, fontsize=1)
        if unit_width <= 0:
            continue
        # Tamaño que ocupa el mismo ancho que la palabra: la selección coincide con lo que se ve.
        fontsize = min(word.rect.height * 0.85, word.rect.width / unit_width)
        if fontsize < _MIN_FONT_SIZE:
            continue
        baseline = (word.rect.x0, word.rect.y1 - word.rect.height * 0.2)
        writer.append(baseline, word.text, font=_FONT, fontsize=fontsize)
        added += 1

    # Un solo bloque de texto por página: mucho más ligero que una inserción por palabra.
    if added:
        writer.write_text(page, render_mode=_INVISIBLE)
