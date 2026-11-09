"""Punto de entrada de la app de escritorio (lo empaqueta PyInstaller).

Hace tres cosas:
1. Si se le llama con `--office-com-worker`, actúa como el worker de Office y termina
   (en el ejecutable no hay un intérprete de Python suelto al que invocar; ver engines/office.py).
2. Localiza el frontend compilado y los datos de idioma del OCR incluidos en el paquete.
3. Arranca el servidor local (sin recarga) en el host y puerto que indique Electron por entorno.
"""

import os
import sys
from collections.abc import Callable
from pathlib import Path
from threading import Thread


def _run_office_worker() -> int:
    from app.engines.office_com_worker import main

    # main() espera [prog, app, entrada, salida]; aquí llegan tras el flag.
    return main([sys.argv[0], *sys.argv[2:]])


def _bundle_dir() -> Path:
    # PyInstaller extrae los datos incluidos en sys._MEIPASS; en desarrollo, junto a este archivo.
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _resolve_asset(bundled_name: str, dev_relative: Path) -> Path | None:
    bundled = _bundle_dir() / bundled_name
    if bundled.is_dir():
        return bundled
    dev = (Path(__file__).resolve().parent / dev_relative).resolve()
    return dev if dev.is_dir() else None


def _wait_for_parent_pipe(fd: int, exit_process: Callable[[int], object]) -> None:
    """Termina el backend cuando Electron cierra su extremo del pipe de vida.

    Lee del descriptor CRUDO a propósito. Usar `sys.stdin.buffer.read()` retiene el lock interno
    del BufferedReader mientras bloquea, y en Windows eso cuelga la carga de extensiones C durante
    el arranque (numpy/markitdown nunca terminan de importarse) y revienta al cerrar el intérprete
    con «_enter_buffered_busy». Con os.read no hay lock de por medio.
    """
    try:
        while os.read(fd, 1):
            pass
    except OSError:
        # Un pipe roto también significa que el proceso padre ya no puede mantenernos vivo.
        pass
    exit_process(0)


def _start_parent_watchdog() -> None:
    if os.environ.get("PDFEDITOR_PARENT_PIPE") != "1":
        return
    try:
        fd = sys.stdin.fileno()
    except (AttributeError, OSError, ValueError):
        return  # Sin stdin utilizable no hay canal de vida que vigilar.
    Thread(
        target=_wait_for_parent_pipe,
        args=(fd, os._exit),
        name="electron-parent-watchdog",
        daemon=True,
    ).start()


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--office-com-worker":
        return _run_office_worker()

    import uvicorn

    from app.core.config import Settings
    from app.main import create_app

    frontend = _resolve_asset("frontend_dist", Path("../frontend/dist"))
    tessdata = _resolve_asset("tessdata", Path("tessdata"))

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        environment="production",
        frontend_dist=frontend,
        tessdata_dir=tessdata,
    )

    # Electron pasa un puerto libre por entorno; si no, el valor por defecto de Settings.
    host = os.environ.get("PDFEDITOR_HOST", settings.host)
    port = int(os.environ.get("PDFEDITOR_PORT", settings.port))

    application = create_app(settings)

    # El vigilante arranca DESPUÉS de los imports pesados: en Windows, un hilo bloqueado leyendo
    # stdin impide que terminen de cargarse las extensiones C (numpy/markitdown se quedan colgados).
    # Aquí ya está todo importado, así que solo queda esperar a que Electron cierre el pipe.
    _start_parent_watchdog()

    uvicorn.run(application, host=host, port=port, log_level=settings.log_level.lower())
    return 0


if __name__ == "__main__":
    sys.exit(main())
