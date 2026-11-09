from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.watermark import WatermarkLayout, WatermarkOpacity, watermark_pdf

router = APIRouter(prefix="/edit/watermark", tags=["editar"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF con marca de agua."))
async def add_watermark(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    text: Annotated[str, Form(min_length=1, max_length=80)],
    layout: Annotated[WatermarkLayout, Form()] = WatermarkLayout.DIAGONAL,
    opacity: Annotated[WatermarkOpacity, Form()] = WatermarkOpacity.MEDIUM,
) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        await runner.run(
            watermark_pdf, source.path, output, text=text, layout=layout, opacity=opacity, name=source.display_name
        )
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix="-marca-de-agua"),
            workspace=workspace,
        )
