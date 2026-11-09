from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.compress import CompressionLevel, compress_pdf

router = APIRouter(prefix="/compress", tags=["optimizar"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF comprimido."))
async def compress_document(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    level: Annotated[CompressionLevel, Form()] = CompressionLevel.MEDIUM,
) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        result = await runner.run(compress_pdf, source.path, output, level=level, name=source.display_name)
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix="-comprimido"),
            workspace=workspace,
            # La interfaz los usa para mostrar cuánto se ahorró.
            headers={"X-Original-Size": str(result.original_bytes), "X-Result-Size": str(result.result_bytes)},
        )
