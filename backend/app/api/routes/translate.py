"""Traducir un PDF a otro idioma conservando el diseño en lo posible.

Aviso: esta herramienta envía el texto del documento a un servicio externo (Groq). Solo
está activa si hay una clave configurada en el entorno (`PDFEDITOR_GROQ_API_KEY`).
"""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload, TranslationEngineDep
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.translate import TranslateLanguage, translate_pdf

router = APIRouter(prefix="/translate", tags=["editar"])

ENGINE_MISSING_MESSAGE = "La traducción no está configurada en este equipo (falta la clave de Groq en el .env)."


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF traducido."))
async def translate_document(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    engine: TranslationEngineDep,
    source_lang: Annotated[TranslateLanguage, Form()],
    target_lang: Annotated[TranslateLanguage, Form()],
    consent: Annotated[bool, Form()] = False,
) -> FileResponse:
    if not consent:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Debes aceptar que el texto del documento se envíe a Groq para traducirlo.",
        )
    if engine is None:
        raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, ENGINE_MISSING_MESSAGE)

    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        result = await runner.run_long(
            settings.translate_timeout_seconds,
            translate_pdf,
            source.path,
            output,
            engine=engine,
            source_lang=source_lang,
            target_lang=target_lang,
            name=source.display_name,
        )
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix=f"-{target_lang.value}"),
            workspace=workspace,
            headers={"X-Result-Count": str(result.blocks_translated)},
        )
