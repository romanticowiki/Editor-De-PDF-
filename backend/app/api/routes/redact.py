from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.redact import RedactionFill, redact_pdf

router = APIRouter(prefix="/security/redact", tags=["seguridad"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF censurado."))
async def redact_document(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    terms: Annotated[str, Form(min_length=1, max_length=5000, description="Un texto por línea.")],
    fill: Annotated[RedactionFill, Form()] = RedactionFill.BLACK,
) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        result = await runner.run(redact_pdf, source.path, output, terms_text=terms, fill=fill, name=source.display_name)
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix="-censurado"),
            workspace=workspace,
            headers={"X-Result-Count": str(result.matches)},
        )
