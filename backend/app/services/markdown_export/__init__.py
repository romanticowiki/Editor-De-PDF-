"""Markdown a PDF, Word o PowerPoint. Un exportador por formato; todos comparten el mismo parser."""

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from app.services.errors import ToolError
from app.services.markdown_export.parser import MAX_MARKDOWN_CHARS
from app.services.markdown_export.to_docx import markdown_to_docx
from app.services.markdown_export.to_pdf import markdown_to_pdf
from app.services.markdown_export.to_pptx import markdown_to_pptx
from app.services.pdf_io import user_facing_errors
from app.services.text import decode_text, strip_control_chars


class MarkdownTarget(StrEnum):
    PDF = "pdf"
    WORD = "docx"
    POWERPOINT = "pptx"


_EXPORTERS: dict[MarkdownTarget, Callable[[str, Path], None]] = {
    MarkdownTarget.PDF: markdown_to_pdf,
    MarkdownTarget.WORD: markdown_to_docx,
    MarkdownTarget.POWERPOINT: markdown_to_pptx,
}


def export_markdown(source: Path, destination: Path, *, target: MarkdownTarget, name: str) -> None:
    # Sin caracteres de control: Word y PowerPoint son XML y los rechazan.
    text = strip_control_chars(decode_text(source.read_bytes()))
    if not text.strip():
        raise ToolError(f"«{name}» está vacío.")
    if len(text) > MAX_MARKDOWN_CHARS:
        raise ToolError(f"«{name}» es demasiado largo. Divídelo en varios archivos.")

    with user_facing_errors(f"No pudimos convertir «{name}». Revisa que sea Markdown válido."):
        _EXPORTERS[target](text, destination)
