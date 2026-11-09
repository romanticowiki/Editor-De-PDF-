"""Generadores de documentos de prueba. Todo en memoria, sin archivos fijos en el repo."""

import io
import os
import zipfile

import pymupdf
from docx import Document
from PIL import Image

Upload = tuple[str, tuple[str, bytes, str]]


def upload(name: str, content: bytes, *, field: str = "file") -> Upload:
    return (field, (name, content, "application/octet-stream"))


def pdf_bytes(*, pages: int = 1, text: str | None = None, width: float = 595, height: float = 842) -> bytes:
    """Con `text` usa Helvetica estándar, que NO queda incrustada (útil para probar PDF/A)."""
    with pymupdf.open() as document:
        for number in range(1, pages + 1):
            page = document.new_page(width=width, height=height)
            if text:
                page.insert_text((72, 72), f"{text} {number}" if pages > 1 else text, fontsize=14)
        return document.tobytes()


def scanned_pdf_bytes(text: str) -> bytes:
    """Página que solo contiene una imagen con texto, sin texto seleccionable: como un escaneo."""
    with pymupdf.open() as source:
        page = source.new_page()
        page.insert_text((72, 140), text, fontsize=30)
        pixmap = page.get_pixmap(dpi=200)
    with pymupdf.open() as scan:
        scan_page = scan.new_page()
        scan_page.insert_image(scan_page.rect, pixmap=pixmap)
        return scan.tobytes(deflate=True)


def locked_pdf_bytes(password: str = "secreto") -> bytes:
    with pymupdf.open() as document:
        document.new_page()
        return document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)


def table_pdf_bytes(rows: list[list[str]]) -> bytes:
    cell_width, row_height, origin = 150, 24, 72
    with pymupdf.open() as document:
        page = document.new_page()
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                x0 = origin + column_index * cell_width
                y0 = origin + row_index * row_height
                rect = pymupdf.Rect(x0, y0, x0 + cell_width, y0 + row_height)
                page.draw_rect(rect, color=(0, 0, 0), width=1)
                page.insert_text((rect.x0 + 6, rect.y1 - 8), value, fontsize=11)
        return document.tobytes()


def image_pdf_bytes(pixels: int = 800) -> bytes:
    """Imagen de ruido a ~400 ppp: mucho margen para reducir."""
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixels, pixels, os.urandom(pixels * pixels * 3), False)
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_image(pymupdf.Rect(72, 72, 216, 216), pixmap=pixmap)
        return document.tobytes(deflate=True)


def image_bytes(width: int, height: int, image_format: str = "PNG", *, exif_orientation: int | None = None) -> bytes:
    image = Image.new("RGB", (width, height), (200, 120, 80))
    buffer = io.BytesIO()
    if exif_orientation is None:
        image.save(buffer, image_format)
    else:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        image.save(buffer, image_format, exif=exif)
    return buffer.getvalue()


def form_pdf_bytes() -> bytes:
    with pymupdf.open() as document:
        page = document.new_page()

        text = pymupdf.Widget()
        text.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        text.field_name = "nombre"
        text.field_label = "Nombre completo"
        text.rect = pymupdf.Rect(72, 72, 320, 94)
        page.add_widget(text)

        check = pymupdf.Widget()
        check.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
        check.field_name = "acepto"
        check.rect = pymupdf.Rect(72, 110, 90, 128)
        page.add_widget(check)

        combo = pymupdf.Widget()
        combo.field_type = pymupdf.PDF_WIDGET_TYPE_COMBOBOX
        combo.field_name = "pais"
        combo.choice_values = ["México", "España"]
        combo.field_value = "México"
        combo.rect = pymupdf.Rect(72, 140, 320, 162)
        page.add_widget(combo)

        return document.tobytes()


def docx_bytes(heading: str, paragraph: str) -> bytes:
    document = Document()
    document.add_heading(heading, level=1)
    document.add_paragraph(paragraph)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def epub_bytes(title: str, body: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        # El mimetype debe ir primero y sin comprimir.
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>'
            "</container>",
        )
        archive.writestr(
            "content.opf",
            '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
            f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">test</dc:identifier>'
            f"<dc:title>{title}</dc:title><dc:language>es</dc:language></metadata>"
            '<manifest><item id="c1" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>'
            '<spine><itemref idref="c1"/></spine></package>',
        )
        archive.writestr(
            "chapter.xhtml",
            f'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{title}</title></head>'
            f"<body><h1>{title}</h1><p>{body}</p></body></html>",
        )
    return buffer.getvalue()


def pdf_text(content: bytes) -> str:
    with pymupdf.open(stream=content, filetype="pdf") as document:
        return "".join(page.get_text() for page in document)


def zip_pdf_page_counts(content: bytes) -> dict[str, int]:
    counts: dict[str, int] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            with pymupdf.open(stream=archive.read(name), filetype="pdf") as document:
                counts[name] = document.page_count
    return counts
