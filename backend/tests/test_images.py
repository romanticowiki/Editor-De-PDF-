import io
import zipfile

import pymupdf
from fastapi.testclient import TestClient
from PIL import Image

from tests.factories import image_bytes, pdf_bytes, upload

PDF_TO_IMAGES = "/api/v1/convert/pdf-to-images"
IMAGES_TO_PDF = "/api/v1/convert/images-to-pdf"


def page_ratios(content: bytes) -> list[float]:
    with pymupdf.open(stream=content, filetype="pdf") as document:
        return [round(page.rect.width / page.rect.height, 2) for page in document]


def test_single_page_returns_the_image_directly(client: TestClient) -> None:
    response = client.post(
        PDF_TO_IMAGES, files=[upload("folleto.pdf", pdf_bytes())], data={"image_format": "png", "quality": "screen"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert "folleto-pagina-001.png" in response.headers["content-disposition"]
    with Image.open(io.BytesIO(response.content)) as image:
        assert abs(image.width - 595 * 96 / 72) <= 1


def test_multiple_pages_come_in_a_zip(client: TestClient) -> None:
    response = client.post(
        PDF_TO_IMAGES, files=[upload("informe.pdf", pdf_bytes(pages=3))], data={"image_format": "jpg", "quality": "screen"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["x-result-count"] == "3"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == ["informe-pagina-001.jpg", "informe-pagina-002.jpg", "informe-pagina-003.jpg"]


def test_images_to_pdf_keeps_order_and_proportion(client: TestClient) -> None:
    files = [
        upload("ancha.png", image_bytes(400, 200, "PNG"), field="files"),
        upload("alta.jpg", image_bytes(200, 400, "JPEG"), field="files"),
    ]

    response = client.post(IMAGES_TO_PDF, files=files, data={"page_size": "original"})

    assert response.status_code == 200
    assert page_ratios(response.content) == [2.0, 0.5]


def test_images_to_pdf_on_a4_follows_image_orientation(client: TestClient) -> None:
    response = client.post(
        IMAGES_TO_PDF, files=[upload("paisaje.png", image_bytes(400, 200), field="files")], data={"page_size": "a4"}
    )

    assert response.status_code == 200
    assert "paisaje.pdf" in response.headers["content-disposition"]
    assert page_ratios(response.content) == [round(842 / 595, 2)]


def test_images_to_pdf_respects_camera_rotation(client: TestClient) -> None:
    # Orientación EXIF 6: la foto está guardada tumbada y se ve en vertical.
    rotated = image_bytes(400, 200, "JPEG", exif_orientation=6)

    response = client.post(IMAGES_TO_PDF, files=[upload("movil.jpg", rotated, field="files")])

    assert response.status_code == 200
    assert page_ratios(response.content) == [0.5]


def test_images_to_pdf_rejects_non_images(client: TestClient) -> None:
    response = client.post(IMAGES_TO_PDF, files=[upload("foto.png", b"hola", field="files")])

    assert response.status_code == 415
