from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, OfficeEngineDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import OFFICE_DOCUMENTS
from app.core.workspace import Workspace

router = APIRouter(prefix="/convert/office-to-pdf", tags=["convertir a PDF"])

ENGINE_MISSING_MESSAGE = "Para convertir documentos de Office necesitas Microsoft Office o LibreOffice en este equipo."


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF generado."))
async def convert_office_to_pdf(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    engine: OfficeEngineDep,
) -> FileResponse:
    # Se comprueba antes de recibir el archivo: no tiene sentido guardarlo si no podemos convertirlo.
    if engine is None:
        raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, ENGINE_MISSING_MESSAGE)

    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(
            file, workspace, settings, accepted=OFFICE_DOCUMENTS, accept_label="un documento de Office"
        )
        output_dir = workspace.file("out")
        output_dir.mkdir()
        output = await runner.run(engine.convert_to_pdf, source.path, source.kind, output_dir)
        return file_response(output, filename=output_filename(source.original_name, ".pdf"), workspace=workspace)
