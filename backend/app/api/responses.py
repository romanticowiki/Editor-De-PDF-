"""Respuestas de archivo compartidas: nombre seguro, tipo MIME y limpieza del temporal."""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.workspace import Workspace
from app.services.packaging import PackedOutput

MEDIA_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".md": "text/markdown; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".zip": "application/zip",
}

_UNSAFE_FILENAME_CHARS = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]+')
_MAX_STEM_LENGTH = 80


def safe_stem(source_name: str) -> str:
    """Nombre base apto para archivos de salida: sin rutas ni caracteres reservados."""
    stem = _UNSAFE_FILENAME_CHARS.sub("", Path(source_name).stem).strip(" .") or "documento"
    return stem[:_MAX_STEM_LENGTH]


def output_filename(source_name: str, extension: str, *, suffix: str = "") -> str:
    """`informe.pdf` → `informe-comprimido.pdf`."""
    return f"{safe_stem(source_name)}{suffix}{extension}"


def content_disposition(filename: str) -> str:
    # `filename` ASCII para clientes antiguos; `filename*` (RFC 5987) conserva tildes y eñes.
    fallback = filename.encode("ascii", "ignore").decode().strip() or f"resultado{Path(filename).suffix}"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


def file_response(
    path: Path,
    *,
    filename: str,
    workspace: Workspace,
    headers: Mapping[str, str] | None = None,
) -> FileResponse:
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[path.suffix],
        headers={"Content-Disposition": content_disposition(filename), "Cache-Control": "no-store", **(headers or {})},
        # Se ejecuta cuando el archivo terminó de enviarse.
        background=BackgroundTask(workspace.cleanup),
    )


def packed_response(packed: PackedOutput, *, workspace: Workspace) -> FileResponse:
    """Un resultado suelto o un ZIP; `X-Result-Count` dice cuántos archivos contiene."""
    return file_response(
        packed.path,
        filename=packed.filename,
        workspace=workspace,
        headers={"X-Result-Count": str(packed.count)},
    )


def file_response_doc(extension: str, description: str) -> dict[int | str, dict[str, Any]]:
    """Documenta en OpenAPI que la ruta devuelve un archivo en lugar de JSON."""
    return {200: {"content": {MEDIA_TYPES[extension]: {}}, "description": description}}


def packed_response_doc(description: str, *extensions: str) -> dict[int | str, dict[str, Any]]:
    content = {MEDIA_TYPES[extension]: {} for extension in (*extensions, ".zip")}
    return {200: {"content": content, "description": description}}
