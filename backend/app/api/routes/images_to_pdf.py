from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import JobRunnerDep, SettingsDep
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import display_name, validate_uploads
from app.core.file_types import IMAGES
from app.core.workspace import Workspace
from app.services.images_to_pdf import ImageSource, PageSize, images_to_pdf

router = APIRouter(prefix="/convert/images-to-pdf", tags=["convertir a PDF"])


@router.post("", response_class=FileResponse, responses=file_response_doc(".pdf", "PDF con una página por imagen."))
async def convert_images_to_pdf(
    files: Annotated[list[UploadFile], File(description="Imágenes en el orden de las páginas.")],
    settings: SettingsDep,
    runner: JobRunnerDep,
    page_size: Annotated[PageSize, Form()] = PageSize.ORIGINAL,
) -> FileResponse:
    await validate_uploads(
        files,
        accepted=IMAGES,
        accept_label="una imagen JPG o PNG",
        min_count=1,
        max_count=settings.max_merge_files,
        max_file_bytes=settings.max_upload_file_bytes,
    )
    sources = [ImageSource(name=display_name(upload), stream=upload.file) for upload in files]

    with Workspace(settings.workspace_dir) as workspace:
        output = workspace.file("result.pdf")
        await runner.run(images_to_pdf, sources, output, page_size=page_size)
        filename = output_filename(files[0].filename or "imagen", ".pdf") if len(files) == 1 else "imagenes.pdf"
        return file_response(output, filename=filename, workspace=workspace)
