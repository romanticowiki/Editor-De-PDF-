"""Rechaza cuerpos demasiado grandes ANTES de que FastAPI lea y parsee el multipart."""

from http import HTTPStatus

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_METHODS_WITH_BODY = frozenset({"POST", "PUT", "PATCH"})


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _METHODS_WITH_BODY:
            await self.app(scope, receive, send)
            return

        rejection = self._check(Headers(scope=scope).get("content-length"))
        if rejection is None:
            await self.app(scope, receive, send)
            return
        await rejection(scope, receive, send)

    def _check(self, content_length: str | None) -> JSONResponse | None:
        # Sin Content-Length (chunked) no podemos acotar la subida: los navegadores siempre lo envían.
        if content_length is None:
            return _error(HTTPStatus.LENGTH_REQUIRED, "No pudimos leer el tamaño de la subida. Inténtalo de nuevo.")
        if not content_length.isdigit():
            return _error(HTTPStatus.BAD_REQUEST, "La solicitud no es válida.")
        if int(content_length) > self._max_bytes:
            return _error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "Los archivos pesan demasiado para una sola vez. Prueba con menos.",
            )
        return None


def _error(status: HTTPStatus, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})
