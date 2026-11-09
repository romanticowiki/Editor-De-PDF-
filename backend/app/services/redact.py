"""Censura irreversible de texto sensible.

No se dibuja un rectángulo encima (eso se puede quitar): se eliminan del archivo el texto,
los píxeles de imagen y los trazos que quedan bajo cada coincidencia, y se limpian
metadatos, adjuntos y JavaScript que podrían filtrar lo censurado.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pymupdf

from app.services.errors import ToolError
from app.services.pdf_io import open_pdf
from app.services.text import strip_control_chars


class RedactionFill(StrEnum):
    BLACK = "black"
    WHITE = "white"


@dataclass(frozen=True, slots=True)
class RedactionResult:
    matches: int


_FILL_COLORS: dict[RedactionFill, tuple[float, float, float]] = {
    RedactionFill.BLACK: (0, 0, 0),
    RedactionFill.WHITE: (1, 1, 1),
}
_MIN_TERM_LENGTH = 2
MAX_TERMS = 50


def parse_terms(raw: str) -> list[str]:
    """Un término por línea (las comas se permiten dentro: «Pérez, Ana»)."""
    terms = list(dict.fromkeys(line.strip() for line in strip_control_chars(raw).splitlines() if line.strip()))
    if not terms:
        raise ToolError("Escribe al menos un texto que quieras censurar.")
    if len(terms) > MAX_TERMS:
        raise ToolError(f"Puedes censurar hasta {MAX_TERMS} textos a la vez.")
    too_short = [term for term in terms if len(term) < _MIN_TERM_LENGTH]
    if too_short:
        raise ToolError(f"«{too_short[0]}» es demasiado corto: censuraría demasiadas coincidencias.")
    return terms


def redact_pdf(source: Path, destination: Path, *, terms_text: str, fill: RedactionFill, name: str) -> RedactionResult:
    terms = parse_terms(terms_text)

    with open_pdf(source, name) as document:
        matches = 0
        for page in document:
            hits = [rect for term in terms for rect in page.search_for(term)]
            if not hits:
                continue
            for rect in hits:
                page.add_redact_annot(rect, fill=_FILL_COLORS[fill], cross_out=False)
            page.apply_redactions(
                images=pymupdf.PDF_REDACT_IMAGE_PIXELS,  # borra solo los píxeles cubiertos
                graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                text=pymupdf.PDF_REDACT_TEXT_REMOVE,
            )
            matches += len(hits)

        if matches == 0:
            listed = ", ".join(f"«{term}»" for term in terms[:3])
            raise ToolError(f"No encontramos {listed} en «{name}». Si es un escaneo, pásalo antes por OCR.")

        document.scrub(
            attached_files=True,
            embedded_files=True,
            javascript=True,
            metadata=True,
            hidden_text=False,  # conserva la capa de OCR (lo sensible ya se eliminó también de ella)
            remove_links=False,
        )
        # garbage=4 elimina del archivo los objetos que quedaron huérfanos tras borrar.
        document.save(destination, garbage=4, deflate=True, clean=True)
    return RedactionResult(matches=matches)
