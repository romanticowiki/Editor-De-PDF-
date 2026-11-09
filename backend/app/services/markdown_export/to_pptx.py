"""Markdown a PowerPoint: cada título de nivel 1 o 2 abre una diapositiva y el resto se convierte en viñetas."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from markdown_it.token import Token
from pptx import Presentation

from app.services.markdown_export.parser import inline_text, parse, read_table

_TITLE_LAYOUT = 0
_CONTENT_LAYOUT = 1
_SLIDE_HEADINGS = ("h1", "h2")
_MAX_ITEMS_PER_SLIDE = 10  # más viñetas no caben legibles en una diapositiva
_MAX_LEVEL = 4
_UNTITLED = "Presentación"


@dataclass(slots=True)
class _Slide:
    title: str
    items: list[tuple[int, str]] = field(default_factory=list)


def markdown_to_pptx(text: str, destination: Path) -> None:
    presentation = Presentation()
    for number, slide in enumerate(_collect_slides(parse(text))):
        if number == 0 and not slide.items:
            title_slide = presentation.slides.add_slide(presentation.slide_layouts[_TITLE_LAYOUT])
            title_slide.shapes.title.text = slide.title
            continue
        for part, items in enumerate(_chunks(slide.items)):
            title = slide.title if part == 0 else f"{slide.title} (cont.)"
            _add_content_slide(presentation, title, items)
    presentation.save(str(destination))


def _collect_slides(tokens: list[Token]) -> list[_Slide]:
    slides: list[_Slide] = []
    list_depth = 0
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open" and token.tag in _SLIDE_HEADINGS:
            slides.append(_Slide(title=inline_text(tokens[index + 1]) or _UNTITLED))
            index += 3
            continue
        if token.type == "table_open":
            table, index = read_table(tokens, index)
            _current(slides).items.extend((0, " | ".join(row)) for row in table.rows)
            continue

        if token.type in ("bullet_list_open", "ordered_list_open"):
            list_depth += 1
        elif token.type in ("bullet_list_close", "ordered_list_close"):
            list_depth -= 1
        elif token.type == "inline" and (text := inline_text(token)):
            _current(slides).items.append((min(max(list_depth - 1, 0), _MAX_LEVEL), text))
        elif token.type in ("fence", "code_block"):
            _current(slides).items.extend((0, line) for line in token.content.splitlines() if line.strip())
        index += 1

    return slides or [_Slide(title=_UNTITLED)]


def _current(slides: list[_Slide]) -> _Slide:
    if not slides:
        slides.append(_Slide(title=_UNTITLED))
    return slides[-1]


def _chunks(items: list[tuple[int, str]]) -> Iterator[list[tuple[int, str]]]:
    if not items:
        yield []
        return
    for start in range(0, len(items), _MAX_ITEMS_PER_SLIDE):
        yield items[start : start + _MAX_ITEMS_PER_SLIDE]


def _add_content_slide(presentation: Presentation, title: str, items: list[tuple[int, str]]) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[_CONTENT_LAYOUT])
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    for position, (level, text) in enumerate(items):
        paragraph = body.paragraphs[0] if position == 0 else body.add_paragraph()
        paragraph.text = text
        paragraph.level = level
