"""Formularios PDF (AcroForms): listar campos, rellenarlos y, si se pide, aplanarlos."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pymupdf

from app.services.errors import ToolError
from app.services.pdf_io import open_pdf
from app.services.text import strip_control_chars

FieldKind = Literal["text", "checkbox", "radio", "choice"]
FormValue = str | bool

_KIND_BY_WIDGET_TYPE: dict[int, FieldKind] = {
    pymupdf.PDF_WIDGET_TYPE_TEXT: "text",
    pymupdf.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
    pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON: "radio",
    pymupdf.PDF_WIDGET_TYPE_COMBOBOX: "choice",
    pymupdf.PDF_WIDGET_TYPE_LISTBOX: "choice",
}
_OFF_STATES = frozenset({"Off", "", "False", "false"})
_READ_ONLY_FLAG = 1
_MULTILINE_FLAG = 1 << 12


@dataclass(slots=True)
class FormField:
    name: str
    kind: FieldKind
    label: str
    value: FormValue
    options: list[str]
    page: int
    multiline: bool
    max_length: int | None
    read_only: bool


def list_form_fields(source: Path, *, name: str) -> list[FormField]:
    with open_pdf(source, name) as document:
        fields: dict[str, FormField] = {}
        for page in document:
            for widget in page.widgets():
                kind = _KIND_BY_WIDGET_TYPE.get(widget.field_type)
                if kind is None or not widget.field_name:
                    continue
                existing = fields.get(widget.field_name)
                if existing is None:
                    fields[widget.field_name] = _describe(widget, kind, page.number + 1)
                elif kind == "radio":
                    # Cada botón de un grupo es un widget con el mismo nombre: sumamos sus opciones.
                    existing.options.extend(option for option in _options(widget, kind) if option not in existing.options)
                    if _is_on(widget.field_value):
                        existing.value = str(widget.on_state())
        return list(fields.values())


def fill_form(
    source: Path,
    destination: Path,
    *,
    values: Mapping[str, FormValue],
    flatten: bool,
    name: str,
) -> int:
    if not values:
        raise ToolError("Rellena al menos un campo.")

    with open_pdf(source, name) as document:
        has_fields = False
        filled: set[str] = set()
        for page in document:
            for widget in page.widgets():
                kind = _KIND_BY_WIDGET_TYPE.get(widget.field_type)
                if kind is None or not widget.field_name:
                    continue
                has_fields = True
                if widget.field_name not in values or (widget.field_flags or 0) & _READ_ONLY_FLAG:
                    continue
                update_form_field(widget, values[widget.field_name])
                filled.add(widget.field_name)

        if not has_fields:
            raise ToolError(f"«{name}» no tiene campos rellenables.")
        if flatten:
            # Convierte los campos en contenido fijo de la página: ya no se pueden modificar.
            document.bake(annots=False, widgets=True)
        document.save(destination, garbage=3, deflate=True)
    return len(filled)


def _describe(widget: pymupdf.Widget, kind: FieldKind, page_number: int) -> FormField:
    flags = widget.field_flags or 0
    return FormField(
        name=widget.field_name,
        kind=kind,
        label=(widget.field_label or widget.field_name).strip(),
        value=_read_value(widget, kind),
        options=_options(widget, kind),
        page=page_number,
        multiline=kind == "text" and bool(flags & _MULTILINE_FLAG),
        max_length=(widget.text_maxlen or None) if kind == "text" else None,
        read_only=bool(flags & _READ_ONLY_FLAG),
    )


def describe_form_field(widget: pymupdf.Widget, page_number: int) -> FormField | None:
    kind = _KIND_BY_WIDGET_TYPE.get(widget.field_type)
    return _describe(widget, kind, page_number) if kind and widget.field_name else None


def update_form_field(widget: pymupdf.Widget, value: FormValue, *, size: float | None = None) -> None:
    kind = _KIND_BY_WIDGET_TYPE.get(widget.field_type)
    if kind is None or (widget.field_flags or 0) & _READ_ONLY_FLAG:
        raise ToolError("Este campo no se puede editar.")
    if (kind == "checkbox" and not isinstance(value, bool)) or (kind != "checkbox" and not isinstance(value, str)):
        raise ToolError("El valor no corresponde al tipo de campo.")
    _write_value(widget, kind, value)
    if kind in ("text", "choice"):
        widget.text_color = (0, 0, 0)
        if size is not None:
            widget.text_fontsize = size
    widget.update()


def _is_on(value: object) -> bool:
    return value is True or (isinstance(value, str) and value not in _OFF_STATES)


def _read_value(widget: pymupdf.Widget, kind: FieldKind) -> FormValue:
    if kind == "checkbox":
        return _is_on(widget.field_value)
    if kind == "radio":
        return str(widget.on_state()) if _is_on(widget.field_value) else ""
    return "" if widget.field_value in (None, False) else str(widget.field_value)


def _options(widget: pymupdf.Widget, kind: FieldKind) -> list[str]:
    if kind == "radio":
        state = widget.on_state()
        return [str(state)] if state else []
    if kind == "choice":
        # Cada opción puede ser "texto" o ["valor exportado", "texto visible"].
        return [str(choice[0] if isinstance(choice, list | tuple) else choice) for choice in widget.choice_values or []]
    return []


def _write_value(widget: pymupdf.Widget, kind: FieldKind, value: FormValue) -> None:
    match kind:
        case "checkbox":
            widget.field_value = value is True
        case "radio":
            widget.field_value = str(widget.on_state()) == str(value)
        case "choice":
            text = str(value)
            if text and text not in _options(widget, kind):
                label = widget.field_label or widget.field_name
                raise ToolError(f"«{text}» no es una opción válida para «{label}».")
            widget.field_value = text
        case "text":
            text = strip_control_chars(str(value))
            limit = widget.text_maxlen or 0
            widget.field_value = text[:limit] if limit > 0 else text
