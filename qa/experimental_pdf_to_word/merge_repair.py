"""Repara fusiones de celdas solapadas antes de que pdf2docx genere OOXML.

pdf2docx 0.5.13 puede producir dos celdas superiores cuya región ``merged_cells``
ocupa la misma coordenada. ``python-docx`` permite ejecutar ambas fusiones, pero la
segunda escribe sobre la primera y destruye texto. Este adaptador no cambia la
detección de tablas: limita exclusivamente las regiones geométricamente inválidas.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import contextmanager
from pathlib import Path
import time
from typing import Any, Iterable

import pymupdf

_message_warning = pymupdf.message_warning
try:
    pymupdf.message_warning = lambda *_args, **_kwargs: None
    import fitz as _legacy_fitz  # noqa: F401 - pdf2docx still imports this alias.
    from pdf2docx import Converter
    from pdf2docx.table.TableBlock import TableBlock
finally:
    pymupdf.message_warning = _message_warning


@dataclass
class Region:
    row: int
    column: int
    rows: int
    columns: int
    cell: Any

    @property
    def bottom(self) -> int:
        return self.row + self.rows

    @property
    def right(self) -> int:
        return self.column + self.columns

    @property
    def area(self) -> int:
        return self.rows * self.columns


@dataclass(frozen=True)
class MergeChange:
    table_path: str
    row: int
    column: int
    before: tuple[int, int]
    after: tuple[int, int]
    conflicting_anchor: tuple[int, int]


@dataclass(frozen=True)
class RowHeightChange:
    table_path: str
    before_total: float
    after_total: float
    rows: int


def _overlap(first: Region, second: Region) -> bool:
    return not (
        first.bottom <= second.row
        or second.bottom <= first.row
        or first.right <= second.column
        or second.right <= first.column
    )


def _first_conflict(regions: list[Region]) -> tuple[Region, Region] | None:
    for index, first in enumerate(regions):
        for second in regions[index + 1 :]:
            if _overlap(first, second):
                return first, second
    return None


def _shrink_earlier(first: Region, second: Region) -> None:
    """Exclude the later anchor while retaining the largest valid rectangle."""
    candidates: list[tuple[int, int]] = []
    if second.row > first.row:
        candidates.append((second.row - first.row, first.columns))
    if second.column > first.column:
        candidates.append((first.rows, second.column - first.column))
    if not candidates:
        # Regions are sorted row-major, so this is defensive rather than expected.
        first.rows, first.columns = 1, 1
        return
    first.rows, first.columns = max(candidates, key=lambda size: size[0] * size[1])


def _regions(table: Any) -> list[Region]:
    result: list[Region] = []
    for row_index, row in enumerate(table):
        for column_index, cell in enumerate(row):
            if not cell:
                continue
            rows, columns = cell.merged_cells
            result.append(Region(row_index, column_index, rows, columns, cell))
    return result


def repair_table_merges(table: Any, table_path: str) -> list[MergeChange]:
    regions = _regions(table)
    original = {(region.row, region.column): (region.rows, region.columns) for region in regions}
    conflicts: dict[tuple[int, int], tuple[int, int]] = {}

    # Each iteration strictly reduces one region's area, so termination is bounded
    # by the finite table grid.
    while conflict := _first_conflict(regions):
        earlier, later = conflict
        key = (earlier.row, earlier.column)
        conflicts.setdefault(key, (later.row, later.column))
        before_area = earlier.area
        _shrink_earlier(earlier, later)
        if earlier.area >= before_area:
            raise RuntimeError(f"No fue posible resolver la fusión solapada en {table_path} {key}.")

    changes: list[MergeChange] = []
    for region in regions:
        before = original[(region.row, region.column)]
        after = (region.rows, region.columns)
        if before == after:
            continue
        region.cell.merged_cells = after
        changes.append(
            MergeChange(
                table_path=table_path,
                row=region.row,
                column=region.column,
                before=before,
                after=after,
                conflicting_anchor=conflicts[(region.row, region.column)],
            )
        )
    return changes


def _reconcile_row_heights(table: Any, table_path: str) -> RowHeightChange | None:
    """Derive row heights from physical cell boxes when they define a full grid."""
    boundaries = sorted(
        {
            round(value, 3)
            for row in table
            for cell in row
            if cell
            for value in (cell.bbox.y0, cell.bbox.y1)
        }
    )
    if len(boundaries) != table.num_rows + 1:
        return None
    before = sum(row.height for row in table)
    heights = [end - start for start, end in zip(boundaries, boundaries[1:])]
    if any(height <= 0 for height in heights):
        return None
    for row, height in zip(table, heights):
        row.height = height
    after = sum(heights)
    return RowHeightChange(table_path, round(before, 3), round(after, 3), table.num_rows)


def repair_layout_merges(pages: Iterable[Any], *, reconcile_row_heights: bool = False) -> dict[str, Any]:
    changes: list[MergeChange] = []
    row_height_changes: list[RowHeightChange] = []
    table_count = 0
    maximum_depth = 0

    def walk(layout: Any, path: str, depth: int) -> None:
        nonlocal table_count, maximum_depth
        maximum_depth = max(maximum_depth, depth)
        for block_index, block in enumerate(layout.blocks):
            if not getattr(block, "is_table_block", False):
                continue
            table_count += 1
            table_path = f"{path}/table[{block_index}]"
            table_changes = repair_table_merges(block, table_path)
            changes.extend(table_changes)
            if table_changes and reconcile_row_heights:
                row_change = _reconcile_row_heights(block, table_path)
                if row_change:
                    row_height_changes.append(row_change)
            for row_index, row in enumerate(block):
                for column_index, cell in enumerate(row):
                    if cell:
                        walk(cell, f"{table_path}/cell[{row_index},{column_index}]", depth + 1)

    for page_index, page in enumerate(pages):
        if page.skip_parsing:
            continue
        for section_index, section in enumerate(page.sections):
            for column_index, column in enumerate(section):
                walk(column, f"page[{page_index}]/section[{section_index}]/column[{column_index}]", 0)

    return {
        "tables_visited": table_count,
        "maximum_table_depth": maximum_depth,
        "merge_changes": [asdict(change) for change in changes],
        "changed_regions": len(changes),
        "row_height_changes": [asdict(change) for change in row_height_changes],
        "remaining_overlap": 0,
    }


@contextmanager
def _selective_stream_parser(enabled: bool):
    """Optionally suppress stream detection only below an explicit lattice table."""
    if not enabled:
        yield
        return
    original = TableBlock.parse

    def parse(self: Any, **settings: Any) -> None:
        child_settings = settings
        if self.is_lattice_table_block and settings.get("parse_stream_table"):
            child_settings = dict(settings)
            child_settings["parse_stream_table"] = False
        for row in self:
            for cell in row:
                if cell:
                    cell.parse(**child_settings)

    TableBlock.parse = parse
    try:
        yield
    finally:
        TableBlock.parse = original


def convert_with_merge_repair(
    source: Path,
    destination: Path,
    *,
    settings_override: dict[str, Any] | None = None,
    reconcile_row_heights: bool = False,
    suppress_stream_inside_lattice: bool = False,
    repair_overlaps: bool = True,
    recover_backgrounds: bool = False,
) -> dict[str, Any]:
    """Run pdf2docx defaults, repair invalid merges, and create an isolated DOCX."""
    converter = Converter(str(source))
    settings = converter.default_settings
    settings.update(settings_override or {})
    phases: dict[str, float] = {}
    try:
        started = time.perf_counter()
        phase = time.perf_counter()
        converter.load_pages()
        phases["load_pages_s"] = time.perf_counter() - phase

        phase = time.perf_counter()
        converter.parse_document(**settings)
        phases["parse_document_s"] = time.perf_counter() - phase

        phase = time.perf_counter()
        with _selective_stream_parser(suppress_stream_inside_lattice):
            converter.parse_pages(**settings)
        phases["parse_pages_s"] = time.perf_counter() - phase

        phase = time.perf_counter()
        repair = (
            repair_layout_merges(converter.pages, reconcile_row_heights=reconcile_row_heights)
            if repair_overlaps
            else {
                "tables_visited": 0,
                "maximum_table_depth": 0,
                "merge_changes": [],
                "changed_regions": 0,
                "row_height_changes": [],
                "remaining_overlap": None,
            }
        )
        phases["repair_merges_s"] = time.perf_counter() - phase

        phase = time.perf_counter()
        if recover_backgrounds:
            from qa.experimental_pdf_to_word.vector_backgrounds import recover_vector_backgrounds

            backgrounds = recover_vector_backgrounds(converter.pages, source)
        else:
            backgrounds = {"candidate_count": 0, "changed_regions": 0, "changes": []}
        phases["recover_backgrounds_s"] = time.perf_counter() - phase

        phase = time.perf_counter()
        converter.make_docx(str(destination), **settings)
        phases["make_docx_s"] = time.perf_counter() - phase
        phases["total_s"] = time.perf_counter() - started
        return {
            "engine": (
                "pdf2docx-0.5.13+merge-repair+vector-backgrounds-experimental"
                if repair_overlaps and recover_backgrounds
                else "pdf2docx-0.5.13+merge-repair-experimental"
                if repair_overlaps
                else "pdf2docx-0.5.13-baseline"
            ),
            "settings_override": settings_override or {},
            "suppress_stream_inside_lattice": suppress_stream_inside_lattice,
            "repair_overlaps": repair_overlaps,
            "recover_backgrounds": recover_backgrounds,
            "phases_s": {key: round(value, 6) for key, value in phases.items()},
            "repair": repair,
            "backgrounds": backgrounds,
        }
    finally:
        converter.close()
