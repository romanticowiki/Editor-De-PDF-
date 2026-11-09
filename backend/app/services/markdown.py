"""Cualquier documento a Markdown limpio con MarkItDown, listo para pegarlo en Claude u otro LLM."""

import threading
from functools import lru_cache
from pathlib import Path

from markitdown import MarkItDown

from app.core.file_types import FileKind
from app.services.errors import ToolError
from app.services.pdf_io import ensure_readable_pdf

# MarkItDown no documenta ser seguro entre hilos.
_lock = threading.Lock()


@lru_cache(maxsize=1)
def _converter() -> MarkItDown:
    # Sin plugins de terceros. `convert_local` nunca descarga nada.
    return MarkItDown(enable_plugins=False)


def to_markdown(source: Path, destination: Path, *, kind: FileKind, name: str) -> None:
    if kind is FileKind.PDF:
        ensure_readable_pdf(source, name)

    try:
        with _lock:
            result = _converter().convert_local(str(source))
    except Exception as exc:
        raise ToolError(f"No pudimos leer «{name}». Prueba a exportarlo de nuevo.") from exc

    markdown = result.markdown.strip()
    if not markdown:
        raise ToolError(f"No encontramos texto en «{name}». Si es un escaneo, pásalo antes por OCR.")
    destination.write_text(f"{markdown}\n", encoding="utf-8")
