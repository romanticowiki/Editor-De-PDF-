"""Traducir un PDF conservando el diseño en lo posible.

Estrategia: por cada bloque de texto se guarda su posición, se traduce todo el documento
de una vez (menos llamadas al servicio) y luego, sobre cada página, se borra el texto
original (sin tocar las imágenes) y se reinserta la traducción dentro del mismo recuadro,
ajustando el tamaño de letra para que quepa. Un escaneo sin texto no se puede traducir.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pymupdf

from app.engines.translate import TranslationEngine
from app.services.errors import ToolError
from app.services.pdf_io import open_pdf

MAX_TRANSLATE_PAGES = 50
# Una sola fuente para todos los idiomas: cubre acentos latinos y Hangul (coreano).
_FONT = pymupdf.Font("cjk")
_FONT_SIZES = (11.0, 10.0, 9.0, 8.0, 7.0, 6.0, 5.0)
_MIN_FONT_SIZE = _FONT_SIZES[-1]
_TEXT_BLOCK = 0  # get_text("blocks"): tipo 0 = texto, 1 = imagen


class TranslateLanguage(StrEnum):
    SPANISH = "es"
    ENGLISH = "en"
    FRENCH = "fr"
    GERMAN = "de"
    KOREAN = "ko"


@dataclass(frozen=True, slots=True)
class TranslateResult:
    blocks_translated: int


@dataclass(frozen=True, slots=True)
class _Block:
    rect: pymupdf.Rect
    text_index: int


def translate_pdf(
    source: Path,
    destination: Path,
    *,
    engine: TranslationEngine,
    source_lang: TranslateLanguage,
    target_lang: TranslateLanguage,
    name: str,
) -> TranslateResult:
    if source_lang is target_lang:
        raise ToolError("Elige un idioma de destino distinto al de origen.")

    with open_pdf(source, name) as document:
        if document.page_count > MAX_TRANSLATE_PAGES:
            raise ToolError(
                f"«{name}» tiene {document.page_count} páginas y traducir admite hasta {MAX_TRANSLATE_PAGES}. "
                "Usa «Dividir PDF» primero."
            )

        texts: list[str] = []
        blocks_by_page: list[list[_Block]] = []
        for page in document:
            page_blocks: list[_Block] = []
            for x0, y0, x1, y1, text, _no, block_type in page.get_text("blocks"):
                clean = text.strip()
                if block_type != _TEXT_BLOCK or not clean:
                    continue
                page_blocks.append(_Block(rect=pymupdf.Rect(x0, y0, x1, y1), text_index=len(texts)))
                texts.append(clean)
            blocks_by_page.append(page_blocks)

        if not texts:
            raise ToolError(f"«{name}» no tiene texto para traducir. Si es un escaneo, pásalo antes por OCR.")

        translations = engine.translate_many(texts, source=source_lang.value, target=target_lang.value)
        if len(translations) != len(texts):
            raise ToolError("No pudimos traducir el documento. Inténtalo de nuevo.")

        for page, page_blocks in zip(document, blocks_by_page, strict=True):
            _rewrite_page(page, page_blocks, translations)

        document.save(destination, garbage=3, deflate=True)

    return TranslateResult(blocks_translated=len(texts))


def _rewrite_page(page: pymupdf.Page, blocks: list[_Block], translations: list[str]) -> None:
    if not blocks:
        return
    # Primero borramos de verdad el texto original; PDF_REDACT_IMAGE_NONE conserva las imágenes.
    for block in blocks:
        page.add_redact_annot(block.rect, fill=(1, 1, 1))
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)

    for block in blocks:
        _draw_into(page, block.rect, translations[block.text_index])


def _draw_into(page: pymupdf.Page, rect: pymupdf.Rect, text: str) -> None:
    for size in _FONT_SIZES:
        writer = pymupdf.TextWriter(page.rect)
        leftover = writer.fill_textbox(rect, text, font=_FONT, fontsize=size, align=pymupdf.TEXT_ALIGN_LEFT)
        if not leftover:
            writer.write_text(page)
            return
    # No cupo ni al tamaño mínimo: se escribe recortado antes que perder el bloque entero.
    writer = pymupdf.TextWriter(page.rect)
    writer.fill_textbox(rect, text, font=_FONT, fontsize=_MIN_FONT_SIZE, align=pymupdf.TEXT_ALIGN_LEFT)
    writer.write_text(page)
