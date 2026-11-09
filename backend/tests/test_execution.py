import asyncio
import threading
import time
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.execution import JobRunner
from app.core.workspace import Workspace


def test_timeout_keeps_the_worker_slot_and_workspace_until_the_thread_finishes(tmp_path: Path) -> None:
    running = 0
    peak = 0
    temporaries_present: list[bool] = []
    lock = threading.Lock()

    def work(path: Path) -> None:
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
        time.sleep(0.1)
        temporaries_present.append(path.is_file())
        with lock:
            running -= 1

    async def scenario() -> None:
        runner = JobRunner(max_concurrent=1, timeout_seconds=0.04)
        for _ in range(2):
            with pytest.raises(HTTPException) as error:
                with Workspace(tmp_path) as workspace:
                    source = workspace.file("source.pdf")
                    source.write_bytes(b"PDF test")
                    await runner.run(work, source)
            assert error.value.status_code == 504
            assert not workspace.path.exists()
        await asyncio.sleep(0.15)

    asyncio.run(scenario())
    assert peak == 1
    assert temporaries_present == [True, True]


def test_cancellation_waits_for_the_active_worker() -> None:
    started = threading.Event()
    finished = threading.Event()

    def work() -> None:
        started.set()
        time.sleep(0.08)
        finished.set()

    async def scenario() -> None:
        runner = JobRunner(max_concurrent=1, timeout_seconds=2)
        job = asyncio.create_task(runner.run(work))
        assert await asyncio.to_thread(started.wait, 1)
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job
        assert finished.is_set()
        assert await runner.run(lambda: "next") == "next"

    asyncio.run(scenario())
