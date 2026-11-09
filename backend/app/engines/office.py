"""Conversión de documentos de oficina a PDF con el software ya instalado en el equipo.

Nada sale del equipo: se usa Microsoft Office (Windows) o LibreOffice, siempre en un
subproceso con tiempo máximo para que un documento problemático no cuelgue el servidor.
"""

import importlib.util
import logging
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Protocol

from app.core.file_types import FileKind
from app.services.errors import EngineUnavailableError, ToolError

logger = logging.getLogger(__name__)

CONVERSION_FAILED_MESSAGE = (
    "No pudimos convertir este documento. Si tiene contraseña, quítala; si no, ábrelo, guárdalo de nuevo y reinténtalo."
)
_TIMEOUT_MESSAGE = "La conversión tardó demasiado. Prueba con un documento más pequeño."

_WORKER_SCRIPT = Path(__file__).with_name("office_com_worker.py")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_STDERR_TAIL_BYTES = 800
# En el ejecutable empaquetado (PyInstaller) no hay intérprete de Python suelto: el propio
# binario se relanza con este parámetro y el arranque lo redirige al worker (ver desktop_server.py).
_FROZEN = getattr(sys, "frozen", False)
OFFICE_WORKER_FLAG = "--office-com-worker"


def _worker_command(app: str, source: Path, output: Path) -> list[str]:
    target = [app, str(source.resolve()), str(output.resolve())]
    if _FROZEN:
        return [sys.executable, OFFICE_WORKER_FLAG, *target]
    return [sys.executable, str(_WORKER_SCRIPT), *target]

_LIBREOFFICE_CANDIDATES = (
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
)

# Qué aplicación de Microsoft Office abre cada formato.
_MS_OFFICE_APP_BY_KIND: dict[FileKind, str] = {
    FileKind.DOCX: "word", FileKind.DOC: "word", FileKind.ODT: "word", FileKind.RTF: "word",
    FileKind.XLSX: "excel", FileKind.XLS: "excel", FileKind.ODS: "excel",
    FileKind.PPTX: "powerpoint", FileKind.PPT: "powerpoint", FileKind.ODP: "powerpoint",
}  # fmt: skip
_MS_OFFICE_PROG_IDS = {"word": "Word.Application", "excel": "Excel.Application", "powerpoint": "PowerPoint.Application"}
_MS_OFFICE_LABELS = {"word": "Word", "excel": "Excel", "powerpoint": "PowerPoint"}


class OfficeEngine(Protocol):
    name: str

    def convert_to_pdf(self, source: Path, kind: FileKind, output_dir: Path) -> Path: ...


class LibreOfficeEngine:
    name = "LibreOffice"

    def __init__(self, executable: Path, timeout_seconds: float) -> None:
        self._executable = executable
        self._timeout_seconds = timeout_seconds

    def convert_to_pdf(self, source: Path, kind: FileKind, output_dir: Path) -> Path:
        # Perfil propio por trabajo: permite conversiones simultáneas y no toca el perfil del usuario.
        profile_uri = (output_dir / "libreoffice-profile").resolve().as_uri()
        command = [
            str(self._executable), "--headless", "--norestore", "--nolockcheck",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to", "pdf", "--outdir", str(output_dir), str(source),
        ]  # fmt: skip
        _run(command, self._timeout_seconds)
        return _expect_output(output_dir / f"{source.stem}.pdf")


class MicrosoftOfficeEngine:
    name = "Microsoft Office"

    def __init__(self, apps: frozenset[str], timeout_seconds: float) -> None:
        self._apps = apps
        self._timeout_seconds = timeout_seconds
        # Una conversión a la vez: cada una arranca una instancia completa de Office.
        self._lock = threading.Lock()

    def convert_to_pdf(self, source: Path, kind: FileKind, output_dir: Path) -> Path:
        app = _MS_OFFICE_APP_BY_KIND[kind]
        if app not in self._apps:
            raise EngineUnavailableError(f"Para convertir este formato necesitas {_MS_OFFICE_LABELS[app]} instalado.")

        output = output_dir / f"{source.stem}.pdf"
        command = _worker_command(app, source, output)
        with self._lock:
            _run(command, self._timeout_seconds)
        return _expect_output(output)


def detect_office_engine(*, timeout_seconds: float, libreoffice_path: Path | None = None) -> OfficeEngine | None:
    """Ruta explícita a LibreOffice > Microsoft Office (mejor fidelidad con .docx/.xlsx/.pptx) > LibreOffice."""
    if libreoffice_path is not None:
        return LibreOfficeEngine(libreoffice_path, timeout_seconds)

    apps = _installed_ms_office_apps()
    if apps:
        return MicrosoftOfficeEngine(apps, timeout_seconds)

    executable = _find_libreoffice()
    return LibreOfficeEngine(executable, timeout_seconds) if executable else None


def _run(command: list[str], timeout_seconds: float) -> None:
    try:
        # subprocess.run mata el proceso si expira el tiempo.
        completed = subprocess.run(
            command, capture_output=True, timeout=timeout_seconds, check=False, creationflags=_NO_WINDOW
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(_TIMEOUT_MESSAGE) from exc
    except OSError as exc:
        raise EngineUnavailableError("No pudimos iniciar el programa de conversión. Comprueba que siga instalado.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr[-_STDERR_TAIL_BYTES:].decode(errors="replace")
        logger.warning("La conversión de Office falló (código %s): %s", completed.returncode, stderr)
        raise ToolError(CONVERSION_FAILED_MESSAGE)


def _expect_output(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise ToolError(CONVERSION_FAILED_MESSAGE)
    return path


def _find_libreoffice() -> Path | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return next((candidate for candidate in _LIBREOFFICE_CANDIDATES if candidate.is_file()), None)


def _installed_ms_office_apps() -> frozenset[str]:
    if sys.platform != "win32" or importlib.util.find_spec("win32com") is None:
        return frozenset()

    import winreg

    installed: set[str] = set()
    for app, prog_id in _MS_OFFICE_PROG_IDS.items():
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\CLSID"):
                installed.add(app)
        except OSError:
            continue
    return frozenset(installed)
