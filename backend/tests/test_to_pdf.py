import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_office_engine
from app.core.file_types import FileKind
from app.engines.office import detect_office_engine
from tests.conftest import ClientFactory
from tests.factories import docx_bytes, epub_bytes, pdf_bytes, pdf_text, upload

OFFICE_URL = "/api/v1/convert/office-to-pdf"
DOCUMENT_URL = "/api/v1/convert/document-to-pdf"


class FakeOfficeEngine:
    name = "Fake Office"

    def __init__(self) -> None:
        self.calls: list[FileKind] = []

    def convert_to_pdf(self, source: Path, kind: FileKind, output_dir: Path) -> Path:
        self.calls.append(kind)
        output = output_dir / f"{source.stem}.pdf"
        output.write_bytes(pdf_bytes())
        return output


def test_office_to_pdf_uses_the_installed_engine(client: TestClient) -> None:
    engine = FakeOfficeEngine()
    client.app.dependency_overrides[get_office_engine] = lambda: engine  # type: ignore[attr-defined]

    response = client.post(OFFICE_URL, files=[upload("carta.docx", docx_bytes("Hola", "Texto"))])

    assert response.status_code == 200
    assert "carta.pdf" in response.headers["content-disposition"]
    assert engine.calls == [FileKind.DOCX]


def test_office_to_pdf_explains_missing_engine(client: TestClient) -> None:
    client.app.dependency_overrides[get_office_engine] = lambda: None  # type: ignore[attr-defined]

    response = client.post(OFFICE_URL, files=[upload("carta.docx", docx_bytes("Hola", "Texto"))])

    assert response.status_code == 503
    assert "Office" in response.json()["detail"]


def test_office_to_pdf_rejects_disguised_files(client: TestClient) -> None:
    client.app.dependency_overrides[get_office_engine] = FakeOfficeEngine  # type: ignore[attr-defined]

    response = client.post(OFFICE_URL, files=[upload("carta.docx", pdf_bytes())])

    assert response.status_code == 415


@pytest.mark.skipif(os.environ.get("PDF_LOCAL_OFFICE_TESTS") != "1", reason="Abre Office de verdad: PDF_LOCAL_OFFICE_TESTS=1")
def test_office_to_pdf_with_real_engine(make_client: ClientFactory) -> None:
    client = make_client()
    if detect_office_engine(timeout_seconds=120) is None:
        pytest.skip("No hay Office ni LibreOffice instalado.")

    response = client.post(OFFICE_URL, files=[upload("carta.docx", docx_bytes("Informe anual", "Todo en orden."))])

    assert response.status_code == 200, response.text
    assert "Informe anual" in pdf_text(response.content)


def test_txt_to_pdf_keeps_windows_accents(client: TestClient) -> None:
    content = "Canción de prueba\nSegunda línea".encode("cp1252")

    response = client.post(DOCUMENT_URL, files=[upload("notas.txt", content)])

    assert response.status_code == 200
    assert "Canción de prueba" in pdf_text(response.content)


def test_html_to_pdf(client: TestClient) -> None:
    content = "<html><body><h1>Título</h1><p>Párrafo</p></body></html>".encode()

    response = client.post(DOCUMENT_URL, files=[upload("pagina.html", content)])

    assert response.status_code == 200
    assert "Párrafo" in pdf_text(response.content)


def test_epub_to_pdf(client: TestClient) -> None:
    response = client.post(DOCUMENT_URL, files=[upload("libro.epub", epub_bytes("Capítulo uno", "Había una vez"))])

    assert response.status_code == 200
    assert "Había una vez" in pdf_text(response.content)


def test_document_to_pdf_rejects_binary_disguised_as_text(client: TestClient) -> None:
    response = client.post(DOCUMENT_URL, files=[upload("notas.txt", b"\x00\x01\x02")])

    assert response.status_code == 415
