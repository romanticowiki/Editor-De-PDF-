"""PDF a Excel: extrae las tablas con pdfplumber.

Si el PDF no tiene tablas dibujadas, exporta su texto línea a línea para que el contenido
no se pierda (mejor algo editable que un libro vacío).
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.worksheet._write_only import WriteOnlyWorksheet

from app.services.errors import ToolError
from app.services.pdf_io import ensure_readable_pdf
from app.services.text import strip_control_chars

CellValue = str | int | float

_TABLE_SETTINGS: dict[str, Any] = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
}
_MAX_SHEET_TITLE_LENGTH = 31  # límite de Excel
_INTEGER = re.compile(r"-?(?:0|[1-9]\d{0,14})")  # sin ceros a la izquierda: "007" sigue siendo texto
_DECIMAL = re.compile(r"-?(?:0|[1-9]\d{0,14})\.\d+")


@dataclass(frozen=True, slots=True)
class ExcelResult:
    tables: int


def pdf_to_excel(source: Path, destination: Path, *, name: str) -> ExcelResult:
    ensure_readable_pdf(source, name)
    workbook = Workbook(write_only=True)  # escribe fila a fila: memoria constante

    try:
        with pdfplumber.open(source) as pdf:
            tables = _write_tables(workbook, pdf)
            if tables == 0 and not _write_text(workbook, pdf):
                raise ToolError(f"No encontramos tablas ni texto en «{name}». Si es un escaneo, pásalo antes por OCR.")
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"No pudimos leer las tablas de «{name}».") from exc

    workbook.save(destination)
    return ExcelResult(tables=tables)


def _write_tables(workbook: Workbook, pdf: pdfplumber.PDF) -> int:
    tables = 0
    for page_number, page in enumerate(pdf.pages, start=1):
        for table_number, table in enumerate(page.extract_tables(_TABLE_SETTINGS), start=1):
            rows = [row for row in ([_normalize(cell) for cell in raw] for raw in table) if any(v != "" for v in row)]
            if rows:
                _append_sheet(workbook, f"Pág {page_number} - Tabla {table_number}", rows)
                tables += 1
        page.close()  # libera la caché de objetos de la página
    return tables


def _write_text(workbook: Workbook, pdf: pdfplumber.PDF) -> bool:
    rows: list[list[CellValue]] = [["Página", "Texto"]]
    for page_number, page in enumerate(pdf.pages, start=1):
        rows.extend([page_number, line] for line in strip_control_chars(page.extract_text() or "").splitlines() if line)
        page.close()
    if len(rows) == 1:
        return False
    _append_sheet(workbook, "Texto", rows)
    return True


def _append_sheet(workbook: Workbook, title: str, rows: list[list[CellValue]]) -> None:
    sheet = workbook.create_sheet(title[:_MAX_SHEET_TITLE_LENGTH])
    for row in rows:
        sheet.append([_cell(sheet, value) for value in row])


def _cell(sheet: WriteOnlyWorksheet, value: CellValue) -> WriteOnlyCell:
    cell = WriteOnlyCell(sheet, value=value)
    # openpyxl guarda "=…" como fórmula: forzamos texto para que un PDF no pueda inyectar fórmulas.
    if isinstance(value, str) and value.startswith("="):
        cell.data_type = "s"
    return cell


def _normalize(cell: str | None) -> CellValue:
    text = strip_control_chars(cell or "").strip()
    if _INTEGER.fullmatch(text):
        return int(text)
    if _DECIMAL.fullmatch(text):
        return float(text)
    return text
