import json

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.services.errors import ToolError
from app.services.page_ranges import parse_page_ranges
from tests.factories import pdf_bytes, upload, zip_pdf_page_counts

SPLIT_URL = "/api/v1/pages/split"
PREVIEW_URL = "/api/v1/pages/preview"
ORGANIZE_URL = "/api/v1/pages/organize"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1-3, 5", [range(0, 3), range(4, 5)]),
        ("8-", [range(7, 10)]),
        ("-2", [range(0, 2)]),
        (" 4 ", [range(3, 4)]),
    ],
)
def test_parses_human_page_ranges(text: str, expected: list[range]) -> None:
    assert parse_page_ranges(text, 10) == expected


@pytest.mark.parametrize("text", ["", "0", "3-1", "11", "a-b", "-", "1--2"])
def test_rejects_invalid_page_ranges(text: str) -> None:
    with pytest.raises(ToolError):
        parse_page_ranges(text, 10)


def test_split_every_page(client: TestClient) -> None:
    response = client.post(SPLIT_URL, files=[upload("doc.pdf", pdf_bytes(pages=3))], data={"mode": "pages"})

    assert response.status_code == 200
    assert "doc-dividido.zip" in response.headers["content-disposition"]
    assert zip_pdf_page_counts(response.content) == {"doc-pagina-1.pdf": 1, "doc-pagina-2.pdf": 1, "doc-pagina-3.pdf": 1}


def test_split_by_ranges(client: TestClient) -> None:
    response = client.post(
        SPLIT_URL, files=[upload("doc.pdf", pdf_bytes(pages=4))], data={"mode": "ranges", "ranges": "1-2, 3"}
    )

    assert zip_pdf_page_counts(response.content) == {"doc-paginas-1-2.pdf": 2, "doc-pagina-3.pdf": 1}


def test_single_range_returns_a_pdf(client: TestClient) -> None:
    response = client.post(
        SPLIT_URL, files=[upload("doc.pdf", pdf_bytes(pages=4))], data={"mode": "ranges", "ranges": "2-3"}
    )

    assert response.headers["content-type"] == "application/pdf"
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        assert document.page_count == 2


def test_split_in_fixed_chunks(client: TestClient) -> None:
    response = client.post(
        SPLIT_URL, files=[upload("doc.pdf", pdf_bytes(pages=5))], data={"mode": "fixed", "chunk_size": "2"}
    )

    assert sorted(zip_pdf_page_counts(response.content).values()) == [1, 2, 2]


def test_split_explains_ranges_outside_the_document(client: TestClient) -> None:
    response = client.post(SPLIT_URL, files=[upload("doc.pdf", pdf_bytes(pages=3))], data={"mode": "ranges", "ranges": "9"})

    assert response.status_code == 422
    assert "3 páginas" in response.json()["detail"]


def test_preview_returns_a_thumbnail_per_page(client: TestClient) -> None:
    response = client.post(PREVIEW_URL, files=[upload("doc.pdf", pdf_bytes(pages=2))])

    assert response.status_code == 200
    body = response.json()
    assert body["page_count"] == 2
    assert body["pages"][0]["thumbnail"].startswith("data:image/jpeg;base64,")


def test_organize_reorders_rotates_and_drops_pages(client: TestClient) -> None:
    pages = json.dumps([{"index": 2, "rotation": 90}, {"index": 0}])

    response = client.post(
        ORGANIZE_URL, files=[upload("doc.pdf", pdf_bytes(pages=3, text="Página"))], data={"pages": pages}
    )

    assert response.status_code == 200
    with pymupdf.open(stream=response.content, filetype="pdf") as document:
        assert document.page_count == 2
        assert "Página 3" in document[0].get_text()
        assert document[0].rotation == 90
        assert "Página 1" in document[1].get_text()


def test_organize_can_extract_pages_as_separate_files(client: TestClient) -> None:
    pages = json.dumps([{"index": 0}, {"index": 2}])

    response = client.post(
        ORGANIZE_URL, files=[upload("doc.pdf", pdf_bytes(pages=3))], data={"pages": pages, "output": "separate"}
    )

    assert zip_pdf_page_counts(response.content) == {"doc-pagina-1.pdf": 1, "doc-pagina-3.pdf": 1}


@pytest.mark.parametrize("pages", ['[{"index": 5}]', "no es json", '[{"index": 0, "rotation": 45}]', "[]"])
def test_organize_rejects_invalid_page_lists(client: TestClient, pages: str) -> None:
    response = client.post(ORGANIZE_URL, files=[upload("doc.pdf", pdf_bytes())], data={"pages": pages})

    assert response.status_code == 422
