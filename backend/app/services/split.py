"""Dividir un PDF en varios: una página por archivo, rangos a medida o bloques fijos."""

from enum import StrEnum
from pathlib import Path

import pymupdf

from app.services.errors import ToolError
from app.services.packaging import OutputEntry, PackedOutput, pack_outputs
from app.services.page_ranges import parse_page_ranges
from app.services.pdf_io import open_pdf


class SplitMode(StrEnum):
    EVERY_PAGE = "pages"
    RANGES = "ranges"
    FIXED = "fixed"


def split_pdf(
    source: Path,
    directory: Path,
    *,
    mode: SplitMode,
    ranges_text: str | None,
    chunk_size: int | None,
    stem: str,
    name: str,
) -> PackedOutput:
    with open_pdf(source, name) as document:
        groups = _page_groups(mode, document.page_count, ranges_text, chunk_size)
        entries = (_extract(document, group, f"{stem}-{_label(group)}.pdf") for group in groups)
        return pack_outputs(entries, directory, archive_stem=f"{stem}-dividido")


def _page_groups(mode: SplitMode, page_count: int, ranges_text: str | None, chunk_size: int | None) -> list[range]:
    if mode is SplitMode.EVERY_PAGE:
        return [range(index, index + 1) for index in range(page_count)]
    if mode is SplitMode.FIXED:
        if chunk_size is None or chunk_size < 1:
            raise ToolError("Indica cada cuántas páginas quieres dividir.")
        return [range(start, min(start + chunk_size, page_count)) for start in range(0, page_count, chunk_size)]
    return parse_page_ranges(ranges_text or "", page_count)


def _label(group: range) -> str:
    return f"pagina-{group.start + 1}" if len(group) == 1 else f"paginas-{group.start + 1}-{group.stop}"


def _extract(document: pymupdf.Document, pages: range, filename: str) -> OutputEntry:
    with pymupdf.open() as part:
        # insert_pdf copia también fuentes e imágenes que usan esas páginas.
        part.insert_pdf(document, from_page=pages.start, to_page=pages.stop - 1)
        return OutputEntry(name=filename, data=part.tobytes(garbage=3, deflate=True))
