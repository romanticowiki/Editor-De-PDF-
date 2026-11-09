from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep
from app.api.responses import file_response, file_response_doc
from app.api.uploads import display_name, validate_uploads
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.pdf_merge import PdfSource, merge_pdfs

router = APIRouter(prefix="/merge", tags=["organizar"])

OUTPUT_FILENAME = "unido.pdf"
_MIN_FILES = 2


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF unido."))
async def merge_documents(
    files: Annotated[list[UploadFile], File(description="PDFs en el orden en que se unirán.")],
    settings: SettingsDep,
    runner: JobRunnerDep,
) -> FileResponse:
    await validate_uploads(
        files,
        accepted=PDF_ONLY,
        accept_label="un PDF",
        min_count=_MIN_FILES,
        max_count=settings.max_merge_files,
        max_file_bytes=settings.max_upload_file_bytes,
    )
    # pypdf lee directamente de los temporales de subida: no hace falta copiarlos.
    sources = [PdfSource(name=display_name(upload), stream=upload.file) for upload in files]

    with Workspace(settings.workspace_dir) as workspace:
        output = workspace.file(OUTPUT_FILENAME)
        await runner.run(merge_pdfs, sources, output)
        return file_response(output, filename=OUTPUT_FILENAME, workspace=workspace)
