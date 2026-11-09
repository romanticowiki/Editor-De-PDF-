from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import READING_DOCUMENTS
from app.core.workspace import Workspace
from app.services.document_to_pdf import document_to_pdf

router = APIRouter(prefix="/convert/document-to-pdf", tags=["convertir a PDF"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF generado."))
async def convert_document_to_pdf(file: SingleUpload, settings: SettingsDep, runner: JobRunnerDep) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(
            file, workspace, settings, accepted=READING_DOCUMENTS, accept_label="un archivo TXT, HTML o EPUB"
        )
        output = workspace.file("result.pdf")
        await runner.run(document_to_pdf, source.path, output, kind=source.kind, name=source.display_name)
        return file_response(output, filename=output_filename(source.original_name, ".pdf"), workspace=workspace)
