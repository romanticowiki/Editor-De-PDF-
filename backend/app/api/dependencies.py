"""Dependencias compartidas por las rutas. En tests se sustituyen con `app.dependency_overrides`."""

from typing import Annotated

from fastapi import Depends, File, Request, UploadFile

from app.api.execution import JobRunner
from app.core.config import Settings, get_settings
from app.engines.ocr import OcrEngine
from app.engines.office import OfficeEngine
from app.engines.translate import TranslationEngine


def get_job_runner(request: Request) -> JobRunner:
    runner: JobRunner = request.app.state.job_runner
    return runner


def get_office_engine(request: Request) -> OfficeEngine | None:
    engine: OfficeEngine | None = request.app.state.office_engine
    return engine


def get_ocr_engine(request: Request) -> OcrEngine | None:
    engine: OcrEngine | None = request.app.state.ocr_engine
    return engine


def get_translation_engine(request: Request) -> TranslationEngine | None:
    engine: TranslationEngine | None = request.app.state.translation_engine
    return engine


SettingsDep = Annotated[Settings, Depends(get_settings)]
JobRunnerDep = Annotated[JobRunner, Depends(get_job_runner)]
OfficeEngineDep = Annotated[OfficeEngine | None, Depends(get_office_engine)]
OcrEngineDep = Annotated[OcrEngine | None, Depends(get_ocr_engine)]
TranslationEngineDep = Annotated[TranslationEngine | None, Depends(get_translation_engine)]
SingleUpload = Annotated[UploadFile, File(description="Archivo a procesar.")]
