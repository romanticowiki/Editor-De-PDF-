import json

import pymupdf
from fastapi.testclient import TestClient

from tests.factories import form_pdf_bytes, pdf_bytes, pdf_text, upload

WATERMARK_URL = "/api/v1/edit/watermark"
NUMBERS_URL = "/api/v1/edit/page-numbers"
REDACT_URL = "/api/v1/security/redact"
FIELDS_URL = "/api/v1/forms/fields"
FILL_URL = "/api/v1/forms/fill"


def page_texts(content: bytes) -> list[str]:
    with pymupdf.open(stream=content, filetype="pdf") as document:
        return [page.get_text() for page in document]


# Marca de agua y numeración


def test_watermark_is_drawn_on_every_page(client: TestClient) -> None:
    response = client.post(
        WATERMARK_URL,
        files=[upload("contrato.pdf", pdf_bytes(pages=2))],
        data={"text": "CONFIDENCIAL", "layout": "diagonal", "opacity": "medium"},
    )

    assert response.status_code == 200
    assert "contrato-marca-de-agua.pdf" in response.headers["content-disposition"]
    assert all("CONFIDENCIAL" in text for text in page_texts(response.content))


def test_watermark_requires_visible_text(client: TestClient) -> None:
    response = client.post(WATERMARK_URL, files=[upload("a.pdf", pdf_bytes())], data={"text": "   "})

    assert response.status_code == 422


def test_watermark_explains_unsupported_characters(client: TestClient) -> None:
    response = client.post(WATERMARK_URL, files=[upload("a.pdf", pdf_bytes())], data={"text": "機密"})

    assert response.status_code == 422
    assert "alfabeto latino" in response.json()["detail"]


def test_page_numbers_show_the_position_in_the_document(client: TestClient) -> None:
    response = client.post(
        NUMBERS_URL,
        files=[upload("a.pdf", pdf_bytes(pages=3))],
        data={"position": "bottom-right", "style": "page-of-total"},
    )

    assert response.status_code == 200
    assert "Página 2 de 3" in page_texts(response.content)[1]


# Censura


def test_redaction_removes_the_text_for_real(client: TestClient) -> None:
    response = client.post(
        REDACT_URL,
        files=[upload("expediente.pdf", pdf_bytes(text="DNI 12345678 de Ana"))],
        data={"terms": "12345678\nAna", "fill": "black"},
    )

    assert response.status_code == 200
    assert "expediente-censurado.pdf" in response.headers["content-disposition"]
    assert response.headers["x-result-count"] == "2"
    text = pdf_text(response.content)
    assert "12345678" not in text
    assert "Ana" not in text
    assert "DNI" in text


def test_redaction_explains_when_nothing_matches(client: TestClient) -> None:
    response = client.post(REDACT_URL, files=[upload("a.pdf", pdf_bytes(text="Hola"))], data={"terms": "Pedro"})

    assert response.status_code == 422
    assert "No encontramos" in response.json()["detail"]


def test_redaction_rejects_terms_that_are_too_short(client: TestClient) -> None:
    response = client.post(REDACT_URL, files=[upload("a.pdf", pdf_bytes(text="Hola"))], data={"terms": "a"})

    assert response.status_code == 422


# Formularios


def test_lists_fillable_fields(client: TestClient) -> None:
    response = client.post(FIELDS_URL, files=[upload("solicitud.pdf", form_pdf_bytes())])

    assert response.status_code == 200
    fields = {field["name"]: field for field in response.json()["fields"]}
    assert fields["nombre"]["kind"] == "text"
    assert fields["nombre"]["label"] == "Nombre completo"
    assert fields["acepto"]["kind"] == "checkbox"
    assert fields["pais"]["options"] == ["México", "España"]


def test_plain_pdf_has_no_fields(client: TestClient) -> None:
    response = client.post(FIELDS_URL, files=[upload("a.pdf", pdf_bytes())])

    assert response.json() == {"fields": []}


def test_fills_and_flattens_the_form(client: TestClient) -> None:
    values = json.dumps({"nombre": "Ana Pérez", "acepto": True, "pais": "España"})

    response = client.post(FILL_URL, files=[upload("solicitud.pdf", form_pdf_bytes())], data={"values": values, "flatten": "true"})

    assert response.status_code == 200
    assert "solicitud-rellenado.pdf" in response.headers["content-disposition"]
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        page = document[0]
        assert list(page.widgets()) == []
        assert "Ana Pérez" in page.get_text()


def test_fills_without_flattening_keeps_fields_editable(client: TestClient) -> None:
    values = json.dumps({"nombre": "Ana"})

    response = client.post(
        FILL_URL, files=[upload("solicitud.pdf", form_pdf_bytes())], data={"values": values, "flatten": "false"}
    )

    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        widgets = {widget.field_name: widget.field_value for widget in document[0].widgets()}
    assert widgets["nombre"] == "Ana"


def test_rejects_options_that_do_not_exist(client: TestClient) -> None:
    response = client.post(
        FILL_URL, files=[upload("solicitud.pdf", form_pdf_bytes())], data={"values": json.dumps({"pais": "Chile"})}
    )

    assert response.status_code == 422
    assert "Chile" in response.json()["detail"]


def test_rejects_malformed_values(client: TestClient) -> None:
    response = client.post(FILL_URL, files=[upload("solicitud.pdf", form_pdf_bytes())], data={"values": "{"})

    assert response.status_code == 422


def test_explains_filling_a_pdf_without_fields(client: TestClient) -> None:
    response = client.post(FILL_URL, files=[upload("a.pdf", pdf_bytes())], data={"values": json.dumps({"x": "y"})})

    assert response.status_code == 422
    assert "no tiene campos" in response.json()["detail"]
