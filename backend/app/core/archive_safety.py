"""Defensa ante bombas de descompresión (zip bombs).

docx, xlsx, pptx, odt, ods, odp y epub son archivos ZIP por dentro. Un archivo de pocos
kilobytes puede descomprimirse en gigabytes y agotar la memoria del equipo al procesarlo
(MarkItDown, MuPDF, openpyxl…). Antes de tocarlo comprobamos su tamaño ya descomprimido y
su ratio de compresión, leyendo solo el índice del ZIP (no descomprimimos nada aquí).
"""

import zipfile
from enum import StrEnum, auto
from pathlib import Path

from app.core.file_types import FileKind

# Formatos cuya firma es la de un ZIP (ver app/core/file_types.py).
ZIP_BASED_KINDS = frozenset(
    {FileKind.DOCX, FileKind.ODT, FileKind.XLSX, FileKind.ODS, FileKind.PPTX, FileKind.ODP, FileKind.EPUB}
)


class ArchiveRisk(StrEnum):
    TOO_LARGE = auto()  # se descomprime en demasiados datos
    SUSPICIOUS_RATIO = auto()  # ratio de compresión propia de una bomba


def inspect_archive(path: Path, *, max_uncompressed_bytes: int, max_ratio: float) -> ArchiveRisk | None:
    """`None` si el archivo es seguro (o no es un ZIP legible: de eso ya avisa la herramienta)."""
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
    except (zipfile.BadZipFile, OSError):
        # No es un ZIP válido: la propia herramienta lo rechazará con un mensaje claro.
        return None

    uncompressed = sum(info.file_size for info in infos)
    compressed = sum(info.compress_size for info in infos)

    if uncompressed > max_uncompressed_bytes:
        return ArchiveRisk.TOO_LARGE
    # Solo miramos la ratio cuando ya hay bastante contenido: descarta falsos positivos triviales.
    if compressed > 0 and uncompressed > max_uncompressed_bytes // 100 and uncompressed / compressed > max_ratio:
        return ArchiveRisk.SUSPICIOUS_RATIO
    return None
