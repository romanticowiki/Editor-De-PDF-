"""Compresión de PDF con PyMuPDF: reduce imágenes, recorta fuentes y reescribe el archivo sin basura."""

import logging
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pymupdf

from app.services.errors import ToolError
from app.services.pdf_io import open_pdf

logger = logging.getLogger(__name__)


class CompressionLevel(StrEnum):
    LOW = "low"  # sin pérdida: solo limpieza y recompresión
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class _ImageProfile:
    dpi_threshold: int  # solo se tocan imágenes por encima de esta resolución
    dpi_target: int
    quality: int


_IMAGE_PROFILES: dict[CompressionLevel, _ImageProfile | None] = {
    CompressionLevel.LOW: None,
    CompressionLevel.MEDIUM: _ImageProfile(dpi_threshold=200, dpi_target=150, quality=75),
    CompressionLevel.HIGH: _ImageProfile(dpi_threshold=110, dpi_target=96, quality=55),
}


@dataclass(frozen=True, slots=True)
class CompressionResult:
    original_bytes: int
    result_bytes: int


def compress_pdf(source: Path, destination: Path, *, level: CompressionLevel, name: str) -> CompressionResult:
    with open_pdf(source, name) as document:
        profile = _IMAGE_PROFILES[level]
        if profile is not None:
            _downsample_images(document, profile)
        _subset_fonts(document)
        try:
            document.save(
                destination,
                garbage=4,  # elimina objetos huérfanos y fusiona duplicados
                clean=True,
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                use_objstms=1,
            )
        except Exception as exc:
            raise ToolError(f"No pudimos comprimir «{name}». Prueba con otro nivel.") from exc

    original_bytes = source.stat().st_size
    if destination.stat().st_size >= original_bytes:
        # Nunca devolvemos un archivo más pesado que el original.
        shutil.copyfile(source, destination)
    return CompressionResult(original_bytes=original_bytes, result_bytes=destination.stat().st_size)


def _downsample_images(document: pymupdf.Document, profile: _ImageProfile) -> None:
    try:
        document.rewrite_images(
            dpi_threshold=profile.dpi_threshold,
            dpi_target=profile.dpi_target,
            quality=profile.quality,
        )
    except Exception as exc:  # una imagen rara no debe impedir el resto de la compresión
        logger.warning("No se pudieron reducir algunas imágenes: %s", exc)


def _subset_fonts(document: pymupdf.Document) -> None:
    try:
        document.subset_fonts()
    except Exception as exc:  # optimización opcional
        logger.info("No se pudieron recortar las fuentes: %s", exc)
