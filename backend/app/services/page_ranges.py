"""Interpretación de rangos de páginas escritos por personas: «1-3, 5, 8-»."""

import re

from app.services.errors import ToolError

_TOKEN = re.compile(r"^\s*(\d+)?\s*(-\s*(\d+)?)?\s*$")
_EXAMPLE = "por ejemplo: 1-3, 5, 8-10"


def parse_page_ranges(text: str, page_count: int) -> list[range]:
    """Devuelve rangos con índices desde 0. «8-» va de la 8 al final; «-3», de la 1 a la 3."""
    ranges: list[range] = []
    for raw in text.split(","):
        token = raw.strip()
        if not token:
            continue

        match = _TOKEN.match(token)
        if match is None or (match.group(1) is None and match.group(3) is None):
            raise ToolError(f"No entendimos «{token}». Usa números y guiones, {_EXAMPLE}.")

        start = int(match.group(1)) if match.group(1) else 1
        if match.group(2) is None:
            end = start
        else:
            end = int(match.group(3)) if match.group(3) else page_count

        if start < 1 or end > page_count or start > end:
            raise ToolError(f"«{token}» no es válido: el documento tiene {page_count} páginas.")
        ranges.append(range(start - 1, end))

    if not ranges:
        raise ToolError(f"Escribe al menos una página o rango, {_EXAMPLE}.")
    return ranges
