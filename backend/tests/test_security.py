"""Revisión de código seguro: rutas, bombas de descompresión y encapsulamiento de errores."""

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies import get_job_runner
from app.core.archive_safety import ArchiveRisk, inspect_archive
from app.core.config import Settings
from app.main import create_app
from tests.conftest import ClientFactory
from tests.factories import pdf_bytes, upload

COMPRESS_URL = "/api/v1/compress"
MARKDOWN_URL = "/api/v1/convert/to-markdown"


# ——— 1. Sanitización de rutas ———


def test_path_traversal_filename_cannot_escape(client: TestClient) -> None:
    # El nombre del cliente nunca se usa como ruta: se guarda como source.pdf y el
    # nombre de descarga se sanea (sin «../» ni separadores).
    response = client.post(COMPRESS_URL, files=[upload("../../../../etc/passwd.pdf", pdf_bytes(text="hola"))])

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert "passwd-comprimido.pdf" in disposition
    assert "../" not in disposition
    assert "/" not in disposition.split("filename=")[1].split(";")[0].strip('"')


# ——— 2. Bombas de descompresión ———


def _zip_with_zeros(byte_count: int) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", b"\x00" * byte_count)
    return buffer.getvalue()


def test_inspect_archive_flags_oversized(tmp_path: Path) -> None:
    path = tmp_path / "bomba.docx"
    path.write_bytes(_zip_with_zeros(3 * 1024 * 1024))

    assert inspect_archive(path, max_uncompressed_bytes=1024 * 1024, max_ratio=1000) is ArchiveRisk.TOO_LARGE


def test_inspect_archive_flags_suspicious_ratio(tmp_path: Path) -> None:
    path = tmp_path / "bomba.docx"
    # 500 KB de ceros que caben bajo el tope de tamaño pero comprimen muchísimo.
    path.write_bytes(_zip_with_zeros(500 * 1024))

    assert inspect_archive(path, max_uncompressed_bytes=1024 * 1024, max_ratio=50) is ArchiveRisk.SUSPICIOUS_RATIO


def test_inspect_archive_accepts_normal_office_file(tmp_path: Path) -> None:
    from tests.factories import docx_bytes

    path = tmp_path / "normal.docx"
    path.write_bytes(docx_bytes("Título", "Un párrafo con contenido real y suficiente para el índice."))

    assert inspect_archive(path, max_uncompressed_bytes=600 * 1024 * 1024, max_ratio=200) is None


def test_decompression_bomb_is_rejected_before_processing(make_client: ClientFactory) -> None:
    client = make_client(max_archive_uncompressed_mb=1)

    response = client.post(MARKDOWN_URL, files=[upload("bomba.docx", _zip_with_zeros(3 * 1024 * 1024))])

    assert response.status_code == 413
    assert "descomprime" in response.json()["detail"]


# ——— 3. Encapsulamiento de errores (sin fugas en un 500) ———


def test_internal_errors_return_a_generic_message(tmp_path: Path) -> None:
    app = create_app(Settings(_env_file=None, workspace_dir=tmp_path / "ws"))  # type: ignore[arg-type]

    class BoomRunner:
        async def run(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("ruta interna secreta C:/app/detalle")

        async def run_long(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("ruta interna secreta C:/app/detalle")

    app.dependency_overrides[get_job_runner] = lambda: BoomRunner()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(COMPRESS_URL, files=[upload("a.pdf", pdf_bytes(text="hola"))])

    assert response.status_code == 500
    assert response.json() == {"detail": "Algo falló en el motor local. Inténtalo de nuevo."}
    assert "secreta" not in response.text
    assert "C:/app" not in response.text
