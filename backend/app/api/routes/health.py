import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def read_health(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    uptime = time.monotonic() - request.app.state.started_at
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.version,
        uptime_seconds=round(uptime, 2),
    )
