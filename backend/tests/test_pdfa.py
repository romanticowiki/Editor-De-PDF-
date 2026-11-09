import io

import pikepdf
from fastapi.testclient import TestClient

from tests.factories import locked_pdf_bytes, pdf_bytes, upload

URL = "/api/v1/convert/pdf-to-pdfa"


def test_adds_pdfa_metadata_and_output_intent(client: TestClient) -> None:
    response = client.post(URL, files=[upload("contrato.pdf", pdf_bytes())])

    assert response.status_code == 200
    assert "contrato-pdfa.pdf" in response.headers["content-disposition"]
    with pikepdf.open(io.BytesIO(response.content)) as pdf:
        metadata = pdf.open_metadata()
        assert metadata["pdfaid:part"] == "2"
        assert metadata["pdfaid:conformance"] == "B"
        assert pdf.Root.OutputIntents[0].S == pikepdf.Name("/GTS_PDFA1")
        assert not pdf.is_encrypted


def test_rejects_non_embedded_fonts_with_guidance(client: TestClient) -> None:
    response = client.post(URL, files=[upload("a.pdf", pdf_bytes(text="Hola"))])

    assert response.status_code == 422
    assert "fuentes sin incrustar" in response.json()["detail"]


def test_rejects_password_protected_pdf(client: TestClient) -> None:
    response = client.post(URL, files=[upload("a.pdf", locked_pdf_bytes())])

    assert response.status_code == 422
    assert "contraseña" in response.json()["detail"]
