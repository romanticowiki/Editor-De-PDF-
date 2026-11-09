"""Apertura segura de PDFs con mensajes claros, compartida por todas las herramientas."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

import pymupdf
from pypdf import PdfReader

from app.services.errors import ToolError

logger = logging.getLogger(__name__)


def damaged_message(name: str) -> str:
    return f"«{name}» parece dañado. Prueba a exportarlo de nuevo."


def locked_message(name: str) -> str:
    return f"«{name}» tiene contraseña. Quítala y vuelve a intentarlo."


@contextmanager
def user_facing_errors(message: str) -> Iterator[None]:
    """Convierte cualquier fallo inesperado de una librería en un `ToolError` con `message`."""
    try:
        yield
    except ToolError:
        raise
    except Exception as exc:
        # Entrada no confiable: las librerías PDF pueden lanzar casi cualquier excepción ante un archivo corrupto.
        logger.warning("Fallo procesando documento: %s", exc)
        raise ToolError(message) from exc


def ensure_readable_pdf(path: Path, name: str) -> None:
    """Falla pronto y con un mensaje claro antes de pasar el PDF a librerías con errores crípticos."""
    with open_pdf(path, name):
        pass


@contextmanager
def open_pdf(path: Path, name: str) -> Iterator[pymupdf.Document]:
    try:
        document = pymupdf.open(path, filetype="pdf")
    except Exception as exc:  # entrada no confiable: cualquier fallo de parseo es "dañado"
        raise ToolError(damaged_message(name)) from exc

    try:
        if document.needs_pass:
            raise ToolError(locked_message(name))
        if document.page_count == 0:
            raise ToolError(f"«{name}» no tiene páginas.")
        yield document
    finally:
        document.close()


def open_pdf_reader(source: Path | BinaryIO, name: str) -> PdfReader:
    """Lector de pypdf. Muchos PDF "protegidos" solo tienen contraseña de propietario y abren con ""."""
    with user_facing_errors(damaged_message(name)):
        reader = PdfReader(source)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ToolError(locked_message(name))
        return reader
