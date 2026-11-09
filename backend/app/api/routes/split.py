from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import packed_response, packed_response_doc, safe_stem
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.split import SplitMode, split_pdf

router = APIRouter(prefix="/pages/split", tags=["organizar"])


@router.post("", response_class=FileResponse, responses=packed_response_doc("Un PDF, o un ZIP con las partes.", ".pdf"))
async def split_document(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    mode: Annotated[SplitMode, Form()] = SplitMode.EVERY_PAGE,
    ranges: Annotated[str | None, Form(max_length=500, description="Solo con mode=ranges. Ej.: 1-3, 5, 8-")] = None,
    chunk_size: Annotated[int | None, Form(ge=1, le=10_000, description="Solo con mode=fixed.")] = None,
) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        packed = await runner.run(
            split_pdf,
            source.path,
            workspace.path,
            mode=mode,
            ranges_text=ranges,
            chunk_size=chunk_size,
            stem=safe_stem(source.original_name),
            name=source.display_name,
        )
        return packed_response(packed, workspace=workspace)
