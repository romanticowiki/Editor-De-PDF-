"""Ejecución acotada de trabajos pesados: concurrencia limitada, tiempo máximo y errores traducidos a HTTP."""

import asyncio
from collections.abc import Callable
from http import HTTPStatus
from typing import ParamSpec, TypeVar

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from app.services.errors import EngineUnavailableError, ToolError

P = ParamSpec("P")
R = TypeVar("R")

TIMEOUT_MESSAGE = "Está tardando demasiado. Prueba con un archivo más pequeño."


class JobRunner:
    def __init__(self, *, max_concurrent: int, timeout_seconds: float) -> None:
        # Evita que varios archivos enormes a la vez agoten CPU y memoria.
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout_seconds = timeout_seconds

    async def run(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return await self._execute(self._timeout_seconds, func, *args, **kwargs)

    async def run_long(self, timeout_seconds: float, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        """Para trabajos que legítimamente tardan más (p. ej. OCR de muchas páginas)."""
        return await self._execute(timeout_seconds, func, *args, **kwargs)

    async def _execute(self, timeout_seconds: float, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        try:
            # El tiempo cuenta desde que se pide turno: esperar en cola también consume el límite.
            async with asyncio.timeout(timeout_seconds), self._semaphore:
                # Las librerías PDF son síncronas y usan CPU: fuera del event loop.
                job = asyncio.create_task(run_in_threadpool(func, *args, **kwargs))
                try:
                    return await asyncio.shield(job)
                except asyncio.CancelledError:
                    # El hilo aún usa el temporal: conservarlo y el turno hasta que termine.
                    await asyncio.gather(job, return_exceptions=True)
                    raise
        except TimeoutError as exc:
            raise HTTPException(HTTPStatus.GATEWAY_TIMEOUT, TIMEOUT_MESSAGE) from exc
        except EngineUnavailableError as exc:
            raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, exc.user_message) from exc
        except ToolError as exc:
            raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, exc.user_message) from exc
