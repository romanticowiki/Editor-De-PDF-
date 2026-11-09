"""Documentos sintéticos, deterministas y sin datos personales para Fase 2A."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from qa.phase1_pdf_to_word_lab import generate_synthetic_fixture


PAGE = (612, 792)


def _rounded_rect(
    page: pymupdf.Page,
    rect: pymupdf.Rect,
    *,
    radius: float,
    fill: tuple[float, float, float],
    color: tuple[float, float, float] | None = None,
    width: float = 0.6,
) -> None:
    """Draw a deterministic rounded rectangle using cubic Bézier segments."""
    k = 0.5522847498
    x0, y0, x1, y1 = rect
    r = min(radius, rect.width / 2, rect.height / 2)
    shape = page.new_shape()
    shape.draw_line((x0 + r, y0), (x1 - r, y0))
    shape.draw_bezier((x1 - r, y0), (x1 - r + k * r, y0), (x1, y0 + r - k * r), (x1, y0 + r))
    shape.draw_line((x1, y0 + r), (x1, y1 - r))
    shape.draw_bezier((x1, y1 - r), (x1, y1 - r + k * r), (x1 - r + k * r, y1), (x1 - r, y1))
    shape.draw_line((x1 - r, y1), (x0 + r, y1))
    shape.draw_bezier((x0 + r, y1), (x0 + r - k * r, y1), (x0, y1 - r + k * r), (x0, y1 - r))
    shape.draw_line((x0, y1 - r), (x0, y0 + r))
    shape.draw_bezier((x0, y0 + r), (x0, y0 + r - k * r), (x0 + r - k * r, y0), (x0 + r, y0))
    shape.finish(fill=fill, color=color, width=width, closePath=True)
    shape.commit()


def _new_document(title: str) -> tuple[pymupdf.Document, pymupdf.Page]:
    document = pymupdf.open()
    page = document.new_page(width=PAGE[0], height=PAGE[1])
    page.insert_text((40, 42), title, fontsize=15, fontname="helv", color=(0.05, 0.2, 0.35))
    return document, page


def _save(document: pymupdf.Document, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(destination, garbage=4, deflate=True)
    document.close()
    return destination


def bordered_table(destination: Path) -> Path:
    document, page = _new_document("BORDERED TABLE FIXTURE")
    left, top, width, row_height = 45, 90, 520, 42
    columns = (0, 170, 350, width)
    for row in range(6):
        y = top + row * row_height
        page.draw_line((left, y), (left + width, y), color=(0.1, 0.25, 0.4), width=0.8)
    for offset in columns:
        page.draw_line((left + offset, top), (left + offset, top + 5 * row_height), color=(0.1, 0.25, 0.4), width=0.8)
    rows = (
        ("Code", "Description", "Amount"),
        ("A-100", "Alpha component", "12"),
        ("B-200", "Bravo component", "25"),
        ("C-300", "Charlie component", "31"),
        ("TOTAL", "All components", "68"),
    )
    for row_index, values in enumerate(rows):
        for column_index, value in enumerate(values):
            page.insert_text(
                (left + columns[column_index] + 8, top + row_index * row_height + 26),
                value,
                fontsize=10,
                fontname="hebo" if row_index == 0 else "helv",
            )
    return _save(document, destination)


def borderless_table(destination: Path) -> Path:
    document, page = _new_document("BORDERLESS TABLE FIXTURE")
    positions = (50, 245, 455)
    rows = (
        ("Identifier", "Aligned description", "Score"),
        ("R-01", "Research complete", "18"),
        ("D-02", "Design reviewed", "22"),
        ("T-03", "Testing passed", "27"),
        ("S-04", "Shipping ready", "33"),
    )
    for row_index, values in enumerate(rows):
        baseline = 105 + row_index * 34
        for column_index, value in enumerate(values):
            page.insert_text(
                (positions[column_index], baseline),
                value,
                fontsize=10,
                fontname="hebo" if row_index == 0 else "helv",
            )
    page.insert_text((50, 310), "The aligned columns above have no visible borders.", fontsize=10, fontname="helv")
    return _save(document, destination)


def nested_table(destination: Path) -> Path:
    document, page = _new_document("LEGITIMATE NESTED TABLE FIXTURE")
    left, top, right, bottom = 45, 85, 565, 365
    middle_x, middle_y = 305, 225
    page.draw_rect((left, top, right, bottom), color=(0.08, 0.25, 0.4), width=1)
    page.draw_line((middle_x, top), (middle_x, bottom), color=(0.08, 0.25, 0.4), width=1)
    page.draw_line((left, middle_y), (right, middle_y), color=(0.08, 0.25, 0.4), width=1)
    page.insert_text((60, 115), "Outer cell alpha", fontsize=10, fontname="helv")
    page.insert_text((320, 115), "Outer cell bravo", fontsize=10, fontname="helv")
    page.insert_text((60, 255), "Outer cell charlie", fontsize=10, fontname="helv")

    inner_left, inner_top, inner_right, inner_bottom = 330, 245, 540, 340
    page.draw_rect((inner_left, inner_top, inner_right, inner_bottom), color=(0.5, 0.2, 0.1), width=0.8)
    page.draw_line(((inner_left + inner_right) / 2, inner_top), ((inner_left + inner_right) / 2, inner_bottom), color=(0.5, 0.2, 0.1), width=0.8)
    page.draw_line((inner_left, (inner_top + inner_bottom) / 2), (inner_right, (inner_top + inner_bottom) / 2), color=(0.5, 0.2, 0.1), width=0.8)
    page.insert_text((340, 268), "Nested one", fontsize=9, fontname="helv")
    page.insert_text((445, 268), "Nested two", fontsize=9, fontname="helv")
    page.insert_text((340, 316), "Nested three", fontsize=9, fontname="helv")
    page.insert_text((445, 316), "Nested four", fontsize=9, fontname="helv")
    return _save(document, destination)


def multipage(destination: Path) -> Path:
    document, first = _new_document("MULTIPAGE FIXTURE - PAGE ONE")
    first.insert_text((50, 95), "Page one keeps ordinary editable text in reading order.", fontsize=11, fontname="helv")
    first.insert_text((50, 125), "Second sentence remains on the first page.", fontsize=11, fontname="helv")
    second = document.new_page(width=PAGE[0], height=PAGE[1])
    second.insert_text((40, 42), "MULTIPAGE FIXTURE - PAGE TWO", fontsize=15, fontname="helv", color=(0.05, 0.2, 0.35))
    left, top = 50, 90
    for row in range(4):
        page_y = top + row * 45
        second.draw_line((left, page_y), (550, page_y), color=(0.1, 0.25, 0.4), width=0.8)
    for x in (left, 220, 410, 550):
        second.draw_line((x, top), (x, top + 3 * 45), color=(0.1, 0.25, 0.4), width=0.8)
    values = (("Key", "Meaning", "Value"), ("P2-A", "Table row alpha", "41"), ("P2-B", "Table row bravo", "59"))
    for row_index, row in enumerate(values):
        for column_index, value in enumerate(row):
            second.insert_text((left + (0, 170, 360)[column_index] + 8, top + row_index * 45 + 28), value, fontsize=10, fontname="helv")
    return _save(document, destination)


def colored_headers(destination: Path) -> Path:
    document, page = _new_document("COLORED HEADER FIXTURE")
    page.draw_rect((40, 78, 572, 360), color=(0.08, 0.25, 0.4), width=0.8)
    page.draw_line((306, 78), (306, 360), color=(0.08, 0.25, 0.4), width=0.8)
    page.draw_line((40, 218), (572, 218), color=(0.08, 0.25, 0.4), width=0.8)
    bars = (
        (pymupdf.Rect(50, 92, 296, 122), (0.05, 0.28, 0.48), (1, 1, 1), "DARK HEADER ALPHA"),
        (pymupdf.Rect(316, 92, 562, 122), (0.86, 0.93, 0.98), (0.03, 0.18, 0.32), "LIGHT HEADER BRAVO"),
        (pymupdf.Rect(50, 232, 296, 262), (0.12, 0.42, 0.25), (1, 1, 1), "DARK HEADER CHARLIE"),
        (pymupdf.Rect(316, 232, 562, 262), (0.96, 0.9, 0.72), (0.12, 0.12, 0.12), "LIGHT HEADER DELTA"),
    )
    for rect, fill, text_color, label in bars:
        _rounded_rect(page, rect, radius=7, fill=fill)
        page.insert_text((rect.x0 + 10, rect.y0 + 20), label, fontsize=10, fontname="hebo", color=text_color)
        page.insert_text((rect.x0 + 10, rect.y0 + 52), f"Editable body for {label.split()[-1].lower()}.", fontsize=9)

    # Regression case for Phase 2B: the visual bar extends slightly beyond its
    # containing cell. pdf2docx keeps the Fill but cannot classify it as that
    # cell's shading, which previously left the white text invisible.
    page.draw_rect((40, 405, 560, 525), color=(0.08, 0.25, 0.4), width=0.8)
    crossing = pymupdf.Rect(50, 420, 570, 452)
    _rounded_rect(page, crossing, radius=7, fill=(0.08, 0.25, 0.4))
    page.insert_text((62, 441), "CROSSING HEADER ECHO", fontsize=10, fontname="hebo", color=(1, 1, 1))
    page.insert_text((62, 482), "The header crosses the outer cell by ten points.", fontsize=9)
    return _save(document, destination)


def alternating_fills(destination: Path) -> Path:
    document, page = _new_document("ALTERNATING FILLS FIXTURE")
    left, top, right, row_height = 45, 82, 567, 42
    columns = (left, 160, 420, right)
    fills = ((0.12, 0.35, 0.55), (0.92, 0.96, 0.99), (1, 1, 1), (0.93, 0.97, 0.92), (1, 1, 1))
    rows = (
        ("Code", "Description", "Value"),
        ("R1", "Blue alternate row", "11"),
        ("R2", "White alternate row", "22"),
        ("R3", "Green alternate row", "33"),
        ("R4", "Final white row", "44"),
    )
    for row_index, (fill, values) in enumerate(zip(fills, rows)):
        y0 = top + row_index * row_height
        page.draw_rect((left, y0, right, y0 + row_height), fill=fill, color=(0.3, 0.45, 0.55), width=0.5)
        for x in columns[1:-1]:
            page.draw_line((x, y0), (x, y0 + row_height), color=(0.3, 0.45, 0.55), width=0.5)
        color = (1, 1, 1) if row_index == 0 else (0.05, 0.12, 0.18)
        for column_index, value in enumerate(values):
            page.insert_text((columns[column_index] + 8, y0 + 26), value, fontsize=10, fontname="hebo" if row_index == 0 else "helv", color=color)
    return _save(document, destination)


def borderless_boxes(destination: Path) -> Path:
    document, page = _new_document("BORDERLESS BOXES FIXTURE")
    boxes = (
        (pymupdf.Rect(50, 95, 280, 175), (0.9, 0.95, 0.99), "BOX ALPHA"),
        (pymupdf.Rect(332, 95, 562, 175), (0.93, 0.97, 0.92), "BOX BRAVO"),
    )
    for rect, fill, label in boxes:
        _rounded_rect(page, rect, radius=9, fill=fill)
        page.insert_text((rect.x0 + 12, rect.y0 + 28), label, fontsize=11, fontname="hebo", color=(0.06, 0.2, 0.34))
        page.insert_text((rect.x0 + 12, rect.y0 + 52), "Borderless region remains editable.", fontsize=9)
    return _save(document, destination)


def four_column_form(destination: Path) -> Path:
    document, page = _new_document("FOUR COLUMN FORM FIXTURE")
    left, top, gap, width = 30, 82, 10, 130.5
    colors = ((0.07, 0.3, 0.5), (0.12, 0.42, 0.25), (0.38, 0.28, 0.56), (0.72, 0.34, 0.05))
    for column, fill in enumerate(colors):
        x0 = left + column * (width + gap)
        x1 = x0 + width
        page.draw_rect((x0, top, x1, 390), color=fill, width=0.7)
        _rounded_rect(page, pymupdf.Rect(x0, top, x1, top + 30), radius=6, fill=fill)
        page.insert_text((x0 + 7, top + 20), f"COLUMN {column + 1}", fontsize=9, fontname="hebo", color=(1, 1, 1))
        for row in range(5):
            y = top + 62 + row * 52
            page.insert_text((x0 + 7, y), f"Field {column + 1}.{row + 1}", fontsize=8)
            page.draw_rect((x0 + 7, y + 7, x1 - 7, y + 29), color=(0.65, 0.72, 0.78), width=0.4)
    return _save(document, destination)


def color_region_without_text(destination: Path) -> Path:
    document, page = _new_document("COLOR REGION WITHOUT TEXT FIXTURE")
    page.insert_text((50, 92), "The rectangle below intentionally has no text.", fontsize=10)
    _rounded_rect(page, pymupdf.Rect(50, 120, 562, 250), radius=12, fill=(0.16, 0.42, 0.62))
    page.insert_text((50, 285), "Editable text remains outside the colored region.", fontsize=10)
    return _save(document, destination)


def generate_all(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_synthetic_fixture(output_dir / "simple_text.pdf", form_grid=False)
    generate_synthetic_fixture(output_dir / "form_grid.pdf", form_grid=True)
    return {
        "simple_text": output_dir / "simple_text.pdf",
        "form_grid": output_dir / "form_grid.pdf",
        "bordered_table": bordered_table(output_dir / "bordered_table.pdf"),
        "borderless_table": borderless_table(output_dir / "borderless_table.pdf"),
        "nested_table": nested_table(output_dir / "nested_table.pdf"),
        "multipage": multipage(output_dir / "multipage.pdf"),
        "colored_headers": colored_headers(output_dir / "colored_headers.pdf"),
        "alternating_fills": alternating_fills(output_dir / "alternating_fills.pdf"),
        "borderless_boxes": borderless_boxes(output_dir / "borderless_boxes.pdf"),
        "four_column_form": four_column_form(output_dir / "four_column_form.pdf"),
        "color_region_without_text": color_region_without_text(output_dir / "color_region_without_text.pdf"),
    }
