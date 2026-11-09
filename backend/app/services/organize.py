"""Reorganizar páginas: reordenar, girar, eliminar y extraer con una sola lista de instrucciones.

La interfaz manda la lista final de páginas (en orden, con su giro); lo que no aparece, se elimina.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pymupdf

from app.services.errors import ToolError
from app.services.packaging import OutputEntry, PackedOutput, pack_outputs
from app.services.pdf_io import open_pdf


class OrganizeOutput(StrEnum):
    SINGLE = "single"  # un PDF con las páginas elegidas
    SEPARATE = "separate"  # un PDF por página (en ZIP si son varias)


@dataclass(frozen=True, slots=True)
class PageInstruction:
    index: int  # página original, desde 0
    rotation: int = 0  # giro adicional en grados: 0, 90, 180 o 270


def organize_pdf(
    source: Path,
    directory: Path,
    *,
    instructions: Sequence[PageInstruction],
    output: OrganizeOutput,
    stem: str,
    name: str,
) -> PackedOutput:
    if not instructions:
        raise ToolError("Deja al menos una página.")

    with open_pdf(source, name) as document:
        if any(instruction.index >= document.page_count for instruction in instructions):
            raise ToolError("La lista de páginas no coincide con el documento. Vuelve a cargarlo.")

        entries: Iterable[OutputEntry]
        if output is OrganizeOutput.SINGLE:
            entries = [_build(document, instructions, f"{stem}-organizado.pdf")]
        else:
            entries = (
                _build(document, [instruction], f"{stem}-pagina-{instruction.index + 1}.pdf")
                for instruction in instructions
            )
        return pack_outputs(entries, directory, archive_stem=f"{stem}-paginas")


def _build(document: pymupdf.Document, instructions: Sequence[PageInstruction], filename: str) -> OutputEntry:
    with pymupdf.open() as result:
        for instruction in instructions:
            result.insert_pdf(document, from_page=instruction.index, to_page=instruction.index)
            if instruction.rotation:
                page = result[-1]
                # El giro se suma al que ya tuviera la página (la miniatura ya lo mostraba así).
                page.set_rotation((page.rotation + instruction.rotation) % 360)
        return OutputEntry(name=filename, data=result.tobytes(garbage=3, deflate=True))
