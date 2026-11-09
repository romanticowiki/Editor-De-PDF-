import io

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from tests.conftest import ClientFactory

MERGE_URL = "/api/v1/merge"


def make_pdf(width: float, *, password: str | None = None) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=200)
    if password:
        writer.encrypt(password)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def upload(name: str, content: bytes) -> tuple[str, tuple[str, bytes, str]]:
    return ("files", (name, content, "application/pdf"))


def test_merges_in_the_given_order(client: TestClient) -> None:
    response = client.post(MERGE_URL, files=[upload("b.pdf", make_pdf(300)), upload("a.pdf", make_pdf(100))])

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="unido.pdf"' in response.headers["content-disposition"]
    reader = PdfReader(io.BytesIO(response.content))
    assert [float(page.mediabox.width) for page in reader.pages] == [300, 100]


def test_requires_at_least_two_files(client: TestClient) -> None:
    response = client.post(MERGE_URL, files=[upload("a.pdf", make_pdf(100))])

    assert response.status_code == 422
    assert "al menos 2" in response.json()["detail"]


def test_rejects_files_that_are_not_pdf(client: TestClient) -> None:
    response = client.post(MERGE_URL, files=[upload("a.pdf", make_pdf(100)), upload("fake.pdf", b"hola")])

    assert response.status_code == 415
    assert "fake.pdf" in response.json()["detail"]


def test_rejects_password_protected_pdf(client: TestClient) -> None:
    response = client.post(
        MERGE_URL,
        files=[upload("a.pdf", make_pdf(100)), upload("locked.pdf", make_pdf(100, password="secret"))],
    )

    assert response.status_code == 422
    assert "contraseña" in response.json()["detail"]


def test_rejects_corrupt_pdf(client: TestClient) -> None:
    response = client.post(MERGE_URL, files=[upload("a.pdf", make_pdf(100)), upload("broken.pdf", b"%PDF-1.7 roto")])

    assert response.status_code == 422
    assert "broken.pdf" in response.json()["detail"]


def test_rejects_too_many_files(make_client: ClientFactory) -> None:
    client = make_client(max_merge_files=2)
    pdf = make_pdf(100)

    response = client.post(MERGE_URL, files=[upload(f"{i}.pdf", pdf) for i in range(3)])

    assert response.status_code == 422


def test_rejects_oversized_body_before_parsing(make_client: ClientFactory) -> None:
    client = make_client(max_merge_files=2, max_upload_file_mb=1)
    big = b"%PDF-" + b"0" * (4 * 1024 * 1024)

    response = client.post(MERGE_URL, files=[upload("a.pdf", big), upload("b.pdf", big)])

    assert response.status_code == 413
