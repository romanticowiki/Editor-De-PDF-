"""Carpetas temporales por trabajo.

Los archivos solo existen mientras dura la petición: se borran al terminar de enviar
la respuesta y, si algo se interrumpe, se purgan al arrancar el servidor.
"""

import logging
import shutil
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import IO, Self

logger = logging.getLogger(__name__)

_JOB_PREFIX = "job-"
_COPY_CHUNK_BYTES = 1024 * 1024
STALE_AFTER_SECONDS = 60 * 60


class Workspace:
    """Uso: `with Workspace(root) as workspace:`. Si el bloque falla, se limpia al salir;
    si termina bien, la limpieza la programa la respuesta (ver `file_response`)."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        # mkdtemp crea la carpeta accesible solo para el usuario actual.
        self.path = Path(tempfile.mkdtemp(prefix=_JOB_PREFIX, dir=root))

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.cleanup()

    def file(self, name: str) -> Path:
        return self.path / name

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


@contextmanager
def scratch_workspace(root: Path) -> Iterator[Workspace]:
    """Para respuestas JSON: no hay archivo que enviar, así que se limpia siempre al salir."""
    workspace = Workspace(root)
    try:
        yield workspace
    finally:
        workspace.cleanup()


def copy_stream(source: IO[bytes], target: Path) -> None:
    source.seek(0)
    with target.open("wb") as destination:
        shutil.copyfileobj(source, destination, _COPY_CHUNK_BYTES)


def purge_stale_workspaces(root: Path, *, max_age_seconds: float = STALE_AFTER_SECONDS) -> int:
    if not root.is_dir():
        return 0

    cutoff = time.time() - max_age_seconds
    removed = 0
    for entry in root.glob(f"{_JOB_PREFIX}*"):
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
                removed += 1
        except OSError:
            logger.debug("No se pudo revisar %s", entry)
    return removed
