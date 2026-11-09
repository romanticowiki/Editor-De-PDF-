"""Unión de PDFs con pypdf.

Lógica pura, sin FastAPI: se puede testear y reutilizar desde cualquier ruta o script.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfWriter

from app.services.pdf_io import damaged_message, open_pdf_reader, user_facing_errors


@dataclass(frozen=True, slots=True)
class PdfSource:
    name: str
    stream: BinaryIO


def merge_pdfs(sources: Sequence[PdfSource], destination: Path) -> int:
    """Une `sources` en orden y escribe el resultado en `destination`. Devuelve el total de páginas."""
    writer = PdfWriter()
    try:
        for source in sources:
            reader = open_pdf_reader(source.stream, source.name)
            with user_facing_errors(damaged_message(source.name)):
                writer.append(reader)

        with user_facing_errors("No pudimos generar el PDF unido. Inténtalo de nuevo."), destination.open("wb") as out:
            writer.write(out)
        return len(writer.pages)
    finally:
        # Libera las referencias a páginas y streams de los lectores.
        writer.close()
