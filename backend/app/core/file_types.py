"""Formatos de entrada reconocidos.

La extensión orienta, pero la firma binaria decide: nunca confiamos solo en lo que dice el cliente.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

Matcher = Callable[[bytes], bool]

_PDF_SIGNATURE = b"%PDF-"
_ZIP_SIGNATURE = b"PK\x03\x04"  # docx, xlsx, pptx, odt, ods, odp, epub
_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # doc, xls, ppt antiguos
_RTF_SIGNATURE = b"{\\rtf"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _starts_with(signature: bytes) -> Matcher:
    return lambda head: head.startswith(signature)


def _is_pdf(head: bytes) -> bool:
    # La especificación tolera bytes basura antes de la cabecera.
    return _PDF_SIGNATURE in head


def _is_text(head: bytes) -> bool:
    return b"\x00" not in head


class FileKind(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    ODT = "odt"
    RTF = "rtf"
    XLSX = "xlsx"
    XLS = "xls"
    ODS = "ods"
    PPTX = "pptx"
    PPT = "ppt"
    ODP = "odp"
    TXT = "txt"
    HTML = "html"
    EPUB = "epub"
    JPG = "jpg"
    PNG = "png"
    MARKDOWN = "md"


@dataclass(frozen=True, slots=True)
class FileKindSpec:
    extensions: tuple[str, ...]
    matches: Matcher

    @property
    def canonical_extension(self) -> str:
        return self.extensions[0]


FILE_KINDS: dict[FileKind, FileKindSpec] = {
    FileKind.PDF: FileKindSpec((".pdf",), _is_pdf),
    FileKind.DOCX: FileKindSpec((".docx",), _starts_with(_ZIP_SIGNATURE)),
    FileKind.DOC: FileKindSpec((".doc",), _starts_with(_OLE_SIGNATURE)),
    FileKind.ODT: FileKindSpec((".odt",), _starts_with(_ZIP_SIGNATURE)),
    FileKind.RTF: FileKindSpec((".rtf",), _starts_with(_RTF_SIGNATURE)),
    FileKind.XLSX: FileKindSpec((".xlsx",), _starts_with(_ZIP_SIGNATURE)),
    FileKind.XLS: FileKindSpec((".xls",), _starts_with(_OLE_SIGNATURE)),
    FileKind.ODS: FileKindSpec((".ods",), _starts_with(_ZIP_SIGNATURE)),
    FileKind.PPTX: FileKindSpec((".pptx",), _starts_with(_ZIP_SIGNATURE)),
    FileKind.PPT: FileKindSpec((".ppt",), _starts_with(_OLE_SIGNATURE)),
    FileKind.ODP: FileKindSpec((".odp",), _starts_with(_ZIP_SIGNATURE)),
    FileKind.TXT: FileKindSpec((".txt",), _is_text),
    FileKind.HTML: FileKindSpec((".html", ".htm"), _is_text),
    FileKind.EPUB: FileKindSpec((".epub",), _starts_with(_ZIP_SIGNATURE)),
    FileKind.JPG: FileKindSpec((".jpg", ".jpeg"), _starts_with(_JPEG_SIGNATURE)),
    FileKind.PNG: FileKindSpec((".png",), _starts_with(_PNG_SIGNATURE)),
    FileKind.MARKDOWN: FileKindSpec((".md", ".markdown"), _is_text),
}

PDF_ONLY = frozenset({FileKind.PDF})
OFFICE_DOCUMENTS = frozenset(
    {
        FileKind.DOCX, FileKind.DOC, FileKind.ODT, FileKind.RTF,
        FileKind.XLSX, FileKind.XLS, FileKind.ODS,
        FileKind.PPTX, FileKind.PPT, FileKind.ODP,
    }
)  # fmt: skip
READING_DOCUMENTS = frozenset({FileKind.TXT, FileKind.HTML, FileKind.EPUB})
IMAGES = frozenset({FileKind.JPG, FileKind.PNG})
MARKDOWN_ONLY = frozenset({FileKind.MARKDOWN})
MARKDOWN_SOURCES = frozenset(
    {FileKind.PDF, FileKind.DOCX, FileKind.XLSX, FileKind.PPTX, FileKind.HTML, FileKind.TXT, FileKind.EPUB}
)


def detect_kind(filename: str | None, head: bytes, accepted: frozenset[FileKind]) -> FileKind | None:
    """Devuelve el formato aceptado cuya extensión Y firma coinciden, o None."""
    extension = Path(filename or "").suffix.lower()
    for kind in accepted:
        spec = FILE_KINDS[kind]
        if extension in spec.extensions and spec.matches(head):
            return kind
    # Un PDF se reconoce por su firma aunque llegue sin extensión.
    if FileKind.PDF in accepted and _is_pdf(head):
        return FileKind.PDF
    return None
