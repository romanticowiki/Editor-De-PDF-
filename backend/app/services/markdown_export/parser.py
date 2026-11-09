from dataclasses import dataclass
from functools import lru_cache

from markdown_it import MarkdownIt
from markdown_it.token import Token

MAX_MARKDOWN_CHARS = 2_000_000


@dataclass(frozen=True, slots=True)
class Table:
    rows: list[list[str]]
    header_rows: int


@lru_cache(maxsize=1)
def _parser() -> MarkdownIt:
    # html=False: el HTML escrito dentro del Markdown se muestra como texto, nunca se interpreta.
    return MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


def parse(text: str) -> list[Token]:
    return _parser().parse(text)


def render_html(text: str) -> str:
    return _parser().render(text)


def inline_text(token: Token) -> str:
    """Texto plano de un token inline, sin marcas de formato."""
    parts: list[str] = []
    for child in token.children or []:
        if child.type in ("text", "code_inline", "image"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts).strip()


def read_table(tokens: list[Token], start: int) -> tuple[Table, int]:
    """Lee la tabla que empieza en `start` (table_open). Devuelve la tabla y el índice tras table_close."""
    rows: list[list[str]] = []
    header_rows = 0
    in_head = False
    index = start
    while tokens[index].type != "table_close":
        token = tokens[index]
        if token.type == "thead_open":
            in_head = True
        elif token.type == "thead_close":
            in_head = False
        elif token.type == "tr_open":
            rows.append([])
            if in_head:
                header_rows += 1
        elif token.type == "inline" and rows:
            rows[-1].append(inline_text(token))
        index += 1
    return Table(rows=rows, header_rows=header_rows), index + 1
