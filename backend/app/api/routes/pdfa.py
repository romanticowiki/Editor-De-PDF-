from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.pdfa import convert_to_pdfa

router = APIRouter(prefix="/convert/pdf-to-pdfa", tags=["optimizar"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF/A-2b."))
async def convert_pdf_to_pdfa(file: SingleUpload, settings: SettingsDep, runner: JobRunnerDep) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        await runner.run(convert_to_pdfa, source.path, output, name=source.display_name)
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix="-pdfa"),
            workspace=workspace,
        )
