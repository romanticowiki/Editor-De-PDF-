import json
import re

import pymupdf
import pytest
from fastapi.testclient import TestClient

from tests.factories import pdf_bytes, upload

PREVIEW_URL = "/api/v1/editor/preview"
PROCESS_URL = "/api/v1/editor/process"
FILL_URL = "/api/v1/forms/fill"


@pytest.fixture
def opaque_form() -> bytes:
    with pymupdf.open() as document:
        page = document.new_page(width=300, height=240)
        for name, kind, rect, value, flags, size in [
            ("Equipo", pymupdf.PDF_WIDGET_TYPE_TEXT, (30, 25, 250, 50), "Original", 0, 12),
            ("detalle", pymupdf.PDF_WIDGET_TYPE_TEXT, (30, 65, 250, 105), "Dos líneas", pymupdf.PDF_TX_FIELD_IS_MULTILINE, 10),
            ("pais", pymupdf.PDF_WIDGET_TYPE_COMBOBOX, (30, 120, 140, 140), "Mexico", 0, 10),
            ("bloqueado", pymupdf.PDF_WIDGET_TYPE_TEXT, (160, 120, 260, 140), "Protegido", pymupdf.PDF_FIELD_IS_READ_ONLY, 10),
            ("acepto", pymupdf.PDF_WIDGET_TYPE_CHECKBOX, (30, 170, 37, 177), False, 0, 7),
        ]:
            widget = pymupdf.Widget()
            widget.field_name = name
            widget.field_label = name
            widget.field_type = kind
            widget.rect = pymupdf.Rect(rect)
            widget.field_value = value
            widget.field_flags = flags
            widget.fill_color = (1, 1, 1)
            widget.text_color = (0.65, 0.65, 0.65)
            widget.text_fontsize = size
            if kind == pymupdf.PDF_WIDGET_TYPE_COMBOBOX:
                widget.choice_values = ["Mexico", "Espana"]
            page.add_widget(widget)
        return document.tobytes()


def _process(client: TestClient, pdf: bytes, operations: list[dict]):
    return client.post(PROCESS_URL, files=[upload("formulario.pdf", pdf)], data={
        "operations": json.dumps({"operations": operations}),
    })


def _assert_black_text(document: pymupdf.Document, widget: pymupdf.Widget) -> None:
    assert tuple(widget.text_color) == (0, 0, 0)
    default = document.xref_get_key(widget.xref, "DA")[1]
    assert re.search(r"(?:0(?:\.0+)?\s+){3}rg|0(?:\.0+)?\s+g", default)
    kind, reference = document.xref_get_key(widget.xref, "AP/N")
    assert kind == "xref"
    appearance = document.xref_stream(int(reference.split()[0]))
    assert re.search(rb"BT\s+(?:(?:0(?:\.0+)?\s+){3}rg|0(?:\.0+)?\s+g)", appearance)
    pixmap = document[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=widget.rect)
    assert min(pixmap.samples) < 10


def test_fill_forces_black_text_and_choice_and_preserves_editability_by_default(client: TestClient, opaque_form: bytes) -> None:
    response = client.post(FILL_URL, files=[upload("formulario.pdf", opaque_form)], data={
        "values": json.dumps({"Equipo": "NEGRO", "pais": "Espana"}),
    })

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        widgets = {widget.field_name: widget for widget in page.widgets()}
        assert set(widgets) == {"Equipo", "detalle", "pais", "bloqueado", "acepto"}
        assert document.xref_get_key(widgets["Equipo"].xref, "V") == ("string", "NEGRO")
        assert document.xref_get_key(widgets["pais"].xref, "V") == ("string", "Espana")
        _assert_black_text(document, widgets["Equipo"])
        _assert_black_text(document, widgets["pais"])
        assert widgets["Equipo"].fill_color == [1, 1, 1]
        assert not widgets["Equipo"].field_flags & pymupdf.PDF_FIELD_IS_READ_ONLY
        widgets["Equipo"].field_value = "Editado después"
        widgets["Equipo"].update()
        edited = document.tobytes()
    with pymupdf.open(stream=edited, filetype="pdf") as document:
        assert next(widget for widget in document[0].widgets() if widget.field_name == "Equipo").field_value == "Editado después"


def test_flatten_is_still_available_only_when_explicitly_requested(client: TestClient, opaque_form: bytes) -> None:
    response = client.post(FILL_URL, files=[upload("formulario.pdf", opaque_form)], data={
        "values": json.dumps({"Equipo": "Fijo"}), "flatten": "true",
    })

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        assert list(document[0].widgets()) == []
        assert "Fijo" in document[0].get_text()


@pytest.mark.parametrize("field, value", [("Equipo", "NEGRO"), ("pais", "Espana")])
def test_fill_replaces_inherited_grey_with_black_in_default_and_actual_appearance(
    client: TestClient, opaque_form: bytes, field: str, value: str,
) -> None:
    response = client.post(FILL_URL, files=[upload("formulario.pdf", opaque_form)], data={
        "values": json.dumps({field: value}), "flatten": "false",
    })

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        widget = next(widget for widget in page.widgets() if widget.field_name == field)
        assert widget.field_value == value
        _assert_black_text(document, widget)


@pytest.mark.parametrize("rotation, expected", [
    (0, (30 / 300, 25 / 240, 250 / 300, 50 / 240)),
    (90, (190 / 240, 30 / 300, 215 / 240, 250 / 300)),
    (180, (50 / 300, 190 / 240, 270 / 300, 215 / 240)),
    (270, (25 / 240, 50 / 300, 50 / 240, 270 / 300)),
])
def test_preview_describes_native_fields_in_rotated_normalized_coordinates(
    client: TestClient, opaque_form: bytes, rotation: int, expected: tuple[float, ...],
) -> None:
    with pymupdf.open(stream=opaque_form, filetype="pdf") as document:
        document[0].set_rotation(rotation)
        pdf = document.tobytes()
    response = client.post(PREVIEW_URL, files=[upload("formulario.pdf", pdf)])

    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["has_form_fields"] is True
    assert preview["pages"][0]["has_form_fields"] is True
    fields = {field["name"]: field for field in preview["pages"][0]["fields"]}
    assert fields["Equipo"]["kind"] == "text"
    assert fields["Equipo"]["value"] == "Original"
    assert fields["Equipo"]["size"] == 12
    assert fields["Equipo"]["multiline"] is False
    assert fields["Equipo"]["read_only"] is False
    assert fields["Equipo"]["options"] == []
    rect = fields["Equipo"]["rect"]
    assert (rect["x0"], rect["y0"], rect["x1"], rect["y1"]) == pytest.approx(expected)
    assert fields["detalle"]["multiline"] is True
    assert fields["bloqueado"]["read_only"] is True
    assert fields["pais"]["kind"] == "choice"
    assert fields["pais"]["options"] == ["Mexico", "Espana"]
    assert fields["acepto"]["kind"] == "checkbox"
    assert fields["acepto"]["value"] is False


def test_preview_without_widgets_reports_no_form_fields(client: TestClient) -> None:
    response = client.post(PREVIEW_URL, files=[upload("pagina.pdf", pdf_bytes())])

    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["has_form_fields"] is False
    assert preview["pages"][0]["has_form_fields"] is False
    assert preview["pages"][0]["fields"] == []


def test_editor_updates_opaque_text_widget_in_black_without_flattening(client: TestClient, opaque_form: bytes) -> None:
    response = _process(client, opaque_form, [{
        "type": "set_field", "page": 0, "name": "Equipo", "value": "Equipo QA", "size": 6.5,
    }])

    assert response.status_code == 200, response.text
    assert response.headers["x-result-count"] == "1"
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        widgets = {widget.field_name: widget for widget in document[0].widgets()}
        widget = widgets["Equipo"]
        assert widget.field_value == "Equipo QA"
        assert widget.text_fontsize == 6.5
        assert document.xref_get_key(widget.xref, "V") == ("string", "Equipo QA")
        assert widget.fill_color == [1, 1, 1]
        assert not widget.field_flags & pymupdf.PDF_FIELD_IS_READ_ONLY
        _assert_black_text(document, widget)
        assert len(widgets) == 5


@pytest.mark.parametrize("checked", [True, False])
def test_editor_checkbox_updates_value_appearance_and_pixels(client: TestClient, opaque_form: bytes, checked: bool) -> None:
    response = _process(client, opaque_form, [{
        "type": "set_field", "page": 0, "name": "acepto", "value": checked,
    }])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        widget = next(widget for widget in page.widgets() if widget.field_name == "acepto")
        expected = f"/{widget.on_state()}" if checked else "/Off"
        assert document.xref_get_key(widget.xref, "V") == ("name", expected)
        assert document.xref_get_key(widget.xref, "AS") == ("name", expected)
        kind, reference = document.xref_get_key(widget.xref, f"AP/N/{expected[1:]}")
        assert kind == "xref" and document.xref_stream(int(reference.split()[0]))
        assert not widget.field_flags & pymupdf.PDF_FIELD_IS_READ_ONLY
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(4, 4), clip=widget.rect)
        assert (min(pixmap.samples) < 100) is checked


@pytest.mark.parametrize("name, value", [
    ("bloqueado", "No permitido"), ("inexistente", "Nuevo"),
    ("Equipo", True), ("acepto", "true"), ("Equipo", 12), ("acepto", 1),
    ("pais", "No existe"),
])
def test_editor_rejects_readonly_missing_wrong_type_and_invalid_choice_fields(
    client: TestClient, opaque_form: bytes, name: str, value: object,
) -> None:
    response = _process(client, opaque_form, [{"type": "set_field", "page": 0, "name": name, "value": value}])

    assert response.status_code == 422


@pytest.mark.parametrize("operation", [
    {"type": "add_text", "page": 0, "x": 40, "y": 30, "text": "Oculto"},
    {"type": "draw", "page": 0, "strokes": [[[40, 35], [80, 35]]]},
])
def test_free_marks_over_opaque_fields_are_rejected_instead_of_silently_hidden(
    client: TestClient, opaque_form: bytes, operation: dict,
) -> None:
    response = _process(client, opaque_form, [operation])

    assert response.status_code == 422
    assert "formulario" in response.json()["detail"].lower() or "campo" in response.json()["detail"].lower()


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_textbox_wraps_all_characters_within_rotated_cropbox(client: TestClient, rotation: int) -> None:
    text = "Descripción ágil con acentos y varias palabras que deben permanecer completas dentro del recuadro."
    with pymupdf.open() as document:
        page = document.new_page(width=300, height=350)
        page.set_cropbox(pymupdf.Rect(50, 70, 250, 270))
        page.set_rotation(rotation)
        pdf = document.tobytes()
    rect = {"x0": 10, "y0": 20, "x1": 190, "y1": 140}
    response = _process(client, pdf, [{
        "type": "add_textbox", "page": 0, "rect": rect, "text": text, "size": 12, "color": [1, 0, 0],
    }])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        assert page.rotation == rotation
        assert page.cropbox == pymupdf.Rect(50, 70, 250, 270)
        lines = [line for block in page.get_text("dict")["blocks"] if block["type"] == 0 for line in block["lines"]]
        assert len(lines) >= 2
        extracted = " ".join("".join(span["text"] for span in line["spans"]) for line in lines)
        assert " ".join(extracted.split()) == text
        for line in lines:
            for span in line["spans"]:
                assert span["size"] == pytest.approx(12)
                assert span["color"] == 0xFF0000
                visible = pymupdf.Rect(span["bbox"]) * page.rotation_matrix
                assert visible.x0 >= rect["x0"] - 0.1
                assert visible.y0 >= rect["y0"] - 0.1
                assert visible.x1 <= rect["x1"] + 0.1
                assert visible.y1 <= rect["y1"] + 0.1


def test_textbox_overflow_is_rejected_without_silently_losing_characters(client: TestClient) -> None:
    response = _process(client, pdf_bytes(width=200, height=200), [{
        "type": "add_textbox", "page": 0, "rect": {"x0": 180, "y0": 180, "x1": 199, "y1": 199},
        "text": "Este texto largo no puede caber en una caja diminuta.", "size": 22,
    }])

    assert response.status_code == 422
    assert any(word in response.json()["detail"].lower() for word in ("cabe", "espacio", "caja"))


def test_existing_point_text_operation_keeps_working(client: TestClient) -> None:
    response = _process(client, pdf_bytes(), [{
        "type": "add_text", "page": 0, "x": 72, "y": 72, "text": "Punto original", "size": 16,
    }])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        assert "Punto original" in document[0].get_text()


def test_free_ink_around_fields_is_not_rejected_by_its_overall_bounding_box(client: TestClient, opaque_form: bytes) -> None:
    response = _process(client, opaque_form, [{"type": "draw", "page": 0, "width": 1,
        "strokes": [[[20, 20], [270, 20], [270, 190], [20, 190], [20, 20]]]}])
    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        assert len(list(page.widgets())) == 5
        assert page.first_annot.type[1] == "Ink"


def test_textbox_handles_inherited_page_resources(client: TestClient) -> None:
    with pymupdf.open() as document:
        page = document.new_page(width=300, height=200)
        page.insert_text((10, 15), "Original")
        resources = document.xref_get_key(page.xref, "Resources")[1]
        parent = int(document.xref_get_key(page.xref, "Parent")[1].split()[0])
        document.xref_set_key(parent, "Resources", resources)
        document.xref_set_key(page.xref, "Resources", "null")
        pdf = document.tobytes()
    response = _process(client, pdf, [{"type": "add_textbox", "page": 0,
        "rect": {"x0": 20, "y0": 40, "x1": 280, "y1": 120}, "text": "Nuevo con recursos heredados", "size": 12}])
    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        assert "Original" in document[0].get_text()
        assert "Nuevo con recursos heredados" in document[0].get_text()


def test_editor_font_is_a_real_font_from_the_same_origin(client: TestClient) -> None:
    response = client.get("/api/v1/editor/font")
    assert response.status_code == 200
    assert response.headers["content-type"] == "font/ttf"
    assert response.content[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"ttcf")
