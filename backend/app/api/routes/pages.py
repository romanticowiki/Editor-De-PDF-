"""Editor visual de páginas: miniaturas y aplicación de la lista final (girar, eliminar, extraer, reordenar)."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import packed_response, packed_response_doc, safe_stem
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace, scratch_workspace
from app.schemas.pages import PAGE_INSTRUCTIONS, PagePreview, PagesPreview
from app.services.organize import OrganizeOutput, PageInstruction, organize_pdf
from app.services.thumbnails import render_thumbnails

router = APIRouter(prefix="/pages", tags=["organizar"])


@router.post("/preview", response_model=PagesPreview)
async def preview_pages(file: SingleUpload, settings: SettingsDep, runner: JobRunnerDep) -> PagesPreview:
    with scratch_workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        thumbnails = await runner.run(render_thumbnails, source.path, name=source.display_name)

    return PagesPreview(
        page_count=len(thumbnails),
        pages=[
            PagePreview(number=number, width=thumb.width, height=thumb.height, thumbnail=thumb.data_url)
            for number, thumb in enumerate(thumbnails, start=1)
        ],
    )


@router.post("/organize", response_class=FileResponse, responses=packed_response_doc("PDF resultante.", ".pdf"))
async def organize_pages(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    pages: Annotated[str, Form(max_length=200_000, description='JSON: [{"index": 0, "rotation": 90}, …]')],
    output: Annotated[OrganizeOutput, Form()] = OrganizeOutput.SINGLE,
) -> FileResponse:
    instructions = _parse_instructions(pages)

    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        packed = await runner.run(
            organize_pdf,
            source.path,
            workspace.path,
            instructions=instructions,
            output=output,
            stem=safe_stem(source.original_name),
            name=source.display_name,
        )
        return packed_response(packed, workspace=workspace)


def _parse_instructions(raw: str) -> list[PageInstruction]:
    try:
        parsed = PAGE_INSTRUCTIONS.validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY, "La lista de páginas no es válida. Vuelve a cargar el documento."
        ) from exc
    return [PageInstruction(index=item.index, rotation=item.rotation) for item in parsed]
