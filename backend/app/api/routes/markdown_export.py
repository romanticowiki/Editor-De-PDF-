from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import MEDIA_TYPES, file_response, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import MARKDOWN_ONLY
from app.core.workspace import Workspace
from app.services.markdown_export import MarkdownTarget, export_markdown

router = APIRouter(prefix="/convert/markdown", tags=["inteligencia artificial"])

_RESPONSES = {
    200: {
        "content": {MEDIA_TYPES[f".{target}"]: {} for target in MarkdownTarget},
        "description": "Documento generado a partir del Markdown.",
    }
}


@router.post("", response_class=FileResponse, responses=_RESPONSES)
async def convert_markdown(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    target: Annotated[MarkdownTarget, Form()],
) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=MARKDOWN_ONLY, accept_label="un archivo Markdown")
        extension = f".{target}"
        output = workspace.file(f"result{extension}")
        await runner.run(export_markdown, source.path, output, target=target, name=source.display_name)
        return file_response(output, filename=output_filename(source.original_name, extension), workspace=workspace)
