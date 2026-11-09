import io

from docx import Document
from fastapi.testclient import TestClient
from pptx import Presentation

from tests.factories import pdf_text, upload

URL = "/api/v1/convert/markdown"
MARKDOWN = """# Informe

Texto con **negrita**.

## Datos

- Uno
- Dos

| A | B |
|---|---|
| 1 | 2 |
""".encode()


def test_markdown_to_pdf(client: TestClient) -> None:
    response = client.post(URL, files=[upload("notas.md", MARKDOWN)], data={"target": "pdf"})

    assert response.status_code == 200
    assert "notas.pdf" in response.headers["content-disposition"]
    text = pdf_text(response.content)
    assert "Informe" in text and "negrita" in text and "Uno" in text


def test_markdown_to_word_keeps_structure(client: TestClient) -> None:
    response = client.post(URL, files=[upload("notas.md", MARKDOWN)], data={"target": "docx"})

    assert response.status_code == 200
    document = Document(io.BytesIO(response.content))
    paragraphs = {paragraph.text: paragraph for paragraph in document.paragraphs}
    assert paragraphs["Informe"].style.name == "Heading 1"
    assert paragraphs["Uno"].style.name == "List Bullet"
    assert any(run.bold for run in paragraphs["Texto con negrita."].runs)
    assert document.tables[0].cell(1, 0).text == "1"


def test_markdown_to_powerpoint_makes_a_slide_per_heading(client: TestClient) -> None:
    response = client.post(URL, files=[upload("charla.md", MARKDOWN)], data={"target": "pptx"})

    assert response.status_code == 200
    slides = list(Presentation(io.BytesIO(response.content)).slides)
    assert [slide.shapes.title.text for slide in slides] == ["Informe", "Datos"]
    assert "Uno" in slides[1].placeholders[1].text_frame.text


def test_markdown_rejects_binary_files(client: TestClient) -> None:
    response = client.post(URL, files=[upload("notas.md", b"\x00\x01")], data={"target": "pdf"})

    assert response.status_code == 415
