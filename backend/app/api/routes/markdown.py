from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import MARKDOWN_SOURCES
from app.core.workspace import Workspace
from app.services.markdown import to_markdown

router = APIRouter(prefix="/convert/to-markdown", tags=["inteligencia artificial"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".md", "Documento en Markdown."))
async def convert_to_markdown(file: SingleUpload, settings: SettingsDep, runner: JobRunnerDep) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(
            file,
            workspace,
            settings,
            accepted=MARKDOWN_SOURCES,
            accept_label="un PDF, Word, Excel, PowerPoint, HTML, TXT o EPUB",
        )
        output = workspace.file("result.md")
        await runner.run(to_markdown, source.path, output, kind=source.kind, name=source.display_name)
        return file_response(output, filename=output_filename(source.original_name, ".md"), workspace=workspace)
