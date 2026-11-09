from app.core.file_types import MARKDOWN_SOURCES, OFFICE_DOCUMENTS, PDF_ONLY, FileKind, detect_kind

ZIP_HEAD = b"PK\x03\x04rest"


def test_detects_by_extension_and_signature() -> None:
    assert detect_kind("carta.DOCX", ZIP_HEAD, OFFICE_DOCUMENTS) is FileKind.DOCX
    assert detect_kind("datos.xlsx", ZIP_HEAD, OFFICE_DOCUMENTS) is FileKind.XLSX


def test_rejects_spoofed_extension() -> None:
    assert detect_kind("carta.docx", b"%PDF-1.7", OFFICE_DOCUMENTS) is None
    assert detect_kind("notas.txt", b"texto\x00binario", MARKDOWN_SOURCES) is None


def test_recognizes_pdf_without_extension() -> None:
    assert detect_kind("descarga", b"%PDF-1.7", PDF_ONLY) is FileKind.PDF


def test_ignores_formats_not_accepted_by_the_tool() -> None:
    assert detect_kind("carta.docx", ZIP_HEAD, PDF_ONLY) is None
