from pathlib import Path

from fastapi.testclient import TestClient

from tests.factories import image_pdf_bytes, pdf_bytes, upload

URL = "/api/v1/compress"


def test_high_level_shrinks_images(client: TestClient) -> None:
    original = image_pdf_bytes()

    response = client.post(URL, files=[upload("foto.pdf", original)], data={"level": "high"})

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert int(response.headers["x-result-size"]) < int(response.headers["x-original-size"]) / 2
    assert "foto-comprimido.pdf" in response.headers["content-disposition"]


def test_never_returns_a_bigger_file(client: TestClient) -> None:
    original = pdf_bytes()

    response = client.post(URL, files=[upload("a.pdf", original)], data={"level": "low"})

    assert response.status_code == 200
    assert len(response.content) <= len(original)


def test_rejects_unknown_level(client: TestClient) -> None:
    response = client.post(URL, files=[upload("a.pdf", pdf_bytes())], data={"level": "extreme"})

    assert response.status_code == 422


def test_rejects_non_pdf(client: TestClient) -> None:
    response = client.post(URL, files=[upload("a.pdf", b"hola")])

    assert response.status_code == 415


def test_removes_temporary_files_after_responding(client: TestClient, workspace_root: Path) -> None:
    client.post(URL, files=[upload("a.pdf", pdf_bytes())])

    assert list(workspace_root.iterdir()) == []
