from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

ClientFactory = Callable[..., TestClient]


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    return tmp_path / "workspaces"


@pytest.fixture
def make_client(workspace_root: Path) -> Iterator[ClientFactory]:
    """Crea clientes con settings a medida; cierra todos al terminar el test."""
    clients: list[TestClient] = []

    def factory(**overrides: object) -> TestClient:
        overrides.setdefault("workspace_dir", workspace_root)
        client = TestClient(create_app(Settings(_env_file=None, **overrides)))  # type: ignore[arg-type]
        client.__enter__()  # dispara el lifespan
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: ClientFactory) -> TestClient:
    return make_client()
