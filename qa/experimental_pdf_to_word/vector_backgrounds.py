"""Recupera fondos vectoriales que pdf2docx conserva pero no escribe en DOCX.

El adaptador trabaja sobre el modelo ya analizado por pdf2docx y usa la fuente PDF
solo como evidencia. Una figura se considera fondo cuando:

* tiene relleno opaco;
* fue dibujada antes que el texto que contiene;
* contiene geométricamente el bloque de texto;
* mantiene contraste suficiente con ese texto; y
* su tamaño es compatible con un fondo local, no con la página completa.

Los fondos que cubren una tabla existente se traducen a sombreado de celda. Si el
texto quedó como párrafo suelto dentro de una celda mayor, se envuelve en una tabla
de una celda para conservar un fondo editable y nativo de Word. No se rasteriza la
página ni se modifica ``site-packages``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import pymupdf

_message_warning = pymupdf.message_warning
try:
    pymupdf.message_warning = lambda *_args, **_kwargs: None
    import fitz as _legacy_fitz  # noqa: F401 - pdf2docx imports the legacy alias.
    from pdf2docx.common.share import rgb_value
    from pdf2docx.table.Cell import Cell
    from pdf2docx.table.TableBlock import TableBlock
finally:
    pymupdf.message_warning = _message_warning


WHITE = 0xFFFFFF


@dataclass(frozen=True)
class VectorBackground:
    page_index: int
    bbox: tuple[float, float, float, float]
    content_bbox: tuple[float, float, float, float]
    color: int
    fill_rgb: tuple[float, float, float]
    fill_opacity: float
    stroke_color: int | None
    stroke_width: float
    seqno: int
    rounded: bool


@dataclass(frozen=True)
class BackgroundChange:
    page_index: int
    action: str
    target_path: str
    text: str
    source_bbox: tuple[float, float, float, float]
    target_bbox: tuple[float, float, float, float]
    color: int
    contrast_ratio: float


def _rgb_int(rgb: tuple[float, float, float] | list[float]) -> int:
    return rgb_value(tuple(rgb))


def _components(color: int) -> tuple[float, float, float]:
    return ((color >> 16 & 0xFF) / 255, (color >> 8 & 0xFF) / 255, (color & 0xFF) / 255)


def _relative_luminance(color: int) -> float:
    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(value) for value in _components(color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: int, second: int) -> float:
    light, dark = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _intersection_ratio(inner: pymupdf.Rect, outer: pymupdf.Rect) -> float:
    if inner.is_empty or inner.get_area() <= 0:
        return 0.0
    intersection = inner & outer
    return 0.0 if intersection.is_empty else intersection.get_area() / inner.get_area()


def _content_bbox(drawing: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return a rectangular Word-safe area inside a rounded vector path."""
    rect = pymupdf.Rect(drawing["rect"])
    horizontal_segments: list[tuple[float, float]] = []
    rounded = False
    for item in drawing.get("items", []):
        if item[0] == "c":
            rounded = True
        if item[0] != "l":
            continue
        first, last = item[1], item[-1]
        if abs(first.y - last.y) <= 0.05 and abs(last.x - first.x) >= rect.width * 0.5:
            horizontal_segments.append((min(first.x, last.x), max(first.x, last.x)))

    if not rounded or not horizontal_segments:
        return tuple(float(value) for value in rect)

    # The flat portion of the rounded top/bottom edge is safe for a rectangular
    # DOCX cell. A small clearance keeps the Word border inside the PDF curve.
    start = min(segment[0] for segment in horizontal_segments)
    end = max(segment[1] for segment in horizontal_segments)
    clearance = max(float(drawing.get("width") or 0.0) / 2, 0.7)
    return (start + clearance, rect.y0, end - clearance, rect.y1)


def extract_vector_backgrounds(
    source: Path,
    *,
    include_white: bool = False,
) -> list[list[VectorBackground]]:
    document = pymupdf.open(source)
    pages: list[list[VectorBackground]] = []
    try:
        for page_index, page in enumerate(document):
            candidates: list[VectorBackground] = []
            for drawing in page.get_drawings(extended=True):
                fill = drawing.get("fill")
                if "rect" not in drawing or fill is None:
                    continue
                opacity = float(drawing.get("fill_opacity", 1.0) or 0.0)
                if opacity < 0.95:
                    continue
                rect = pymupdf.Rect(drawing["rect"])
                if rect.is_empty or rect.width < 2 or rect.height < 2:
                    continue
                color = _rgb_int(fill)
                if color == WHITE and not include_white:
                    continue
                stroke = drawing.get("color")
                candidates.append(
                    VectorBackground(
                        page_index=page_index,
                        bbox=tuple(float(value) for value in rect),
                        content_bbox=_content_bbox(drawing),
                        color=color,
                        fill_rgb=tuple(float(value) for value in fill),
                        fill_opacity=opacity,
                        stroke_color=_rgb_int(stroke) if stroke is not None else None,
                        stroke_width=float(drawing.get("width") or 0.0),
                        seqno=int(drawing.get("seqno", -1)),
                        rounded=any(item[0] == "c" for item in drawing.get("items", [])),
                    )
                )
            pages.append(candidates)
    finally:
        document.close()
    return pages


def _block_color(block: Any) -> int | None:
    weighted: dict[int, float] = {}
    for line in getattr(block, "lines", []):
        for span in getattr(line, "spans", []):
            color = getattr(span, "color", None)
            bbox = getattr(span, "bbox", None)
            if color is None or bbox is None:
                continue
            weighted[int(color)] = weighted.get(int(color), 0.0) + max(bbox.get_area(), 1.0)
    return max(weighted, key=weighted.get) if weighted else None


def _trace_records(source: Path) -> list[list[dict[str, Any]]]:
    document = pymupdf.open(source)
    pages: list[list[dict[str, Any]]] = []
    try:
        for page in document:
            records = []
            for span in page.get_texttrace():
                records.append(
                    {
                        "bbox": pymupdf.Rect(span["bbox"]),
                        "seqno": int(span.get("seqno", -1)),
                        "color": _rgb_int(span["color"]),
                    }
                )
            pages.append(records)
    finally:
        document.close()
    return pages


def _block_seqno(block: Any, traces: list[dict[str, Any]]) -> int | None:
    bbox = pymupdf.Rect(block.bbox)
    seqnos = [record["seqno"] for record in traces if _intersection_ratio(record["bbox"], bbox) >= 0.75]
    return min(seqnos) if seqnos else None


def _matching_background(
    block: Any,
    candidates: Iterable[VectorBackground],
    traces: list[dict[str, Any]],
    *,
    minimum_contrast: float,
) -> tuple[VectorBackground, float] | None:
    block_bbox = pymupdf.Rect(block.bbox)
    if block_bbox.is_empty or block_bbox.get_area() <= 0:
        return None
    text_color = _block_color(block)
    text_seqno = _block_seqno(block, traces)
    if text_color is None or text_seqno is None:
        return None

    matches: list[tuple[float, int, VectorBackground, float]] = []
    for background in candidates:
        background_bbox = pymupdf.Rect(background.bbox)
        containment = _intersection_ratio(block_bbox, background_bbox)
        if containment < 0.9 or background.seqno >= text_seqno:
            continue
        area_ratio = background_bbox.get_area() / block_bbox.get_area()
        if area_ratio > 20 or background_bbox.height > block_bbox.height * 5:
            continue
        contrast = contrast_ratio(text_color, background.color)
        if contrast < minimum_contrast:
            continue
        matches.append((background_bbox.get_area(), text_seqno - background.seqno, background, contrast))

    if not matches:
        return None
    _area, _sequence_gap, candidate, contrast = min(matches, key=lambda item: (item[0], item[1]))
    return candidate, contrast


def _text_blocks(layout: Any) -> list[Any]:
    result: list[Any] = []
    for block in layout.blocks:
        if getattr(block, "is_table_block", False):
            for row in block:
                for cell in row:
                    if cell:
                        result.extend(_text_blocks(cell))
        elif getattr(block, "is_text_block", False) and getattr(block, "text", "").strip():
            result.append(block)
    return result


def _table_blocks(layout: Any) -> list[Any]:
    result: list[Any] = []
    for block in layout.blocks:
        if not getattr(block, "is_table_block", False):
            continue
        result.append(block)
        for row in block:
            for cell in row:
                if cell:
                    result.extend(_table_blocks(cell))
    return result


def _cell_has_nonwhite_background(block: Any) -> bool:
    parent = getattr(block, "parent", None)
    return isinstance(parent, Cell) and parent.bg_color not in (None, WHITE)


def _shade_existing_tables(
    page_index: int,
    page: Any,
    candidates: list[VectorBackground],
    all_fills: list[VectorBackground],
    traces: list[dict[str, Any]],
    minimum_contrast: float,
) -> list[BackgroundChange]:
    changes: list[BackgroundChange] = []
    table_number = 0
    for section_index, section in enumerate(page.sections):
        for column_index, column in enumerate(section):
            for table in _table_blocks(column):
                table_number += 1
                texts = _text_blocks_in_table(table)
                if not texts:
                    continue
                table_bbox = pymupdf.Rect(table.bbox)
                for background in candidates:
                    background_bbox = pymupdf.Rect(background.bbox)
                    if _intersection_ratio(table_bbox, background_bbox) < 0.9:
                        continue
                    matching = [
                        (block, _matching_background(block, [background], traces, minimum_contrast=minimum_contrast))
                        for block in texts
                    ]
                    visible = [(block, match) for block, match in matching if match]
                    if not visible:
                        continue
                    collapsed = _collapse_spurious_rows(table, background, all_fills)
                    changed_cells = table.num_cols if collapsed else 0
                    if not collapsed:
                        for row in table:
                            for cell in row:
                                if not cell or cell.bg_color not in (None, WHITE):
                                    continue
                                if _intersection_ratio(pymupdf.Rect(cell.bbox), background_bbox) < 0.8:
                                    continue
                                cell.bg_color = background.color
                                changed_cells += 1
                    if changed_cells:
                        block, (_candidate, contrast) = visible[0]
                        changes.append(
                            BackgroundChange(
                                page_index=page_index,
                                action=f"shade_existing_table_cells:{changed_cells}",
                                target_path=f"section[{section_index}]/column[{column_index}]/table[{table_number}]",
                                text=" | ".join(item.text for item, _match in visible),
                                source_bbox=background.bbox,
                                target_bbox=tuple(float(value) for value in table_bbox),
                                color=background.color,
                                contrast_ratio=round(contrast, 3),
                            )
                        )
                        if collapsed:
                            changes.append(
                                BackgroundChange(
                                    page_index=page_index,
                                    action="collapse_rows_inside_single_background",
                                    target_path=f"section[{section_index}]/column[{column_index}]/table[{table_number}]",
                                    text=" | ".join(item.text for item, _match in visible),
                                    source_bbox=background.bbox,
                                    target_bbox=tuple(float(value) for value in table.bbox),
                                    color=background.color,
                                    contrast_ratio=round(contrast, 3),
                                )
                            )
                    break
    return changes


def _text_blocks_in_table(table: Any) -> list[Any]:
    result: list[Any] = []
    for row in table:
        for cell in row:
            if cell:
                result.extend(_text_blocks(cell))
    return result


def _cell_overlay_color(
    cell_bbox: pymupdf.Rect,
    background: VectorBackground,
    all_fills: Iterable[VectorBackground],
) -> int:
    overlays: list[VectorBackground] = []
    for fill in all_fills:
        if fill.seqno <= background.seqno:
            continue
        fill_bbox = pymupdf.Rect(fill.bbox)
        intersection = fill_bbox & cell_bbox
        if intersection.is_empty:
            continue
        horizontal = intersection.width / min(fill_bbox.width, cell_bbox.width)
        fill_covered = intersection.get_area() / fill_bbox.get_area()
        if horizontal >= 0.9 and fill_covered >= 0.9:
            overlays.append(fill)
    return max(overlays, key=lambda item: item.seqno).color if overlays else background.color


def _collapse_spurious_rows(
    table: Any,
    background: VectorBackground,
    all_fills: list[VectorBackground],
) -> bool:
    """Collapse rows created inside one visual bar when their geometry clips text."""
    if table.num_rows <= 1 or table.num_cols <= 0 or not isinstance(table.parent, Cell):
        return False
    background_bbox = pymupdf.Rect(background.bbox)
    table_bbox = pymupdf.Rect(table.bbox)
    if background_bbox.height <= table_bbox.height * 1.25:
        return False

    # Require real evidence of the parser split: at least one text block crosses
    # a detected row boundary, while all content still fits the single source bar.
    boundaries = [table[row][0].bbox.y1 for row in range(table.num_rows - 1) if table[row][0]]
    texts = _text_blocks_in_table(table)
    crosses_boundary = any(
        any(block.bbox.y0 < boundary < block.bbox.y1 for boundary in boundaries)
        for block in texts
    )
    if not crosses_boundary:
        return False

    column_bounds: list[tuple[float, float]] = []
    for column in range(table.num_cols):
        cells = [table[row][column] for row in range(table.num_rows) if table[row][column]]
        if not cells:
            return False
        column_bounds.append((min(cell.bbox.x0 for cell in cells), max(cell.bbox.x1 for cell in cells)))
    column_bounds[0] = (background_bbox.x0, column_bounds[0][1])
    column_bounds[-1] = (column_bounds[-1][0], background_bbox.x1)

    for column, (x0, x1) in enumerate(column_bounds):
        primary = table[0][column]
        raw_blocks: list[dict[str, Any]] = []
        for row in range(table.num_rows):
            cell = table[row][column]
            if cell:
                raw_blocks.extend(block.store() for block in cell.blocks)
        cell_bbox = pymupdf.Rect(x0, background_bbox.y0, x1, background_bbox.y1)
        for raw in raw_blocks:
            raw_bbox = pymupdf.Rect(raw.get("bbox", (0, 0, 0, 0)))
            raw["left_space"] = max(raw_bbox.x0 - cell_bbox.x0, 0.0)
            raw["right_space"] = max(cell_bbox.x1 - raw_bbox.x1, 0.0)
            raw["before_space"] = max(raw_bbox.y0 - cell_bbox.y0, 0.0)
            raw["after_space"] = 0.0
        primary.update_bbox(cell_bbox)
        primary.bg_color = _cell_overlay_color(cell_bbox, background, all_fills)
        primary.merged_cells = (table.num_rows, 1)
        primary.blocks.restore(raw_blocks)
        for row in range(1, table.num_rows):
            table[row]._cells._instances[column] = Cell()

    table[0].height = max(background_bbox.height - 1.0, 1.0)
    for row in range(1, table.num_rows):
        table[row].height = 0.0
    table.update_bbox(background_bbox)
    parent_bbox = pymupdf.Rect(table.parent.working_bbox)
    table.left_space = max(background_bbox.x0 - parent_bbox.x0, 0.0)
    table.right_space = max(parent_bbox.x1 - background_bbox.x1, 0.0)
    table.before_space = max(background_bbox.y0 - parent_bbox.y0, 0.0)
    return True


def _wrapped_table(block: Any, parent: Cell, background: VectorBackground) -> TableBlock:
    source_bbox = pymupdf.Rect(background.content_bbox)
    safe_bbox = source_bbox & pymupdf.Rect(parent.working_bbox)
    if safe_bbox.is_empty:
        safe_bbox = pymupdf.Rect(background.bbox) & pymupdf.Rect(parent.working_bbox)

    block_raw = block.store()
    block_raw["left_space"] = max(block.bbox.x0 - safe_bbox.x0, 0.0)
    # A single-line header needs the full cell width. Carrying the free space on
    # the right as a Word paragraph indent can introduce a false line wrap.
    block_raw["right_space"] = 0.0
    block_raw["before_space"] = max(block.bbox.y0 - safe_bbox.y0, 0.0)
    block_raw["after_space"] = 0.0

    parent_bbox = pymupdf.Rect(parent.working_bbox)
    table_raw = {
        "bbox": tuple(safe_bbox),
        "left_space": max(safe_bbox.x0 - parent_bbox.x0, 0.0),
        "right_space": max(parent_bbox.x1 - safe_bbox.x1, 0.0),
        "before_space": max(safe_bbox.y0 - parent_bbox.y0, 0.0),
        "after_space": 0.0,
        "rows": [
            {
                "bbox": tuple(safe_bbox),
                "height": max(safe_bbox.height - 1.0, 1.0),
                "cells": [
                    {
                        "bbox": tuple(safe_bbox),
                        "bg_color": background.color,
                        "border_color": (0, 0, 0, 0),
                        "border_width": (0.0, 0.0, 0.0, 0.0),
                        "merged_cells": (1, 1),
                        "blocks": [block_raw],
                    }
                ],
            }
        ],
    }
    return TableBlock(table_raw)


def recover_vector_backgrounds(
    pages: Iterable[Any],
    source: Path,
    *,
    minimum_contrast: float = 3.0,
) -> dict[str, Any]:
    """Apply evidence-backed vector backgrounds to a parsed pdf2docx model."""
    candidates_by_page = extract_vector_backgrounds(source)
    all_fills_by_page = extract_vector_backgrounds(source, include_white=True)
    traces_by_page = _trace_records(source)
    changes: list[BackgroundChange] = []

    for page_index, page in enumerate(pages):
        if page.skip_parsing:
            continue
        candidates = candidates_by_page[page_index]
        all_fills = all_fills_by_page[page_index]
        traces = traces_by_page[page_index]
        changes.extend(
            _shade_existing_tables(page_index, page, candidates, all_fills, traces, minimum_contrast)
        )

        def walk(layout: Any, path: str) -> None:
            # Work on a copy because a text block may be replaced by a table.
            for block_index, block in enumerate(list(layout.blocks)):
                block_path = f"{path}/block[{block_index}]"
                if getattr(block, "is_table_block", False):
                    for row_index, row in enumerate(block):
                        for column_index, cell in enumerate(row):
                            if cell:
                                walk(cell, f"{block_path}/cell[{row_index},{column_index}]")
                    continue
                if not getattr(block, "is_text_block", False) or not block.text.strip():
                    continue
                if _cell_has_nonwhite_background(block) or not isinstance(layout, Cell):
                    continue
                match = _matching_background(
                    block,
                    candidates,
                    traces,
                    minimum_contrast=minimum_contrast,
                )
                if not match:
                    continue
                background, contrast = match
                replacement = _wrapped_table(block, layout, background)
                current_index = layout.blocks._instances.index(block)
                layout.blocks.pop(current_index)
                layout.blocks.insert(current_index, replacement)
                changes.append(
                    BackgroundChange(
                        page_index=page_index,
                        action="wrap_text_in_shaded_cell",
                        target_path=block_path,
                        text=block.text,
                        source_bbox=background.bbox,
                        target_bbox=background.content_bbox,
                        color=background.color,
                        contrast_ratio=round(contrast, 3),
                    )
                )

        for section_index, section in enumerate(page.sections):
            for column_index, column in enumerate(section):
                walk(column, f"page[{page_index}]/section[{section_index}]/column[{column_index}]")

    return {
        "candidate_count": sum(len(page) for page in candidates_by_page),
        "changed_regions": len(changes),
        "changes": [asdict(change) for change in changes],
    }
