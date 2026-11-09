"""Recepción y validación de archivos subidos, compartida por todas las herramientas."""

from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.archive_safety import ZIP_BASED_KINDS, ArchiveRisk, inspect_archive
from app.core.config import Settings
from app.core.file_types import FILE_KINDS, FileKind, detect_kind
from app.core.workspace import Workspace, copy_stream

# Suficiente para cualquier firma, incluida la del PDF (puede no estar en el byte 0).
_HEAD_BYTES = 1024
_MAX_DISPLAY_NAME_LENGTH = 80
_BYTES_PER_MB = 1024 * 1024

_ARCHIVE_RISK_MESSAGES = {
    ArchiveRisk.TOO_LARGE: "«{name}» se descomprime en demasiados datos. Puede estar dañado o manipulado.",
    ArchiveRisk.SUSPICIOUS_RATIO: "«{name}» tiene una compresión sospechosa, así que no lo procesamos.",
}


@dataclass(frozen=True, slots=True)
class ReceivedFile:
    path: Path
    kind: FileKind
    display_name: str
    original_name: str


def display_name(upload: UploadFile) -> str:
    name = upload.filename or "Archivo sin nombre"
    if len(name) <= _MAX_DISPLAY_NAME_LENGTH:
        return name
    return f"{name[: _MAX_DISPLAY_NAME_LENGTH - 1]}…"


async def validate_uploads(
    uploads: Sequence[UploadFile],
    *,
    accepted: frozenset[FileKind],
    accept_label: str,
    min_count: int,
    max_count: int,
    max_file_bytes: int,
) -> list[FileKind]:
    """Valida cantidad, tamaño y formato real. Devuelve el formato detectado de cada archivo."""
    _check_count(len(uploads), min_count, max_count)
    return [await _validate_upload(upload, accepted, accept_label, max_file_bytes) for upload in uploads]


async def receive_upload(
    upload: UploadFile,
    workspace: Workspace,
    settings: Settings,
    *,
    accepted: frozenset[FileKind],
    accept_label: str,
) -> ReceivedFile:
    """Valida un único archivo y lo guarda en el espacio de trabajo con un nombre controlado."""
    [kind] = await validate_uploads(
        [upload],
        accepted=accepted,
        accept_label=accept_label,
        min_count=1,
        max_count=1,
        max_file_bytes=settings.max_upload_file_bytes,
    )
    # Nunca usamos el nombre del cliente como ruta: evita path traversal y nombres reservados.
    path = workspace.file(f"source{FILE_KINDS[kind].canonical_extension}")
    await run_in_threadpool(copy_stream, upload.file, path)
    if kind in ZIP_BASED_KINDS:
        await _reject_archive_bombs(path, settings, display_name(upload))
    return ReceivedFile(path=path, kind=kind, display_name=display_name(upload), original_name=upload.filename or "")


async def _reject_archive_bombs(path: Path, settings: Settings, name: str) -> None:
    risk = await run_in_threadpool(
        inspect_archive,
        path,
        max_uncompressed_bytes=settings.max_archive_uncompressed_bytes,
        max_ratio=settings.max_archive_ratio,
    )
    if risk is not None:
        # El Workspace de la ruta se limpia solo al propagarse la excepción (ver su __exit__).
        raise HTTPException(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, _ARCHIVE_RISK_MESSAGES[risk].format(name=name))


def _check_count(count: int, min_count: int, max_count: int) -> None:
    if count < min_count:
        message = "Añade un archivo para empezar." if min_count == 1 else f"Añade al menos {min_count} archivos."
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, message)
    if count > max_count:
        message = (
            "Esta herramienta trabaja con un archivo a la vez."
            if max_count == 1
            else f"Puedes procesar hasta {max_count} archivos a la vez."
        )
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, message)


async def _validate_upload(
    upload: UploadFile,
    accepted: frozenset[FileKind],
    accept_label: str,
    max_file_bytes: int,
) -> FileKind:
    name = display_name(upload)

    if upload.size is not None and upload.size > max_file_bytes:
        raise HTTPException(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            f"«{name}» supera el límite de {max_file_bytes // _BYTES_PER_MB} MB.",
        )

    head = await upload.read(_HEAD_BYTES)
    await upload.seek(0)
    if not head:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, f"«{name}» está vacío.")

    kind = detect_kind(upload.filename, head, accepted)
    if kind is None:
        raise HTTPException(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, f"«{name}» no es {accept_label}.")
    return kind
