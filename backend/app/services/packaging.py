"""Empaquetado de resultados: un solo archivo se entrega tal cual; varios, en un ZIP."""

import itertools
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.services.errors import ToolError


@dataclass(frozen=True, slots=True)
class OutputEntry:
    name: str
    data: bytes


@dataclass(frozen=True, slots=True)
class PackedOutput:
    path: Path
    filename: str
    count: int


def pack_outputs(entries: Iterable[OutputEntry], directory: Path, *, archive_stem: str) -> PackedOutput:
    """Consume `entries` de uno en uno: nunca hay más de dos resultados en memoria."""
    iterator = iter(entries)
    first = next(iterator, None)
    if first is None:
        raise ToolError("No hay nada que exportar.")

    second = next(iterator, None)
    if second is None:
        path = directory / f"single{PurePosixPath(first.name).suffix}"
        path.write_bytes(first.data)
        return PackedOutput(path=path, filename=first.name, count=1)

    path = directory / "result.zip"
    used_names: set[str] = set()
    count = 0
    # PDF e imágenes ya van comprimidos: ZIP_STORED evita gastar CPU sin ahorrar espacio.
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for entry in itertools.chain((first, second), iterator):
            archive.writestr(_unique_name(entry.name, used_names), entry.data)
            count += 1
    return PackedOutput(path=path, filename=f"{archive_stem}.zip", count=count)


def _unique_name(name: str, used_names: set[str]) -> str:
    candidate, original, attempt = name, PurePosixPath(name), 2
    while candidate in used_names:
        candidate = f"{original.stem}-{attempt}{original.suffix}"
        attempt += 1
    used_names.add(candidate)
    return candidate
