"""Imágenes JPG/PNG a PDF: sin recomprimir, con su proporción y respetando la rotación de la cámara."""

import io
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO

import pymupdf
from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.errors import ToolError
from app.services.pdf_io import user_facing_errors


class PageSize(StrEnum):
    ORIGINAL = "original"  # la página adopta la proporción de la imagen
    A4 = "a4"  # la imagen se encaja en un A4 con márgenes


@dataclass(frozen=True, slots=True)
class ImageSource:
    name: str
    stream: BinaryIO


@dataclass(frozen=True, slots=True)
class _PreparedImage:
    data: bytes
    width: int
    height: int


_EXIF_ORIENTATION_TAG = 0x0112
_UPRIGHT = 1
_SCREEN_DPI = 96
_A4 = pymupdf.paper_rect("a4")
_A4_LONG_SIDE = max(_A4.width, _A4.height)
_A4_MARGIN_POINTS = 36
_REENCODE_JPEG_QUALITY = 92


def images_to_pdf(sources: Sequence[ImageSource], destination: Path, *, page_size: PageSize) -> None:
    with pymupdf.open() as document:
        for source in sources:
            image = _prepare(source)
            page_rect = _page_rect(image, page_size)
            with user_facing_errors(f"«{source.name}» no se pudo añadir. Prueba a guardarla de nuevo."):
                page = document.new_page(width=page_rect.width, height=page_rect.height)
                target = page.rect
                if page_size is PageSize.A4:
                    margin = _A4_MARGIN_POINTS
                    target = page.rect + (margin, margin, -margin, -margin)
                # El JPG se incrusta tal cual: sin pérdida adicional de calidad.
                page.insert_image(target, stream=image.data, keep_proportion=True)
        document.save(destination, garbage=3, deflate=True)


def _prepare(source: ImageSource) -> _PreparedImage:
    source.stream.seek(0)
    data = source.stream.read()
    try:
        with Image.open(io.BytesIO(data)) as image:
            orientation = image.getexif().get(_EXIF_ORIENTATION_TAG, _UPRIGHT)
            if orientation == _UPRIGHT:
                return _PreparedImage(data=data, width=image.width, height=image.height)

            # Las cámaras guardan la foto "tumbada" y anotan cómo girarla: aplicamos ese giro.
            upright = ImageOps.exif_transpose(image)
            buffer = io.BytesIO()
            if image.format == "PNG":
                upright.save(buffer, "PNG")
            else:
                upright.convert("RGB").save(buffer, "JPEG", quality=_REENCODE_JPEG_QUALITY)
            return _PreparedImage(data=buffer.getvalue(), width=upright.width, height=upright.height)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise ToolError(f"«{source.name}» no es una imagen válida o es demasiado grande.") from exc


def _page_rect(image: _PreparedImage, page_size: PageSize) -> pymupdf.Rect:
    if page_size is PageSize.A4:
        landscape = image.width > image.height
        return pymupdf.Rect(0, 0, _A4.height, _A4.width) if landscape else pymupdf.Rect(_A4)

    width = image.width * 72 / _SCREEN_DPI
    height = image.height * 72 / _SCREEN_DPI
    # Una foto de móvil (4000 px) daría una página de 1 metro: la acotamos al lado largo de un A4.
    scale = min(1.0, _A4_LONG_SIDE / max(width, height))
    return pymupdf.Rect(0, 0, width * scale, height * scale)
