import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_ocr_engine
from app.core.config import get_settings
from app.engines.ocr import RecognizedWord, detect_ocr_engine
from app.services.ocr import inject_invisible_words
from tests.factories import pdf_bytes, pdf_text, scanned_pdf_bytes, upload

URL = "/api/v1/ocr"
# Motor real si el equipo tiene los datos de idioma (scripts\setup-ocr.ps1).
REAL_ENGINE = detect_ocr_engine(get_settings().tessdata_dir)


def first_page_pixels(content: bytes) -> bytes:
    with pymupdf.open(stream=content, filetype="pdf") as document:
        return bytes(document[0].get_pixmap(dpi=72).samples)


@pytest.mark.skipif(REAL_ENGINE is None, reason="Sin datos de idioma de Tesseract (scripts/setup-ocr.ps1).")
def test_real_tesseract_makes_a_scan_searchable_without_changing_it(client: TestClient) -> None:
    client.app.dependency_overrides[get_ocr_engine] = lambda: REAL_ENGINE  # type: ignore[attr-defined]
    scan = scanned_pdf_bytes("Factura 2026 pagada")
    assert pdf_text(scan).strip() == ""

    response = client.post(URL, files=[upload("escaneo.pdf", scan)], data={"language": "spa"})

    assert response.status_code == 200, response.text
    text = pdf_text(response.content)
    assert "Factura" in text
    assert "2026" in text
    # La capa de texto es invisible: la página se ve exactamente igual.
    assert first_page_pixels(response.content) == first_page_pixels(scan)


class FakeOcrEngine:
    name = "Fake OCR"

    def __init__(self) -> None:
        self.languages: list[str] = []

    def recognize(self, page: pymupdf.Page, *, language: str, dpi: int) -> list[RecognizedWord]:
        self.languages.append(language)
        return [
            RecognizedWord(pymupdf.Rect(72, 72, 220, 96), "Factura"),
            RecognizedWord(pymupdf.Rect(230, 72, 300, 96), "2026"),
        ]


def test_invisible_words_are_searchable_but_do_not_change_the_page() -> None:
    with pymupdf.open() as document:
        page = document.new_page()
        before = page.get_pixmap().samples

        inject_invisible_words(page, [RecognizedWord(pymupdf.Rect(72, 72, 220, 96), "Factura")])

        assert "Factura" in page.get_text()
        assert page.get_pixmap().samples == before


def test_ocr_adds_searchable_text_to_scanned_pages(client: TestClient) -> None:
    engine = FakeOcrEngine()
    client.app.dependency_overrides[get_ocr_engine] = lambda: engine  # type: ignore[attr-defined]

    response = client.post(URL, files=[upload("escaneo.pdf", pdf_bytes())], data={"language": "spa+eng"})

    assert response.status_code == 200
    assert "escaneo-ocr.pdf" in response.headers["content-disposition"]
    assert response.headers["x-result-count"] == "1"
    text = pdf_text(response.content)
    assert "Factura" in text and "2026" in text
    assert engine.languages == ["spa+eng"]


def test_ocr_skips_pages_that_already_have_text(client: TestClient) -> None:
    client.app.dependency_overrides[get_ocr_engine] = FakeOcrEngine  # type: ignore[attr-defined]

    response = client.post(URL, files=[upload("digital.pdf", pdf_bytes(text="Este documento ya tiene texto real"))])

    assert response.status_code == 422


def test_ocr_explains_missing_language_data(client: TestClient) -> None:
    client.app.dependency_overrides[get_ocr_engine] = lambda: None  # type: ignore[attr-defined]

    response = client.post(URL, files=[upload("escaneo.pdf", pdf_bytes())])

    assert response.status_code == 503
    assert "Tesseract" in response.json()["detail"]
