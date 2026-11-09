import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.execution import JobRunner
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.workspace import purge_stale_workspaces
from app.engines.ocr import detect_ocr_engine
from app.engines.office import detect_office_engine
from app.engines.translate import detect_translation_engine
from app.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware

logger = logging.getLogger(__name__)

_UNEXPECTED_ERROR_MESSAGE = "Algo falló en el motor local. Inténtalo de nuevo."


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Último cortafuegos: cualquier fallo no previsto se registra en el servidor, pero al
    cliente solo le llega un mensaje genérico. Nunca se filtran trazas, rutas ni entorno."""
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": _UNEXPECTED_ERROR_MESSAGE})


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.started_at = time.monotonic()
        # Si el servidor se cerró a mitad de un trabajo, no dejamos documentos olvidados en disco.
        if removed := purge_stale_workspaces(settings.workspace_dir):
            logger.info("Eliminados %s trabajos temporales antiguos", removed)
        office, ocr = app.state.office_engine, app.state.ocr_engine
        translate = app.state.translation_engine
        logger.info("Motor de Office: %s", office.name if office else "no disponible")
        logger.info("Motor de OCR: %s", ocr.name if ocr else "no disponible (faltan datos de idioma)")
        logger.info("Motor de traducción: %s", translate.name if translate else "no disponible (sin clave de Groq)")
        logger.info("%s v%s listo en http://%s:%s", settings.app_name, settings.version, settings.host, settings.port)
        yield
        logger.info("%s detenido", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_development else None,
    )

    app.state.job_runner = JobRunner(
        max_concurrent=settings.max_concurrent_jobs,
        timeout_seconds=settings.job_timeout_seconds,
    )
    app.state.office_engine = detect_office_engine(
        timeout_seconds=settings.office_timeout_seconds,
        libreoffice_path=settings.libreoffice_path,
    )
    app.state.ocr_engine = detect_ocr_engine(settings.tessdata_dir)
    app.state.translation_engine = detect_translation_engine(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        timeout_seconds=settings.groq_timeout_seconds,
    )
    # Las rutas leen la misma instancia de Settings que los middlewares (clave en tests).
    app.dependency_overrides[get_settings] = lambda: settings

    app.add_exception_handler(Exception, _handle_unexpected_error)

    # Starlette envuelve en orden inverso: lo último añadido es la capa externa.
    # CORS va fuera para que incluso un 429/413 lleve sus cabeceras y el front pueda leerlo.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Disposition", "Retry-After", "X-Original-Size", "X-Result-Size", "X-Result-Count"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    # La interfaz compilada se sirve al final: solo atiende lo que no reclamó la API.
    # `html=True` entrega index.html en «/»; el enrutado del front es por hash, no necesita fallback.
    if settings.frontend_dist and settings.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
        logger.info("Sirviendo la interfaz desde %s", settings.frontend_dist)

    return app


app = create_app()
