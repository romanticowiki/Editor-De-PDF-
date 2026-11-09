from dataclasses import asdict
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.api.dependencies import JobRunnerDep, SettingsDep, SingleUpload
from app.api.responses import file_response, file_response_doc, output_filename
from app.api.uploads import receive_upload
from app.core.file_types import PDF_ONLY
from app.core.workspace import Workspace, scratch_workspace
from app.schemas.forms import FORM_VALUES, FormFieldOut, FormFieldsResponse
from app.services.forms import fill_form, list_form_fields

router = APIRouter(prefix="/forms", tags=["editar"])


@router.post("/fields", response_model=FormFieldsResponse)
async def read_form_fields(file: SingleUpload, settings: SettingsDep, runner: JobRunnerDep) -> FormFieldsResponse:
    with scratch_workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        fields = await runner.run(list_form_fields, source.path, name=source.display_name)
    return FormFieldsResponse(fields=[FormFieldOut(**asdict(field)) for field in fields])


@router.post("/fill", response_class=FileResponse, responses=file_response_doc(".pdf", "Formulario rellenado."))
async def fill_form_fields(
    file: SingleUpload,
    settings: SettingsDep,
    runner: JobRunnerDep,
    values: Annotated[str, Form(max_length=500_000, description='JSON: {"campo": "valor" | true}')],
    flatten: Annotated[bool, Form()] = False,
) -> FileResponse:
    try:
        parsed_values = FORM_VALUES.validate_json(values)
    except ValidationError as exc:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Los datos del formulario no son válidos.") from exc

    with Workspace(settings.workspace_dir) as workspace:
        source = await receive_upload(file, workspace, settings, accepted=PDF_ONLY, accept_label="un PDF")
        output = workspace.file("result.pdf")
        await runner.run(fill_form, source.path, output, values=parsed_values, flatten=flatten, name=source.display_name)
        return file_response(
            output,
            filename=output_filename(source.original_name, ".pdf", suffix="-rellenado"),
            workspace=workspace,
        )
