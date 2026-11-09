from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class PagePreview(BaseModel):
    number: int
    width: float
    height: float
    thumbnail: str  # data URL JPEG


class PagesPreview(BaseModel):
    page_count: int
    pages: list[PagePreview]


class PageInstructionIn(BaseModel):
    index: int = Field(ge=0)
    rotation: Literal[0, 90, 180, 270] = 0


PAGE_INSTRUCTIONS = TypeAdapter(Annotated[list[PageInstructionIn], Field(min_length=1, max_length=5000)])
