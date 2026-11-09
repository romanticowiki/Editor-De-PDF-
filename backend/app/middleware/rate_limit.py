"""Rate limiting por IP con ventana deslizante, sin dependencias externas.

Se implementa como middleware ASGI puro (no BaseHTTPMiddleware) para no
bufferizar el cuerpo de las respuestas: importante cuando devolvamos PDFs.
"""

import math
import time
from collections import deque
from collections.abc import Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

Clock = Callable[[], float]


class SlidingWindowLimiter:
    # Tope de claves antes de purgar: evita que el dict crezca sin límite.
    _MAX_TRACKED_KEYS = 1024

    def __init__(self, limit: int, window_seconds: float, clock: Clock = time.monotonic) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> float | None:
        """Registra un intento. Devuelve None si se permite o los segundos a esperar."""
        # Sin `await` dentro: en el event loop esta operación es atómica.
        now = self._clock()
        if len(self._hits) >= self._MAX_TRACKED_KEYS:
            self._purge_expired(now)

        timestamps = self._hits.setdefault(key, deque())
        self._drop_expired(timestamps, now)

        if len(timestamps) >= self._limit:
            return self._window - (now - timestamps[0])

        timestamps.append(now)
        return None

    def _drop_expired(self, timestamps: deque[float], now: float) -> None:
        while timestamps and now - timestamps[0] >= self._window:
            timestamps.popleft()

    def _purge_expired(self, now: float) -> None:
        for key in list(self._hits):
            self._drop_expired(self._hits[key], now)
            if not self._hits[key]:
                del self._hits[key]


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, *, limit: int, window_seconds: float) -> None:
        self.app = app
        self._limiter = SlidingWindowLimiter(limit, window_seconds)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        retry_after = self._limiter.hit(client[0] if client else "unknown")

        if retry_after is None:
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            status_code=429,
            content={"detail": "Vas muy rápido. Espera un momento y vuelve a intentarlo."},
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )
        await response(scope, receive, send)
