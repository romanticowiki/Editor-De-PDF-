import io
import zipfile
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pptx import Presentation

import app.services.pdf_to_word as word_service
from tests.factories import locked_pdf_bytes, pdf_bytes, table_pdf_bytes, upload

WORD_URL = "/api/v1/convert/pdf-to-word"
EXCEL_URL = "/api/v1/convert/pdf-to-excel"
POWERPOINT_URL = "/api/v1/convert/pdf-to-powerpoint"


def test_pdf_to_word_keeps_the_text(client: TestClient) -> None:
    response = client.post(WORD_URL, files=[upload("informe.pdf", pdf_bytes(text="Hola mundo"))])

    assert response.status_code == 200
    assert "informe.docx" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as docx:
        assert "Hola mundo" in docx.read("word/document.xml").decode()

    document = Document(io.BytesIO(response.content))
    paragraph = next(paragraph for paragraph in document.paragraphs if "Hola mundo" in paragraph.text)
    paragraph.text = "Texto editado"
    edited = io.BytesIO()
    document.save(edited)
    edited.seek(0)
    assert "Texto editado" in "\n".join(paragraph.text for paragraph in Document(edited).paragraphs)


def test_pdf_to_word_explains_locked_files(client: TestClient) -> None:
    response = client.post(WORD_URL, files=[upload("a.pdf", locked_pdf_bytes())])

    assert response.status_code == 422
    assert "contraseña" in response.json()["detail"]


def test_pdf_to_word_rejects_a_partial_result_and_cleans_the_workspace(
    client: TestClient, workspace_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []

    class PageFailingConverter:
        def __init__(self, _source: str) -> None:
            pass

        def convert(self, destination: str, *, ignore_page_error: bool) -> None:
            calls.append(ignore_page_error)
            Path(destination).write_bytes(b"DOCX parcial")
            raise RuntimeError("fallo simulado en la pagina 2")

        def close(self) -> None:
            pass

    monkeypatch.setattr(word_service, "Converter", PageFailingConverter)

    response = client.post(WORD_URL, files=[upload("informe.pdf", pdf_bytes(pages=2, text="Hola"))])

    assert response.status_code == 422
    assert "incompleto" in response.json()["detail"]
    assert calls == [False]
    assert list(workspace_root.iterdir()) == []


def test_pdf_to_word_partial_retry_is_explicit_and_identified(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []

    class TolerantConverter:
        def __init__(self, _source: str) -> None:
            pass

        def convert(self, destination: str, *, ignore_page_error: bool) -> None:
            calls.append(ignore_page_error)
            Path(destination).write_bytes(b"DOCX parcial")

        def close(self) -> None:
            pass

    monkeypatch.setattr(word_service, "Converter", TolerantConverter)

    response = client.post(
        WORD_URL,
        files=[upload("informe.pdf", pdf_bytes(pages=2, text="Hola"))],
        data={"allow_partial": "true"},
    )

    assert response.status_code == 200
    assert "informe-parcial.docx" in response.headers["content-disposition"]
    assert calls == [True]


def test_pdf_to_excel_extracts_tables_as_typed_cells(client: TestClient) -> None:
    pdf = table_pdf_bytes([["Nombre", "Total"], ["Ana", "42"], ["=1+1", "3.5"]])

    response = client.post(EXCEL_URL, files=[upload("ventas.pdf", pdf)])

    assert response.status_code == 200
    sheet = load_workbook(io.BytesIO(response.content)).worksheets[0]
    values = [[cell.value for cell in row] for row in sheet.iter_rows()]
    assert values == [["Nombre", "Total"], ["Ana", 42], ["=1+1", 3.5]]
    # Una fórmula que viene del PDF queda como texto, nunca se ejecuta.
    assert sheet["A3"].data_type == "s"


def test_pdf_to_excel_falls_back_to_text(client: TestClient) -> None:
    response = client.post(EXCEL_URL, files=[upload("carta.pdf", pdf_bytes(text="Querida Ana"))])

    assert response.status_code == 200
    sheet = load_workbook(io.BytesIO(response.content))["Texto"]
    assert sheet["B2"].value == "Querida Ana"


def test_pdf_to_excel_explains_empty_documents(client: TestClient) -> None:
    response = client.post(EXCEL_URL, files=[upload("vacio.pdf", pdf_bytes())])

    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]


def test_pdf_to_powerpoint_creates_one_slide_per_page(client: TestClient) -> None:
    response = client.post(POWERPOINT_URL, files=[upload("charla.pdf", pdf_bytes(pages=2, text="Diapositiva"))])

    assert response.status_code == 200
    presentation = Presentation(io.BytesIO(response.content))
    assert len(presentation.slides) == 2
    assert "Diapositiva 2" in presentation.slides[1].notes_slide.notes_text_frame.text
