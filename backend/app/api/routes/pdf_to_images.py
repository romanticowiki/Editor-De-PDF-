from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import packed_response, packed_response_doc, safe_stem
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace
from app.services.pdf_to_images import ImageFormat, ImageQuality, pdf_to_images

router = APIRouter(prefix="/convert/pdf-to-images", tags=["convertir desde PDF"])


@router.post(
    "",
    response_class=FileResponse,
    responses=packed_response_doc("Una imagen, o un ZIP con una imagen por página.", ".png", ".jpg"),
)
async def convert_pdf_to_images(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    image_format: Annotated[ImageFormat, Form()] = ImageFormat.PNG,
    quality: Annotated[ImageQuality, Form()] = ImageQuality.STANDARD,
) -> FileResponse:
    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        packed = await runner.run(
            pdf_to_images,
            source.path,
            workspace.path,
            image_format=image_format,
            quality=quality,
            stem=safe_stem(source.original_name),
            name=source.display_name,
        )
        return packed_response(packed, workspace=workspace)
