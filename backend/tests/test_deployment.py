from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_docker_compose_publishes_the_api_on_loopback_only() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '"127.0.0.1:8000:8000"' in compose
    assert '"8000:8000"' not in compose


def test_docker_frontend_build_uses_supported_node_runtime() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:24-slim AS frontend" in dockerfile
    assert "FROM node:20-slim AS frontend" not in dockerfile


def test_desktop_build_uses_node_locks_without_installing_python_packages() -> None:
    build = (ROOT / "scripts" / "build-desktop.ps1").read_text(encoding="utf-8")
    frontend_setup = (ROOT / "scripts" / "setup-frontend.ps1").read_text(encoding="utf-8")

    assert build.count("npm ci --no-fund --no-audit") == 2
    assert "npm install" not in build
    assert "pip install" not in build
    assert "npm ci --no-fund --no-audit" in frontend_setup
    assert "$expectedDistDesktop" in build
    assert "La ruta de salida no es segura" in build
    assert "verify-electron-package.js" in build


def test_electron_keeps_a_lifecycle_pipe_open_for_the_backend() -> None:
    main = (ROOT / "electron" / "main.js").read_text(encoding="utf-8")

    assert 'PDFEDITOR_PARENT_PIPE: "1"' in main
    assert 'stdio: ["pipe", "ignore", "ignore"]' in main
