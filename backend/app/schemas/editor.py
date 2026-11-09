"""Validación estricta del payload del editor visual.

Cada operación llega con su tipo, página y coordenadas en PUNTOS PDF (origen arriba-izquierda,
y hacia abajo — el sistema nativo de PyMuPDF). Los límites de aquí son la primera línea de
defensa contra payloads maliciosos (coordenadas absurdas, miles de trazos, texto enorme).
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, StringConstraints, model_validator

from app.schemas.forms import FormFieldOut

# Una coordenada nunca debería salirse tanto de una página (A4 ≈ 595×842 pt): acota valores
# patológicos sin ser restrictiva. En tiempo de ejecución además se recorta a la página real.
Coord = Annotated[float, Field(ge=-100_000, le=100_000)]
Unit = Annotated[float, Field(ge=0.0, le=1.0)]  # componente de color 0..1
Rgb = tuple[Unit, Unit, Unit]
Point = tuple[Coord, Coord]
TextStr = Annotated[str, StringConstraints(min_length=1, max_length=10_000)]

MAX_OPERATIONS = 300
_MAX_STROKES = 200
_MAX_POINTS_PER_STROKE = 3_000
_MAX_TOTAL_POINTS = 20_000
MAX_IMAGES = 20


class Rect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x0: Coord
    y0: Coord
    x1: Coord
    y1: Coord

    @model_validator(mode="after")
    def _ordered(self) -> "Rect":
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("El rectángulo debe tener ancho y alto positivos.")
        return self


class _Op(BaseModel):
    model_config = ConfigDict(extra="forbid")  # un campo de más = rechazo (no confiamos en el cliente)
    page: Annotated[int, Field(ge=0, le=9_999)]


class AddTextOp(_Op):
    type: Literal["add_text"]
    x: Coord
    y: Coord
    text: TextStr
    size: Annotated[float, Field(ge=4, le=400)] = 12.0
    color: Rgb = (0.0, 0.0, 0.0)


class AddTextBoxOp(_Op):
    type: Literal["add_textbox"]
    rect: Rect
    text: TextStr
    size: Annotated[float, Field(ge=4, le=400)] = 12.0
    color: Rgb = (0.0, 0.0, 0.0)
    align: Literal[0, 1, 2] = 0


class SetFieldOp(_Op):
    type: Literal["set_field"]
    name: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    value: StrictBool | Annotated[StrictStr, StringConstraints(max_length=10_000)]
    size: Annotated[float, Field(ge=4, le=400)] | None = None


class HighlightOp(_Op):
    type: Literal["highlight"]
    rect: Rect
    color: Rgb = (0.99, 0.85, 0.25)


class DrawOp(_Op):
    type: Literal["draw"]
    strokes: Annotated[
        list[Annotated[list[Point], Field(min_length=1, max_length=_MAX_POINTS_PER_STROKE)]],
        Field(min_length=1, max_length=_MAX_STROKES),
    ]
    color: Rgb = (0.85, 0.33, 0.18)
    width: Annotated[float, Field(ge=0.5, le=20)] = 2.0

    @model_validator(mode="after")
    def _total_points(self) -> "DrawOp":
        if sum(len(stroke) for stroke in self.strokes) > _MAX_TOTAL_POINTS:
            raise ValueError("Demasiados puntos en el dibujo.")
        return self


class PatchTextOp(_Op):
    type: Literal["patch_text"]
    rect: Rect
    text: TextStr
    size: Annotated[float, Field(ge=4, le=400)] = 12.0
    color: Rgb = (0.0, 0.0, 0.0)
    fill: Rgb = (1.0, 1.0, 1.0)  # color con el que se borra la zona antes de reescribir


class AddImageOp(_Op):
    type: Literal["add_image"]
    rect: Rect
    image: Annotated[int, Field(ge=0, le=MAX_IMAGES - 1)]  # índice en los PNG subidos aparte


Operation = Annotated[
    Union[AddTextOp, AddTextBoxOp, SetFieldOp, HighlightOp, DrawOp, PatchTextOp, AddImageOp],
    Field(discriminator="type"),
]


class EditorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operations: Annotated[list[Operation], Field(min_length=1, max_length=MAX_OPERATIONS)]


# ——— Respuesta de la vista previa (páginas rasterizadas para editar encima) ———


class EditorFormField(FormFieldOut):
    rect: Rect  # normalizado respecto a la página visible, incluido su giro
    size: float
    color: Rgb | None = None
    font: str = "Helv"


class EditorPage(BaseModel):
    number: int
    width: float
    height: float
    image: str  # data URL JPEG
    has_form_fields: bool = False
    fields: list[EditorFormField] = Field(default_factory=list)


class EditorPreview(BaseModel):
    page_count: int
    has_form_fields: bool = False
    pages: list[EditorPage]
