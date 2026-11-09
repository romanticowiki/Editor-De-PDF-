from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from markdown_it.token import Token

from app.services.markdown_export.parser import parse, read_table

_CODE_FONT = "Consolas"
_CODE_SIZE = Pt(9.5)
_MAX_HEADING_LEVEL = 4
_MAX_LIST_DEPTH = 3  # la plantilla de Word trae estilos de lista hasta nivel 3


def markdown_to_docx(text: str, destination: Path) -> None:
    document = Document()
    tokens = parse(text)
    list_styles: list[str] = []
    quote_depth = 0
    index = 0

    while index < len(tokens):
        token = tokens[index]

        if token.type == "heading_open":
            heading = document.add_heading(level=min(int(token.tag[1]), _MAX_HEADING_LEVEL))
            _add_inline(heading, tokens[index + 1])
            index += 3  # heading_open, inline, heading_close
            continue
        if token.type == "paragraph_open":
            paragraph = document.add_paragraph(style=_paragraph_style(list_styles, quote_depth))
            _add_inline(paragraph, tokens[index + 1])
            index += 3
            continue
        if token.type == "table_open":
            index = _add_table(document, tokens, index)
            continue

        match token.type:
            case "bullet_list_open":
                list_styles.append("List Bullet")
            case "ordered_list_open":
                list_styles.append("List Number")
            case "bullet_list_close" | "ordered_list_close":
                list_styles.pop()
            case "blockquote_open":
                quote_depth += 1
            case "blockquote_close":
                quote_depth -= 1
            case "fence" | "code_block":
                _add_code(document, token.content)
            case "hr":
                document.add_paragraph()
        index += 1

    document.save(str(destination))


def _paragraph_style(list_styles: list[str], quote_depth: int) -> str | None:
    if list_styles:
        depth = min(len(list_styles), _MAX_LIST_DEPTH)
        return list_styles[-1] if depth == 1 else f"{list_styles[-1]} {depth}"
    return "Quote" if quote_depth else None


def _add_inline(paragraph: Paragraph, inline: Token) -> None:
    bold = italic = strike = False
    for child in inline.children or []:
        match child.type:
            case "strong_open" | "strong_close":
                bold = child.type == "strong_open"
            case "em_open" | "em_close":
                italic = child.type == "em_open"
            case "s_open" | "s_close":
                strike = child.type == "s_open"
            case "softbreak":
                paragraph.add_run(" ")
            case "hardbreak":
                paragraph.add_run().add_break()
            case "text" | "code_inline" | "image":
                run = paragraph.add_run(child.content)
                run.bold = bold or None
                run.italic = italic or None
                run.font.strike = strike or None
                if child.type == "code_inline":
                    run.font.name = _CODE_FONT


def _add_code(document: DocxDocument, content: str) -> None:
    run = document.add_paragraph().add_run(content.rstrip("\n"))
    run.font.name = _CODE_FONT
    run.font.size = _CODE_SIZE


def _add_table(document: DocxDocument, tokens: list[Token], start: int) -> int:
    table_data, next_index = read_table(tokens, start)
    if not table_data.rows:
        return next_index

    columns = max(len(row) for row in table_data.rows)
    table = document.add_table(rows=len(table_data.rows), cols=columns)
    table.style = "Table Grid"
    for row_index, row in enumerate(table_data.rows):
        for column_index, value in enumerate(row):
            cell = table.cell(row_index, column_index)
            cell.text = value
            if row_index < table_data.header_rows:
                for run in cell.paragraphs[0].runs:
                    run.bold = True
    return next_index
