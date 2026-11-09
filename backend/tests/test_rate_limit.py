import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.middleware.rate_limit import SlidingWindowLimiter
from tests.conftest import ClientFactory


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_limiter_blocks_after_limit_and_recovers() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=2, window_seconds=10, clock=clock)

    assert limiter.hit("a") is None
    assert limiter.hit("a") is None
    assert limiter.hit("a") == pytest.approx(10)

    clock.now = 10
    assert limiter.hit("a") is None


def test_limiter_isolates_keys() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=10, clock=FakeClock())

    assert limiter.hit("a") is None
    assert limiter.hit("b") is None


def test_limiter_purges_idle_keys() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=1, window_seconds=1, clock=clock)
    for i in range(SlidingWindowLimiter._MAX_TRACKED_KEYS):
        limiter.hit(f"ip-{i}")

    clock.now = 5
    limiter.hit("new")

    assert len(limiter._hits) == 1


def test_middleware_returns_429_with_retry_after(make_client: ClientFactory) -> None:
    client = make_client(rate_limit_requests=2)

    client.get("/api/v1/health")
    client.get("/api/v1/health")
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_settings_reject_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=["*"])
