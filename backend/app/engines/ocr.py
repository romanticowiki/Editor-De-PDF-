"""Reconocimiento de texto con el motor Tesseract que PyMuPDF (MuPDF) lleva integrado.

No hace falta instalar el programa Tesseract: bastan los datos de idioma (`*.traineddata`).
Se buscan en `PDFEDITOR_TESSDATA_DIR`, `TESSDATA_PREFIX` o una instalación estándar de Tesseract.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pymupdf

from app.services.errors import EngineUnavailableError

_STANDARD_TESSDATA_DIRS = (
    Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
    Path("/usr/share/tesseract-ocr/5/tessdata"),
    Path("/usr/share/tesseract-ocr/4.00/tessdata"),
    Path("/opt/homebrew/share/tessdata"),
    Path("/usr/local/share/tessdata"),
)
_LANGUAGE_NAMES = {"spa": "español", "eng": "inglés"}


@dataclass(frozen=True, slots=True)
class RecognizedWord:
    rect: pymupdf.Rect
    text: str


class OcrEngine(Protocol):
    name: str

    def recognize(self, page: pymupdf.Page, *, language: str, dpi: int) -> list[RecognizedWord]: ...


class TesseractEngine:
    name = "Tesseract"

    def __init__(self, tessdata_dir: Path, languages: frozenset[str]) -> None:
        self._tessdata_dir = tessdata_dir
        self._languages = languages

    def recognize(self, page: pymupdf.Page, *, language: str, dpi: int) -> list[RecognizedWord]:
        missing = [code for code in language.split("+") if code not in self._languages]
        if missing:
            names = ", ".join(_LANGUAGE_NAMES.get(code, code) for code in missing)
            raise EngineUnavailableError(f"Faltan los datos de idioma para el OCR ({names}).")

        # full=True: reconoce la página entera como imagen (es un escaneo, no hay texto que conservar).
        textpage = page.get_textpage_ocr(language=language, dpi=dpi, full=True, tessdata=str(self._tessdata_dir))
        return [
            RecognizedWord(pymupdf.Rect(x0, y0, x1, y1), text)
            for (x0, y0, x1, y1, text, *_rest) in page.get_text("words", textpage=textpage)
            if text.strip()
        ]


def detect_ocr_engine(tessdata_dir: Path | None = None) -> OcrEngine | None:
    env_dir = os.environ.get("TESSDATA_PREFIX")
    candidates = (tessdata_dir, Path(env_dir) if env_dir else None, *_STANDARD_TESSDATA_DIRS)

    for candidate in candidates:
        if candidate is None or not candidate.is_dir():
            continue
        languages = frozenset(path.stem for path in candidate.glob("*.traineddata"))
        if languages:
            return TesseractEngine(candidate, languages)
    return None
