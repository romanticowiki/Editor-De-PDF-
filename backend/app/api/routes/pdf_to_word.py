from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.pdf_to_word import pdf_to_word

router = APIRouter(prefix="/convert/pdf-to-word", tags=["convertir desde PDF"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".docx", "Documento de Word."))
async def convert_pdf_to_word(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    allow_partial: Annotated[bool, Form()] = False,
) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.docx")
        await runner.run(pdf_to_word, source.path, output, name=source.display_name, allow_partial=allow_partial)
        suffix = "-parcial" if allow_partial else ""
        return file_response(
            output,
            filename=output_filename(source.original_name, ".docx", suffix=suffix),
            workspace=workspace,
        )
