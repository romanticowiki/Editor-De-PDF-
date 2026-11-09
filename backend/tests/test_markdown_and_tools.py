from fastapi.testclient import TestClient

from app.api.dependencies import get_ocr_engine, get_office_engine, get_translation_engine
from tests.factories import docx_bytes, pdf_bytes, upload
from tests.test_to_pdf import FakeOfficeEngine

MARKDOWN_URL = "/api/v1/convert/to-markdown"


def test_word_to_markdown_keeps_structure(client: TestClient) -> None:
    response = client.post(MARKDOWN_URL, files=[upload("informe.docx", docx_bytes("Resumen", "Todo bien."))])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "informe.md" in response.headers["content-disposition"]
    assert "# Resumen" in response.text
    assert "Todo bien." in response.text


def test_pdf_to_markdown(client: TestClient) -> None:
    response = client.post(MARKDOWN_URL, files=[upload("nota.pdf", pdf_bytes(text="Texto importante"))])

    assert response.status_code == 200
    assert "Texto importante" in response.text


def test_markdown_explains_documents_without_text(client: TestClient) -> None:
    response = client.post(MARKDOWN_URL, files=[upload("escaneo.pdf", pdf_bytes())])

    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]


def test_tools_status_reports_engines(client: TestClient) -> None:
    overrides = client.app.dependency_overrides  # type: ignore[attr-defined]
    overrides[get_office_engine] = FakeOfficeEngine
    overrides[get_ocr_engine] = lambda: None
    overrides[get_translation_engine] = lambda: None

    assert client.get("/api/v1/tools").json() == {
        "engines": {
            "office": {"available": True, "name": "Fake Office"},
            "ocr": {"available": False, "name": None},
            "translate": {"available": False, "name": None},
        }
    }


def test_non_ascii_filenames_survive_download(client: TestClient) -> None:
    response = client.post("/api/v1/compress", files=[upload("canción.pdf", pdf_bytes())])

    assert "filename*=UTF-8''canci%C3%B3n-comprimido.pdf" in response.headers["content-disposition"]
