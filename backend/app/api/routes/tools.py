"""Qué motores externos hay instalados, para que la interfaz explique (en vez de fallar) lo que falta."""

from fastapi import APIRouter

from app.api.dependencies import OcrEngineDep, OfficeEngineDep, TranslationEngineDep
from app.schemas.tools import EngineStatus, ToolsStatus

router = APIRouter(prefix="/tools", tags=["sistema"])


@router.get("", response_model=ToolsStatus)
async def read_tools_status(
    office_engine: OfficeEngineDep,
    ocr_engine: OcrEngineDep,
    translation_engine: TranslationEngineDep,
) -> ToolsStatus:
    return ToolsStatus(
        engines={
            "office": EngineStatus(available=office_engine is not None, name=office_engine.name if office_engine else None),
            "ocr": EngineStatus(available=ocr_engine is not None, name=ocr_engine.name if ocr_engine else None),
            "translate": EngineStatus(
                available=translation_engine is not None,
                name=translation_engine.name if translation_engine else None,
            ),
        }
    )
