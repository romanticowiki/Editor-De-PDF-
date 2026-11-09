import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from desktop_server import _wait_for_parent_pipe

BACKEND_DIR = Path(__file__).resolve().parents[1]
# Arrancar el servidor real importa PyMuPDF y compañía: el primer /health tarda unos segundos.
_STARTUP_TIMEOUT_S = 90.0
_SHUTDOWN_TIMEOUT_S = 20.0


def test_parent_pipe_eof_requests_backend_exit() -> None:
    """Sobre un pipe real: al cerrarse el extremo de escritura, el backend pide salir."""
    exit_codes: list[int] = []
    read_fd, write_fd = os.pipe()
    os.close(write_fd)  # el «padre» desaparece
    try:
        _wait_for_parent_pipe(read_fd, exit_codes.append)
    finally:
        os.close(read_fd)

    assert exit_codes == [0]


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_until_healthy(process: subprocess.Popen[bytes], port: int) -> None:
    deadline = time.monotonic() + _STARTUP_TIMEOUT_S
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"El backend terminó durante el arranque (código {process.returncode}).")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            pass
        time.sleep(0.3)
    raise AssertionError("El backend no respondió a /health a tiempo.")


@pytest.mark.skipif(not (BACKEND_DIR / "desktop_server.py").is_file(), reason="Falta desktop_server.py")
def test_running_backend_shuts_down_when_the_parent_pipe_closes() -> None:
    """Regresión del proceso huérfano: si Electron muere, el backend debe apagarse solo.

    Reproduce el canal de vida real (stdin heredado) sobre un servidor en marcha, no sobre un
    buffer simulado: arranca, confirma que atiende, cierra el pipe y exige que el proceso termine.
    """
    port = _free_port()
    environment = {
        **os.environ,
        "PDFEDITOR_PARENT_PIPE": "1",
        "PDFEDITOR_HOST": "127.0.0.1",
        "PDFEDITOR_PORT": str(port),
    }
    process = subprocess.Popen(
        [sys.executable, str(BACKEND_DIR / "desktop_server.py")],
        cwd=str(BACKEND_DIR),
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_until_healthy(process, port)

        assert process.stdin is not None
        process.stdin.close()  # equivale a que Electron desaparezca

        assert process.wait(timeout=_SHUTDOWN_TIMEOUT_S) is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=_SHUTDOWN_TIMEOUT_S)
