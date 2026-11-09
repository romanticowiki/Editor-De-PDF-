from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, TypeAdapter


class FormFieldOut(BaseModel):
    name: str
    kind: Literal["text", "checkbox", "radio", "choice"]
    label: str
    value: str | bool
    options: list[str]
    page: int
    multiline: bool
    max_length: int | None
    read_only: bool


class FormFieldsResponse(BaseModel):
    fields: list[FormFieldOut]


_FieldName = Annotated[str, StringConstraints(min_length=1, max_length=300)]
_FieldValue = bool | Annotated[str, StringConstraints(max_length=10_000)]

FORM_VALUES = TypeAdapter(Annotated[dict[_FieldName, _FieldValue], Field(max_length=2000)])
