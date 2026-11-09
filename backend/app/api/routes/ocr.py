from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, OcrEngineDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.ocr import OcrLanguage, ocr_pdf

router = APIRouter(prefix="/ocr", tags=["editar"])

ENGINE_MISSING_MESSAGE = "Para el OCR faltan los datos de idioma de Tesseract en este equipo."


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF con texto buscable."))
async def recognize_text(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    engine: OcrEngineDep,
    language: Annotated[OcrLanguage, Form()] = OcrLanguage.SPANISH,
) -> FileResponse:
    if engine is None:
        raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, ENGINE_MISSING_MESSAGE)

    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        result = await runner.run_long(
            settings.ocr_timeout_seconds,
            ocr_pdf,
            source.path,
            output,
            engine=engine,
            language=language,
            name=source.display_name,
        )
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix="-ocr"),
            workspace=workspace,
            headers={"X-Result-Count": str(result.pages_recognized)},
        )
