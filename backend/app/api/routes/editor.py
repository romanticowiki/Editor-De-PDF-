"""Editor visual: rasteriza páginas para editar y aplica las anotaciones recibidas.

Las imágenes/firmas/sellos viajan como archivos PNG/JPG aparte (validados por tamaño y firma de bytes),
no como base64 dentro del JSON: así el payload de anotaciones se mantiene pequeño y se evita
que un base64 gigante agote la memoria.
"""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import ValidationError

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace, scratch_workspace
from app.schemas.editor import MAX_IMAGES, EditorPage, EditorPreview, EditorRequest
from app.services.editor import MAX_IMAGE_BYTES, edit_pdf, editor_font, render_editor_pages

router = APIRouter(prefix="/editor", tags=["editar"])

# El JSON solo lleva coordenadas y texto (sin imágenes): 1 MB es de sobra y acota el consumo.
_MAX_OPERATIONS_JSON = 1_000_000


@router.post("/preview", response_model=EditorPreview)
async def preview_document(file: SingleUpload, settings: SettingsDep, runner: JobRunnerDep) -> EditorPreview:
    with scratch_workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        pages = await runner.run(render_editor_pages, source.path, name=source.display_name)
    return EditorPreview(
        page_count=len(pages),
        has_form_fields=any(p.has_form_fields for p in pages),
        pages=[EditorPage(number=p.number, width=p.width, height=p.height, image=p.image, has_form_fields=p.has_form_fields, fields=p.fields) for p in pages],
    )


@router.get("/font", response_class=Response)
def read_editor_font() -> Response:
    return Response(editor_font(), media_type="font/ttf", headers={"Cache-Control": "public, max-age=86400"})


@router.post("/process", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF editado."))
async def process_document(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    operations: Annotated[str, Form(max_length=_MAX_OPERATIONS_JSON, description='JSON: {"operations": [...]}')],
    images: Annotated[list[UploadFile], File(description="Firmas, sellos o imágenes en PNG o JPG.")] = [],  # noqa: B006 (idioma FastAPI)
) -> FileResponse:
    if len(images) > MAX_IMAGES:
        raise HTTPException(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"Puedes adjuntar hasta {MAX_IMAGES} imágenes.")

    try:
        request = EditorRequest.model_validate_json(operations)
    except ValidationError as exc:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Las anotaciones no son válidas.") from exc

    payloads = [await _read_image(image) for image in images]

    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        count = await runner.run(
            edit_pdf, source.path, output, request=request, images=payloads, name=source.display_name
        )
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix="-editado"),
            workspace=workspace,
            headers={"X-Result-Count": str(count)},
        )


async def _read_image(image: UploadFile) -> bytes:
    # Starlette cuenta los bytes de la parte: rechazamos ANTES de leer, sin gastar memoria.
    if image.size is not None and image.size > MAX_IMAGE_BYTES:
        raise HTTPException(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Una imagen pesa demasiado.")
    data = await image.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Una imagen pesa demasiado.")
    return data
