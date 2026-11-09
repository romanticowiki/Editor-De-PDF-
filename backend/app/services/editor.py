"""Editor visual: aplica anotaciones (texto, resaltado, dibujo, parche, firma) sobre un PDF.

Seguridad de memoria: las páginas se acotan, las coordenadas se recortan al tamaño real de
la página (una X de 99999 no dibuja fuera ni revienta), y las imágenes PNG/JPG se validan (firma
de bytes, tamaño y dimensiones) antes de insertarlas.
"""

import base64
import io
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

from app.schemas.editor import (
    AddImageOp,
    AddTextOp,
    AddTextBoxOp,
    DrawOp,
    EditorRequest,
    HighlightOp,
    PatchTextOp,
    Rect,
    SetFieldOp,
)
from app.services.errors import ToolError
from app.services.pdf_io import open_pdf, user_facing_errors
from app.services.text import strip_control_chars
from app.services.forms import describe_form_field, update_form_field

MAX_EDITOR_PAGES = 200
MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_IMAGE_SIDE = 6_000
_PREVIEW_WIDTH = 1_100
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
# Una sola fuente que cubre acentos latinos y otros alfabetos: el texto insertado nunca sale en blanco.
_FONT = pymupdf.Font("cjk")
_FONT_DATA = _FONT.buffer


@dataclass(frozen=True, slots=True)
class RenderedPage:
    number: int
    width: float
    height: float
    image: str
    has_form_fields: bool
    fields: list[dict[str, object]]


def editor_font() -> bytes:
    return _FONT_DATA


def render_editor_pages(source: Path, *, name: str) -> list[RenderedPage]:
    """Rasteriza cada página a una imagen sobre la que el frontend dibuja las anotaciones."""
    with open_pdf(source, name) as document:
        if document.page_count > MAX_EDITOR_PAGES:
            raise ToolError(
                f"«{name}» tiene {document.page_count} páginas y el editor admite hasta {MAX_EDITOR_PAGES}. "
                "Usa «Dividir PDF» primero."
            )
        return [_render(page) for page in document]


def edit_pdf(source: Path, destination: Path, *, request: EditorRequest, images: list[bytes], name: str) -> int:
    """Aplica todas las operaciones y guarda. Devuelve cuántas se aplicaron."""
    signatures = [_validate_image(data) for data in images]

    with open_pdf(source, name) as document:
        page_count = document.page_count
        if page_count > MAX_EDITOR_PAGES:
            raise ToolError(f"«{name}» tiene demasiadas páginas para el editor (máximo {MAX_EDITOR_PAGES}).")

        for op in request.operations:
            if op.page >= page_count:
                raise ToolError(f"La operación apunta a la página {op.page + 1}, que no existe en «{name}».")
            if isinstance(op, AddImageOp) and op.image >= len(signatures):
                raise ToolError("Falta el archivo de una imagen, firma o sello.")

        # Los parches borran de verdad; hay que aplicar las redacciones ANTES de reescribir encima.
        for page_index in {op.page for op in request.operations if isinstance(op, PatchTextOp)}:
            page = document[page_index]
            for patch in (op for op in request.operations if isinstance(op, PatchTextOp) and op.page == page_index):
                rect = _clamp_rect(patch.rect, page)
                if rect is not None:
                    page.add_redact_annot(rect, fill=patch.fill)
            with _unrotated_page(page):
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)

        # Las imágenes terminan en la capa de anotaciones, después de cualquier marca.
        for op in sorted(request.operations, key=lambda operation: isinstance(operation, AddImageOp)):
            _apply(document[op.page], op, signatures)

        document.save(destination, garbage=3, deflate=True)

    return len(request.operations)


def _apply(page: pymupdf.Page, op: object, signatures: list[bytes]) -> None:
    if isinstance(op, AddTextOp):
        _write_text(page, op.x, op.y, op.text, op.size, op.color)
    elif isinstance(op, AddTextBoxOp):
        rect = pymupdf.Rect(op.rect.x0, op.rect.y0, op.rect.x1, op.rect.y1) & page.rect
        if rect.is_empty:
            raise ToolError("La caja de texto está fuera de la página.")
        _write_text(page, rect.x0, rect.y0, op.text, op.size, op.color, textbox=rect, align=op.align)
    elif isinstance(op, SetFieldOp):
        widgets = [widget for widget in page.widgets() if widget.field_name == op.name]
        if not widgets:
            raise ToolError("No encontramos ese campo en el formulario.")
        for widget in widgets:
            update_form_field(widget, op.value, size=op.size)
    elif isinstance(op, PatchTextOp):
        _write_text(page, op.rect.x0, op.rect.y0, op.text, op.size, op.color)
    elif isinstance(op, HighlightOp):
        rect = _clamp_rect(op.rect, page)
        if rect is not None:
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=op.color)
            annot.update()
    elif isinstance(op, DrawOp):
        strokes = [[tuple(pymupdf.Point(_clamp_point(x, y, page)) * page.derotation_matrix) for x, y in stroke] for stroke in op.strokes]
        widgets = [widget.rect for widget in page.widgets()]
        for stroke in strokes:
            for start, end in zip(stroke, stroke[1:] or stroke):
                segment = pymupdf.Rect(min(start[0], end[0]) - op.width / 2, min(start[1], end[1]) - op.width / 2, max(start[0], end[0]) + op.width / 2, max(start[1], end[1]) + op.width / 2)
                _reject_widget_overlap(page, segment, widgets)
        annot = page.add_ink_annot(strokes)
        annot.set_colors(stroke=op.color)
        annot.set_border(width=op.width)
        annot.update()
    elif isinstance(op, AddImageOp):
        rect = _clamp_rect(op.rect, page)
        if rect is not None:
            _insert_foreground_image(page, rect, signatures[op.image])


def _insert_foreground_image(page: pymupdf.Page, rect: pymupdf.Rect, image: bytes) -> None:
    """Una apariencia de sello propia cubre también anotaciones sin destruirlas."""
    # shortcut: los widgets mantienen su capa interactiva; cubrirlos exigiría aplanar el formulario explícitamente.
    document = page.parent
    with _unrotated_page(page) as rotation:
        page.insert_image(rect, stream=image, keep_proportion=True, overlay=True, rotate=rotation)
        contents = page.get_contents()
        appearance = contents.pop()
        bbox = rect * ~page.transformation_matrix
        coordinates = "[" + " ".join(str(value) for value in bbox) + "]"
        document.xref_set_key(appearance, "Type", "/XObject")
        document.xref_set_key(appearance, "Subtype", "/Form")
        document.xref_set_key(appearance, "BBox", coordinates)
        document.xref_set_key(appearance, "Resources", document.xref_get_key(page.xref, "Resources")[1])
        # Mover el flujo, no duplicarlo: un PNG semitransparente se pinta una sola vez.
        document.xref_set_key(page.xref, "Contents", "[" + " ".join(f"{xref} 0 R" for xref in contents) + "]")
        annotation = page.add_rect_annot(rect)
        document.xref_set_key(annotation.xref, "Subtype", "/Stamp")
        document.xref_set_key(annotation.xref, "Rect", coordinates)
        document.xref_set_key(annotation.xref, "AP", f"<< /N {appearance} 0 R >>")


def _write_text(page: pymupdf.Page, x: float, y: float, text: str, size: float, color: tuple[float, float, float], *, textbox: pymupdf.Rect | None = None, align: int = 0) -> None:
    clean = strip_control_chars(text)  # nada de bytes de control; insert_text nunca ejecuta código (sin JS en el PDF)
    if not clean:
        return
    px, baseline = _clamp_point(x, y + size, page)  # (x,y) es la esquina superior; la base va una línea más abajo
    derotation = page.derotation_matrix
    with _unrotated_page(page):
        writer = pymupdf.TextWriter(page.rect, color=color)
        if textbox is None:
            writer.append((px, baseline), clean, font=_FONT, fontsize=size)
        else:
            if textbox.width <= size * 0.2 + max(_FONT.char_lengths(clean, fontsize=size), default=0):
                raise ToolError("El texto no cabe en la caja. Amplíala o reduce el tamaño de fuente.")
            try:
                remaining = writer.fill_textbox(textbox, clean, font=_FONT, fontsize=size, align=align, lineheight=1.35)
            except ValueError as exc:
                raise ToolError("El texto no cabe en la caja. Amplíala o reduce el tamaño de fuente.") from exc
            if remaining or writer.last_point.y - _FONT.descender * size > textbox.y1 + 0.01:
                raise ToolError("El texto no cabe en la caja. Amplíala o reduce el tamaño de fuente.")
        _reject_widget_overlap(page, writer.text_rect * derotation)
        crop = page.cropbox_position
        offset = pymupdf.Matrix(1, 0, 0, 1, crop.x, crop.y + page.mediabox.y0)
        # Deshacer el origen de TextWriter y compensar su desplazamiento del CropBox.
        matrix = pymupdf.Matrix(1, 0, 0, -1, 0, page.rect.height) * derotation * ~page.transformation_matrix * ~offset
        writer.write_text(page, matrix=matrix, overlay=True)


def _reject_widget_overlap(page: pymupdf.Page, rect: pymupdf.Rect, widgets: list[pymupdf.Rect] | None = None) -> None:
    areas = widgets if widgets is not None else [widget.rect for widget in page.widgets()]
    if any(rect.intersects(area) for area in areas):
        raise ToolError("La anotación cruza un campo del formulario. Edita el campo directamente o usa «Rellenar formulario» para conservar la edición.")


@contextmanager
def _unrotated_page(page: pymupdf.Page) -> Iterator[int]:
    # PyMuPDF omite el desplazamiento del CropBox en transformation_matrix si la página está girada.
    rotation = page.rotation
    page.set_rotation(0)
    try:
        yield rotation
    finally:
        page.set_rotation(rotation)


def _clamp_rect(rect: Rect, page: pymupdf.Page) -> pymupdf.Rect | None:
    clamped = pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y1) & page.rect
    return None if clamped.is_empty else clamped * page.derotation_matrix


def _clamp_point(x: float, y: float, page: pymupdf.Page) -> tuple[float, float]:
    return (min(max(x, 0.0), page.rect.width), min(max(y, 0.0), page.rect.height))


def _validate_image(data: bytes) -> bytes:
    if len(data) > MAX_IMAGE_BYTES:
        raise ToolError("Una imagen supera el tamaño permitido.")
    if not data.startswith((_PNG_SIGNATURE, _JPEG_SIGNATURE)):
        raise ToolError("Las imágenes, firmas y sellos deben ser imágenes PNG o JPG.")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            width, height = probe.size
            orientation = probe.getexif().get(0x0112, 1) if probe.format == "JPEG" else 1
            probe.verify()
    except Exception as exc:  # entrada no confiable: cualquier fallo de parseo = imagen inválida
        raise ToolError("El archivo no es una imagen válida.") from exc
    if width > _MAX_IMAGE_SIDE or height > _MAX_IMAGE_SIDE:
        raise ToolError("La imagen tiene una resolución excesiva.")
    if orientation in range(2, 9):
        # El navegador aplica EXIF; MuPDF no: guardar el mismo giro que muestra la vista previa.
        with user_facing_errors("El archivo no es una imagen válida."), Image.open(io.BytesIO(data)) as probe:
            with ImageOps.exif_transpose(probe) as upright, io.BytesIO() as buffer:
                upright.save(buffer, "JPEG", quality=92)
                return buffer.getvalue()
    return data


def _render(page: pymupdf.Page) -> RenderedPage:
    zoom = min(_PREVIEW_WIDTH / page.rect.width, (_PREVIEW_WIDTH * 1.6) / page.rect.height)
    widgets = list(page.widgets())
    fields = []
    for widget in widgets:
        info = describe_form_field(widget, page.number + 1)
        rect = widget.rect * page.rotation_matrix & page.rect
        if info is None or rect.is_empty:
            continue
        color = widget.text_color
        if color and len(color) == 1:
            color = color * 3
        elif color and len(color) == 4:
            color = [1 - min(1, component + color[3]) for component in color[:3]]
        fields.append({**asdict(info), "size": widget.text_fontsize or 0, "color": color, "font": widget.text_font or "Helv", "rect": {
            "x0": rect.x0 / page.rect.width, "y0": rect.y0 / page.rect.height,
            "x1": rect.x1 / page.rect.width, "y1": rect.y1 / page.rect.height,
        }})
    editable = {field["name"] for field in fields if not field["read_only"]}
    if editable:
        # Vaciar solo una copia de render: evita que el valor anterior quede detrás del nuevo en el SVG.
        with pymupdf.open() as preview:
            preview.insert_pdf(page.parent, from_page=page.number, to_page=page.number, widgets=True)
            background = preview[0]
            for widget in background.widgets():
                if widget.field_name in editable and not (widget.field_flags or 0) & pymupdf.PDF_FIELD_IS_READ_ONLY:
                    widget.field_value = False if widget.field_type in (pymupdf.PDF_WIDGET_TYPE_CHECKBOX, pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON) else ""
                    widget.update()
            background = preview.reload_page(background)
            pixmap = background.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    else:
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    encoded = base64.b64encode(pixmap.tobytes(output="jpeg", jpg_quality=80)).decode("ascii")
    return RenderedPage(
        number=page.number + 1,
        width=page.rect.width,
        height=page.rect.height,
        image=f"data:image/jpeg;base64,{encoded}",
        has_form_fields=bool(widgets),
        fields=fields,
    )
