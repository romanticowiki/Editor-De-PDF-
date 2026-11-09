from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.pdf_to_powerpoint import pdf_to_powerpoint

router = APIRouter(prefix="/convert/pdf-to-powerpoint", tags=["convertir desde PDF"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".pptx", "Presentación de PowerPoint."))
async def convert_pdf_to_powerpoint(file: SingleUpload, settings: SettingsDep, runner: JobRunnerDep) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pptx")
        await runner.run(pdf_to_powerpoint, source.path, output, name=source.display_name)
        return file_response(output, filename=output_filename(source.original_name, ".pptx"), workspace=workspace)
