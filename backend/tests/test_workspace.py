import os
import time
from pathlib import Path

import pytest

from app.core.workspace import STALE_AFTER_SECONDS, Workspace, purge_stale_workspaces


def test_cleans_up_when_the_block_fails(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError), Workspace(tmp_path) as workspace:
        workspace.file("x.pdf").write_bytes(b"x")
        raise RuntimeError

    assert not workspace.path.exists()


def test_keeps_files_when_the_block_succeeds(tmp_path: Path) -> None:
    with Workspace(tmp_path) as workspace:
        workspace.file("x.pdf").write_bytes(b"x")

    assert workspace.path.exists()


def test_purges_only_stale_workspaces(tmp_path: Path) -> None:
    stale = Workspace(tmp_path).path
    fresh = Workspace(tmp_path).path
    old = time.time() - STALE_AFTER_SECONDS - 60
    os.utime(stale, (old, old))

    assert purge_stale_workspaces(tmp_path) == 1
    assert not stale.exists()
    assert fresh.exists()
