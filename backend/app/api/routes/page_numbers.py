from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.page_numbers import NumberPosition, NumberStyle, number_pages

router = APIRouter(prefix="/edit/page-numbers", tags=["editar"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF numerado."))
async def add_page_numbers(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    position: Annotated[NumberPosition, Form()] = NumberPosition.BOTTOM_CENTER,
    style: Annotated[NumberStyle, Form()] = NumberStyle.NUMBER,
) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        await runner.run(number_pages, source.path, output, position=position, style=style, name=source.display_name)
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix="-numerado"),
            workspace=workspace,
        )
