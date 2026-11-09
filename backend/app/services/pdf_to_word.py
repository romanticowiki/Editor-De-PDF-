"""PDF a Word editable con pdf2docx (reconstruye párrafos, tablas e imágenes por geometría)."""

import logging
from pathlib import Path

from pdf2docx import Converter

from app.services.errors import ToolError
from app.services.pdf_io import ensure_readable_pdf

logger = logging.getLogger(__name__)


def pdf_to_word(source: Path, destination: Path, *, name: str, allow_partial: bool = False) -> None:
    ensure_readable_pdf(source, name)

    converter: Converter | None = None
    try:
        converter = Converter(str(source))
        converter.convert(str(destination), ignore_page_error=allow_partial)
    except Exception as exc:  # pdf2docx lanza errores muy variados ante maquetaciones complejas
        logger.warning("pdf2docx falló con %s: %s", name, exc)
        raise ToolError(
            f"No pudimos convertir «{name}» completo y no se descargó un Word incompleto. "
            "Puedes reintentarlo activando «Permitir Word parcial» si aceptas que falten páginas."
        ) from exc
    finally:
        if converter is not None:
            converter.close()
