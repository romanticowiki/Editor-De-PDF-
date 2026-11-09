"""TXT, HTML y EPUB a PDF con el motor de maquetación de MuPDF (sin navegador ni acceso a red)."""

import html
from pathlib import Path

import pymupdf

from app.core.file_types import FileKind
from app.services.errors import ToolError
from app.services.story import write_story_pdf
from app.services.text import decode_text, strip_control_chars

_TEXT_CSS = """
body { font-family: sans-serif; font-size: 11pt; line-height: 1.5; }
pre { font-family: sans-serif; white-space: pre-wrap; margin: 0; }
"""


def document_to_pdf(source: Path, destination: Path, *, kind: FileKind, name: str) -> None:
    try:
        if kind is FileKind.TXT:
            # Decodificamos nosotros: MuPDF asume UTF-8 y rompería las tildes de un .txt en Windows-1252.
            text = strip_control_chars(decode_text(source.read_bytes()))
            write_story_pdf(f"<pre>{html.escape(text)}</pre>", _TEXT_CSS, destination)
        else:
            with pymupdf.open(source, filetype=kind.value) as document:
                destination.write_bytes(document.convert_to_pdf())
    except Exception as exc:
        raise ToolError(f"No pudimos convertir «{name}». Comprueba que se abre bien y vuelve a intentarlo.") from exc
