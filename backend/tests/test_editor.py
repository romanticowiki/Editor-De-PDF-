import asyncio
import io
import json

import pymupdf
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes.editor import _read_image
from app.services.editor import MAX_IMAGE_BYTES

from tests.factories import image_bytes, pdf_bytes, pdf_text, upload

PREVIEW_URL = "/api/v1/editor/preview"
PROCESS_URL = "/api/v1/editor/process"


def _process(client: TestClient, pdf: bytes, operations: list[dict], *, images: list[bytes] | None = None):
    files = [upload("doc.pdf", pdf)]
    for i, png in enumerate(images or []):
        files.append(("images", (f"sig{i}.png", png, "image/png")))
    return client.post(PROCESS_URL, data={"operations": json.dumps({"operations": operations})}, files=files)


def _annot_types(content: bytes, page: int = 0) -> list[str]:
    with pymupdf.open(stream=content, filetype="pdf") as document:
        return [annot.type[1] for annot in document[page].annots()]


# ——— Vista previa ———


def test_preview_returns_rasterized_pages_with_dimensions(client: TestClient) -> None:
    response = client.post(PREVIEW_URL, files=[upload("doc.pdf", pdf_bytes(pages=2))])

    assert response.status_code == 200
    body = response.json()
    assert body["page_count"] == 2
    assert body["pages"][0]["image"].startswith("data:image/jpeg;base64,")
    assert body["pages"][0]["width"] > 0 and body["pages"][0]["height"] > 0


# ——— Operaciones ———


def test_add_text_writes_new_text(client: TestClient) -> None:
    response = _process(client, pdf_bytes(), [{"type": "add_text", "page": 0, "x": 72, "y": 72, "text": "Añadido"}])

    assert response.status_code == 200, response.text
    assert "doc-editado.pdf" in response.headers["content-disposition"]
    assert response.headers["x-result-count"] == "1"
    assert "Añadido" in pdf_text(response.content)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_text_matches_preview_coordinates_size_and_color_on_rotated_pages(client: TestClient, rotation: int) -> None:
    with pymupdf.open(stream=pdf_bytes(), filetype="pdf") as source:
        page = source[0]
        original = page.add_highlight_annot(pymupdf.Rect(50, 50, 200, 100))
        original_rect = original.rect
        page.set_rotation(rotation)
        width, height = page.rect.width, page.rect.height
        pdf = source.tobytes()
    response = _process(client, pdf, [{
        "type": "add_text", "page": 0, "x": width - 110, "y": 72,
        "text": "VISIBLE", "size": 20, "color": [1, 0, 0],
    }])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        assert page.rect == pymupdf.Rect(0, 0, width, height)
        assert page.rotation == rotation
        assert tuple(page.first_annot.rect) == pytest.approx(tuple(original_rect), abs=0.001)
        [block] = page.get_text("dict")["blocks"]
        span = block["lines"][0]["spans"][0]
        assert span["text"] == "VISIBLE"
        assert span["size"] == pytest.approx(20)
        assert span["color"] == 0xFF0000
        visible = pymupdf.Rect(span["bbox"]) * page.rotation_matrix
        assert visible.x0 == pytest.approx(width - 110, abs=0.01)
        assert visible.y0 == pytest.approx(72, abs=1)


def test_highlight_and_draw_add_annotations(client: TestClient) -> None:
    ops = [
        {"type": "highlight", "page": 0, "rect": {"x0": 60, "y0": 60, "x1": 300, "y1": 90}},
        {"type": "draw", "page": 0, "strokes": [[[100, 100], [150, 130], [200, 100]]]},
    ]
    response = _process(client, pdf_bytes(text="Hola"), ops)

    assert response.status_code == 200, response.text
    types = _annot_types(response.content)
    assert "Highlight" in types
    assert "Ink" in types


def test_patch_text_removes_original_and_rewrites(client: TestClient) -> None:
    ops = [{"type": "patch_text", "page": 0, "rect": {"x0": 70, "y0": 60, "x1": 400, "y1": 90}, "text": "Nuevo"}]
    response = _process(client, pdf_bytes(text="Secreto"), ops)

    assert response.status_code == 200, response.text
    text = pdf_text(response.content)
    assert "Secreto" not in text
    assert "Nuevo" in text


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_patch_erases_scan_pixels_and_paints_an_opaque_custom_fill(client: TestClient, rotation: int) -> None:
    with pymupdf.open() as source:
        page = source.new_page(width=200, height=200)
        page.insert_image(page.rect, stream=image_bytes(200, 200))
        page.set_rotation(rotation)
        pdf = source.tobytes()
    response = _process(client, pdf, [{
        "type": "patch_text", "page": 0,
        "rect": {"x0": 50, "y0": 50, "x1": 150, "y1": 150},
        "text": "Nuevo", "fill": [0.2, 0.4, 0.6],
    }])

    assert response.status_code == 200, response.text
    assert "Nuevo" in pdf_text(response.content)
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        assert page.get_pixmap().pixel(100, 130) == pytest.approx((51, 102, 153), abs=1)
        assert page.get_pixmap().pixel(25, 25) == (200, 120, 80)
        [embedded] = page.get_images()
        with Image.open(io.BytesIO(document.extract_image(embedded[0])["image"])) as scan:
            assert scan.convert("RGB").getpixel((100, 130)) == (255, 255, 255)
            assert scan.convert("RGB").getpixel((25, 25)) == (200, 120, 80)


def test_add_image_inserts_the_signature(client: TestClient) -> None:
    ops = [{"type": "add_image", "page": 0, "rect": {"x0": 400, "y0": 700, "x1": 520, "y1": 780}, "image": 0}]
    response = _process(client, pdf_bytes(), ops, images=[image_bytes(120, 60, "PNG")])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        assert len(document[0].get_images()) >= 1


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_sticker_is_above_annotations_and_marks_without_destroying_widgets(client: TestClient, rotation: int) -> None:
    with pymupdf.open() as source:
        page = source.new_page(width=300, height=200)
        page.insert_image(page.rect, stream=image_bytes(300, 200))
        original = page.add_rect_annot(pymupdf.Rect(10, 10, 290, 190))
        original.set_colors(fill=(0, 0, 1))
        original.update()
        original_rect = original.rect
        widget = pymupdf.Widget()
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.field_name = "original"
        widget.field_value = "Conservar"
        widget.fill_color = (1, 0, 0)
        widget.rect = pymupdf.Rect(70, 60, 230, 140)
        page.add_widget(widget)
        page.set_rotation(rotation)
        pdf = source.tobytes()
    ops = [
        {"type": "add_image", "page": 0, "rect": {"x0": 50, "y0": 50, "x1": 150, "y1": 150}, "image": 0},
        {"type": "draw", "page": 0, "strokes": [[[50, 50], [60, 60]]], "width": 10, "color": [0, 0, 0]},
        {"type": "highlight", "page": 0, "rect": {"x0": 50, "y0": 50, "x1": 150, "y1": 150}},
    ]
    response = _process(client, pdf, ops, images=[image_bytes(100, 100)])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        # Los campos de formulario conservan su propia capa interactiva; la imagen cubre el resto.
        assert page.get_pixmap().pixel(60, 60) == (200, 120, 80)
        annotations = list(page.annots())
        assert annotations[0].type[1] == "Square"
        assert annotations[0].rect == original_rect
        assert annotations[-1].type[1] == "Stamp"
        assert annotations[-1].rect * page.rotation_matrix == pymupdf.Rect(50, 50, 150, 150)
        [original_widget] = page.widgets()
        assert original_widget.field_name == "original"
        assert original_widget.field_value == "Conservar"
        assert original_widget.rect == pymupdf.Rect(70, 60, 230, 140)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_ink_and_highlight_match_rotated_preview_coordinates(client: TestClient, rotation: int) -> None:
    with pymupdf.open(stream=pdf_bytes(width=300, height=200), filetype="pdf") as source:
        source[0].set_rotation(rotation)
        pdf = source.tobytes()
    response = _process(client, pdf, [
        {"type": "draw", "page": 0, "strokes": [[[20, 30], [80, 40]]]},
        {"type": "highlight", "page": 0, "rect": {"x0": 60, "y0": 60, "x1": 100, "y1": 100}},
    ])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        ink, highlight = list(page.annots())
        visible_stroke = [tuple(pymupdf.Point(point) * page.rotation_matrix) for point in ink.vertices[0]]
        assert visible_stroke == [(20, 30), (80, 40)]
        points = [pymupdf.Point(point) * page.rotation_matrix for point in highlight.vertices]
        assert min(point.x for point in points) == 60
        assert max(point.x for point in points) == 100
        assert min(point.y for point in points) == 60
        assert max(point.y for point in points) == 100


def test_transparent_sticker_is_painted_once_and_keeps_clear_pixels(client: TestClient) -> None:
    with Image.new("RGBA", (100, 100), (200, 120, 80, 128)) as sticker, io.BytesIO() as buffer:
        sticker.putpixel((25, 25), (0, 0, 0, 0))
        sticker.save(buffer, "PNG")
        png = buffer.getvalue()
    response = _process(client, pdf_bytes(width=200, height=200), [{
        "type": "add_image", "page": 0,
        "rect": {"x0": 50, "y0": 50, "x1": 150, "y1": 150}, "image": 0,
    }], images=[png])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        pixmap = document[0].get_pixmap()
        assert pixmap.pixel(100, 100) == pytest.approx((227, 187, 167), abs=3)
        assert pixmap.pixel(75, 75) == (255, 255, 255)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_text_and_sticker_respect_rotated_cropbox_offsets(client: TestClient, rotation: int) -> None:
    with pymupdf.open() as source:
        page = source.new_page(width=300, height=350)
        page.set_cropbox(pymupdf.Rect(50, 70, 250, 270))
        page.set_rotation(rotation)
        pdf = source.tobytes()
    response = _process(client, pdf, [
        {"type": "add_text", "page": 0, "x": 10, "y": 10, "text": "TEST", "size": 20},
        {"type": "add_image", "page": 0, "rect": {"x0": 50, "y0": 50, "x1": 150, "y1": 150}, "image": 0},
    ], images=[image_bytes(100, 100)])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        assert page.rotation == rotation
        assert page.cropbox == pymupdf.Rect(50, 70, 250, 270)
        [word] = page.get_text("words")
        visible = pymupdf.Rect(word[:4]) * page.rotation_matrix
        assert visible.x0 == pytest.approx(10, abs=0.01)
        assert visible.y0 == pytest.approx(10, abs=1)
        assert page.first_annot.rect * page.rotation_matrix == pymupdf.Rect(50, 50, 150, 150)
        assert page.get_pixmap().pixel(100, 100) == (200, 120, 80)


def test_out_of_page_coordinates_are_clamped_not_crashing(client: TestClient) -> None:
    response = _process(client, pdf_bytes(), [{"type": "add_text", "page": 0, "x": 99999, "y": 99999, "text": "X"}])

    assert response.status_code == 200, response.text  # no revienta: se recorta a la página


# ——— Red Team ———


def test_operation_on_missing_page_is_rejected(client: TestClient) -> None:
    response = _process(client, pdf_bytes(), [{"type": "add_text", "page": 50, "x": 10, "y": 10, "text": "X"}])

    assert response.status_code == 422
    assert "página" in response.json()["detail"].lower()


def test_unknown_field_in_operation_is_rejected(client: TestClient) -> None:
    response = _process(client, pdf_bytes(), [{"type": "add_text", "page": 0, "x": 1, "y": 1, "text": "X", "evil": 1}])

    assert response.status_code == 422  # extra="forbid"


def test_too_many_operations_are_rejected(client: TestClient) -> None:
    ops = [{"type": "add_text", "page": 0, "x": 1, "y": 1, "text": "x"}] * 301
    response = _process(client, pdf_bytes(), ops)

    assert response.status_code == 422


def test_ink_with_too_many_points_is_rejected(client: TestClient) -> None:
    huge = [[[float(i), float(i)] for i in range(3001)]]  # supera el tope por trazo
    response = _process(client, pdf_bytes(), [{"type": "draw", "page": 0, "strokes": huge}])

    assert response.status_code == 422


def test_jpeg_image_is_inserted_at_the_requested_rectangle(client: TestClient) -> None:
    ops = [{"type": "add_image", "page": 0, "rect": {"x0": 100, "y0": 120, "x1": 260, "y1": 240}, "image": 0}]
    response = _process(client, pdf_bytes(), ops, images=[image_bytes(80, 60, "JPEG")])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        [image] = document[0].get_image_info()
        assert image["bbox"] == (100, 120, 260, 240)


def test_jpeg_camera_orientation_matches_the_browser_preview(client: TestClient) -> None:
    ops = [{"type": "add_image", "page": 0, "rect": {"x0": 100, "y0": 120, "x1": 220, "y1": 280}, "image": 0}]
    response = _process(client, pdf_bytes(), ops, images=[image_bytes(80, 60, "JPEG", exif_orientation=6)])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        [image] = document[0].get_image_info()
        assert (image["width"], image["height"]) == (60, 80)
        assert image["bbox"] == (100, 120, 220, 280)


def test_unsupported_image_is_rejected(client: TestClient) -> None:
    ops = [{"type": "add_image", "page": 0, "rect": {"x0": 10, "y0": 10, "x1": 80, "y1": 60}, "image": 0}]
    response = _process(client, pdf_bytes(), ops, images=[image_bytes(80, 60, "GIF")])

    assert response.status_code == 422
    assert "PNG" in response.json()["detail"]


def test_corrupt_jpeg_is_rejected_cleanly(client: TestClient) -> None:
    ops = [{"type": "add_image", "page": 0, "rect": {"x0": 10, "y0": 10, "x1": 80, "y1": 60}, "image": 0}]
    response = _process(client, pdf_bytes(), ops, images=[b"\xff\xd8\xffbroken"])

    assert response.status_code == 422
    assert "imagen" in response.json()["detail"].lower()


@pytest.mark.parametrize("image_format", ["PNG", "JPEG"])
def test_image_dimensions_are_still_limited(client: TestClient, image_format: str) -> None:
    ops = [{"type": "add_image", "page": 0, "rect": {"x0": 10, "y0": 10, "x1": 80, "y1": 60}, "image": 0}]
    response = _process(client, pdf_bytes(), ops, images=[image_bytes(6001, 1, image_format)])

    assert response.status_code == 422
    assert "resolución" in response.json()["detail"]


def test_image_read_without_reported_size_is_bounded() -> None:
    with io.BytesIO(b"x" * (MAX_IMAGE_BYTES + 100)) as stream:
        image = UploadFile(stream, size=None, filename="oversized.png")
        with pytest.raises(HTTPException) as error:
            asyncio.run(_read_image(image))
        assert error.value.status_code == 413
        assert stream.tell() == MAX_IMAGE_BYTES + 1


def test_png_and_jpeg_keep_their_uploaded_indices(client: TestClient) -> None:
    ops = [
        {"type": "add_image", "page": 0, "rect": {"x0": 10, "y0": 20, "x1": 90, "y1": 80}, "image": 1},
        {"type": "add_image", "page": 1, "rect": {"x0": 100, "y0": 120, "x1": 220, "y1": 180}, "image": 0},
    ]
    response = _process(client, pdf_bytes(pages=2), ops, images=[image_bytes(120, 60, "PNG"), image_bytes(80, 60, "JPEG")])

    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        for page, dimensions, expected in [(document[0], (80, 60), (10, 20, 90, 80)), (document[1], (120, 60), (100, 120, 220, 180))]:
            [image] = page.get_image_info()
            assert (image["width"], image["height"]) == dimensions
            assert image["bbox"] == expected


def test_corrupt_png_signature_is_rejected_cleanly(client: TestClient) -> None:
    # Firma PNG (firma de bytes correcta) pero cuerpo roto: debe dar 422, nunca un 500.
    broken = b"\x89PNG\r\n\x1a\n" + b"basura que no es un PNG real" * 4
    ops = [{"type": "add_image", "page": 0, "rect": {"x0": 10, "y0": 10, "x1": 80, "y1": 60}, "image": 0}]
    response = _process(client, pdf_bytes(), ops, images=[broken])

    assert response.status_code == 422
    assert "imagen" in response.json()["detail"].lower()


def test_invalid_json_is_rejected(client: TestClient) -> None:
    response = client.post(PROCESS_URL, data={"operations": "no-es-json"}, files=[upload("doc.pdf", pdf_bytes())])

    assert response.status_code == 422


def test_control_characters_in_text_are_stripped(client: TestClient) -> None:
    response = _process(client, pdf_bytes(), [{"type": "add_text", "page": 0, "x": 72, "y": 72, "text": "A\x00\x07B"}])

    assert response.status_code == 200, response.text
    assert "AB" in pdf_text(response.content).replace(" ", "")
