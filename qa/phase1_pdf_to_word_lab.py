"""Laboratorio reproducible de calidad PDF -> DOCX para EPDF.

No contiene documentos ni datos personales. Recibe rutas explícitas y escribe únicamente
en el directorio de salida indicado por el operador.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager, redirect_stdout
from difflib import SequenceMatcher
import io
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import pymupdf

# pdf2docx 0.5.13 imports the deprecated ``fitz`` alias and prints a warning to
# stdout. Keep the CLI's stdout valid JSON while still allowing import failures
# to propagate normally.
_message_warning = pymupdf.message_warning
try:
    pymupdf.message_warning = lambda *_args, **_kwargs: None
    with redirect_stdout(io.StringIO()):
        import fitz as _legacy_fitz  # noqa: F401 - pdf2docx still imports this alias lazily.
        from pdf2docx import Converter
        from pdf2docx.page.RawPageFactory import RawPageFactory
finally:
    pymupdf.message_warning = _message_warning


WORD_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
V_NS = "urn:schemas-microsoft-com:vml"


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return WORD_RE.findall(normalized)


def compare_text(source: str, target: str) -> dict[str, object]:
    source_tokens = tokens(source)
    target_tokens = tokens(target)
    missing = Counter(source_tokens) - Counter(target_tokens)
    extra = Counter(target_tokens) - Counter(source_tokens)
    return {
        "source_words": len(source_tokens),
        "target_words": len(target_tokens),
        "missing_words": sum(missing.values()),
        "extra_words": sum(extra.values()),
        "missing_examples": list(missing.elements())[:80],
        "extra_examples": list(extra.elements())[:80],
        "sequence_ratio": round(SequenceMatcher(None, source_tokens, target_tokens, autojunk=False).ratio(), 6),
    }


def pdf_metrics(path: Path) -> tuple[dict[str, object], str]:
    document = pymupdf.open(path)
    pages: list[dict[str, object]] = []
    text_parts: list[str] = []
    for index, page in enumerate(document):
        text = page.get_text("text", sort=True)
        text_parts.append(text)
        widgets = list(page.widgets() or [])
        drawings = page.get_drawings()
        pages.append(
            {
                "page": index + 1,
                "width_pt": round(page.rect.width, 3),
                "height_pt": round(page.rect.height, 3),
                "words": len(page.get_text("words", sort=True)),
                "blocks": len(page.get_text("blocks", sort=True)),
                "drawings": len(drawings),
                "drawing_items": sum(len(item.get("items", [])) for item in drawings),
                "images": len(page.get_images(full=True)),
                "widgets": len(widgets),
                "widget_types": Counter(widget.field_type_string for widget in widgets),
            }
        )
    text = "\n".join(text_parts)
    result = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "pages": len(document),
        "word_count": len(tokens(text)),
        "char_count": len(text),
        "page_metrics": pages,
    }
    document.close()
    return result, text


def _xml_root(archive: zipfile.ZipFile, member: str) -> ET.Element | None:
    try:
        return ET.fromstring(archive.read(member))
    except KeyError:
        return None


def docx_metrics(path: Path) -> tuple[dict[str, object], str]:
    with zipfile.ZipFile(path) as archive:
        document = _xml_root(archive, "word/document.xml")
        if document is None:
            raise ValueError(f"{path} no contiene word/document.xml")
        text_nodes = [node.text or "" for node in document.iter(f"{{{W_NS}}}t")]
        text = " ".join(text_nodes)
        tables = list(document.iter(f"{{{W_NS}}}tbl"))
        rows = list(document.iter(f"{{{W_NS}}}tr"))
        cells = list(document.iter(f"{{{W_NS}}}tc"))
        paragraphs = list(document.iter(f"{{{W_NS}}}p"))
        runs = list(document.iter(f"{{{W_NS}}}r"))
        drawings = list(document.iter(f"{{{W_NS}}}drawing"))
        picts = list(document.iter(f"{{{W_NS}}}pict"))
        app = _xml_root(archive, "docProps/app.xml")
        page_count = None
        if app is not None:
            for node in app:
                if node.tag.endswith("}Pages") and node.text:
                    page_count = int(node.text)
                    break
        nested_tables = sum(1 for table in tables if any(parent is not table for parent in tables if table in list(parent.iter())))
        media = [name for name in archive.namelist() if name.startswith("word/media/") and not name.endswith("/")]
        result = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "valid_zip": archive.testzip() is None,
            "reported_pages": page_count,
            "word_count": len(tokens(text)),
            "char_count": len(text),
            "paragraphs": len(paragraphs),
            "runs": len(runs),
            "tables": len(tables),
            "nested_tables": nested_tables,
            "rows": len(rows),
            "cells": len(cells),
            "drawings": len(drawings),
            "vml_pictures": len(picts),
            "images": len(media),
            "sections": sum(1 for _ in document.iter(f"{{{W_NS}}}sectPr")),
            "drawing_blips": sum(1 for _ in document.iter(f"{{{A_NS}}}blip")),
            "vml_shapes": sum(1 for _ in document.iter(f"{{{V_NS}}}shape")),
        }
    return result, text


def _layout_stats(converter: Converter) -> dict[str, int]:
    stats: Counter[str] = Counter()

    def walk(layout) -> None:
        stats["layouts"] += 1
        stats["shapes"] += len(layout.shapes)
        for block in layout.blocks:
            stats["blocks"] += 1
            if getattr(block, "is_table_block", False):
                stats["tables"] += 1
                if getattr(block, "is_lattice_table_block", False):
                    stats["lattice_tables"] += 1
                if getattr(block, "is_stream_table_block", False):
                    stats["stream_tables"] += 1
                for row in block:
                    stats["table_rows"] += 1
                    for cell in row:
                        stats["table_cells"] += 1
                        walk(cell)
            elif getattr(block, "is_text_block", False):
                stats["text_blocks"] += 1
                stats["lines"] += len(block.lines)
            else:
                stats[type(block).__name__] += 1

    for page in converter.pages:
        if page.skip_parsing:
            continue
        stats["pages"] += 1
        stats["sections"] += len(page.sections)
        stats["float_images"] += len(page.float_images)
        for section in page.sections:
            stats["columns"] += len(section)
            for column in section:
                walk(column)
    return dict(stats)


def _text_from_layout(converter: Converter) -> str:
    parts: list[str] = []

    def walk(layout) -> None:
        for block in layout.blocks:
            if getattr(block, "is_table_block", False):
                for row in block:
                    for cell in row:
                        walk(cell)
            else:
                value = getattr(block, "text", "")
                if value:
                    parts.append(value)

    for page in converter.pages:
        for section in page.sections:
            for column in section:
                walk(column)
    return "\n".join(parts)


def pipeline_text_metrics(path: Path, settings: dict[str, object]) -> list[dict[str, object]]:
    document = pymupdf.open(path)
    results: list[dict[str, object]] = []
    for index, page in enumerate(document):
        raw_page = RawPageFactory.create(page_engine=page, backend="PyMuPDF")
        raw_page.restore(**settings)
        restored = raw_page.raw_text
        raw_page.clean_up(**settings)
        cleaned = raw_page.raw_text
        raw_page.margin = raw_page.calculate_margin(**settings)
        sections = raw_page.parse_section(**settings) or []
        assigned_parts: list[str] = []
        for section in sections:
            for column in section:
                for block in column.blocks:
                    value = getattr(block, "raw_text", "") or getattr(block, "text", "")
                    if value:
                        assigned_parts.append(value)
        assigned = "\n".join(assigned_parts)
        source = page.get_text("text", sort=True)
        results.append(
            {
                "page": index + 1,
                "source_to_restored": compare_text(source, restored),
                "restored_to_cleaned": compare_text(restored, cleaned),
                "cleaned_to_sections": compare_text(cleaned, assigned),
                "sections": len(sections),
                "columns": sum(len(section) for section in sections),
            }
        )
    document.close()
    return results


@contextmanager
def peak_memory_sampler(interval: float = 0.02):
    def current_rss() -> int:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ProcessMemoryCounters),
                wintypes.DWORD,
            ]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            handle = kernel32.GetCurrentProcess()
            if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                raise OSError("GetProcessMemoryInfo falló")
            return int(counters.WorkingSetSize)

        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if value > 10_000_000 else value * 1024)

    peak = {"rss": current_rss()}
    stopped = threading.Event()

    def sample() -> None:
        while not stopped.wait(interval):
            peak["rss"] = max(peak["rss"], current_rss())

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    try:
        yield peak
    finally:
        stopped.set()
        thread.join(timeout=1)
        peak["rss"] = max(peak["rss"], current_rss())


def instrument_pdf2docx(source: Path, destination: Path, settings_override: dict[str, object]) -> dict[str, object]:
    converter = Converter(str(source))
    settings = converter.default_settings
    settings.update(settings_override)
    phases: dict[str, float] = {}
    started = time.perf_counter()
    with peak_memory_sampler() as peak:
        phase = time.perf_counter()
        converter.load_pages()
        phases["load_pages_s"] = time.perf_counter() - phase

        phase = time.perf_counter()
        pipeline = pipeline_text_metrics(source, settings)
        phases["diagnostic_pipeline_s"] = time.perf_counter() - phase

        phase = time.perf_counter()
        converter.parse_document(**settings)
        phases["parse_document_s"] = time.perf_counter() - phase
        pre_parse_stats = _layout_stats(converter)

        phase = time.perf_counter()
        converter.parse_pages(**settings)
        phases["parse_pages_s"] = time.perf_counter() - phase
        post_parse_stats = _layout_stats(converter)
        layout_text = _text_from_layout(converter)

        phase = time.perf_counter()
        converter.make_docx(str(destination), **settings)
        phases["make_docx_s"] = time.perf_counter() - phase
    converter.close()

    pdf, pdf_text = pdf_metrics(source)
    docx, docx_text = docx_metrics(destination)
    phases["total_s"] = time.perf_counter() - started
    return {
        "engine": "pdf2docx",
        "settings": settings_override,
        "phases_s": {key: round(value, 6) for key, value in phases.items()},
        "peak_rss_bytes": peak["rss"],
        "pdf": pdf,
        "docx": docx,
        "pdf_to_layout": compare_text(pdf_text, layout_text),
        "pdf_to_docx": compare_text(pdf_text, docx_text),
        "pipeline": pipeline,
        "layout_before_page_parse": pre_parse_stats,
        "layout_after_page_parse": post_parse_stats,
    }


def generate_synthetic_fixture(destination: Path, *, form_grid: bool) -> None:
    """Create a deterministic, non-personal PDF fixture for quality regression checks."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    page = document.new_page(width=792, height=612)
    page.insert_text((36, 34), "EPDF QUALITY FIXTURE", fontsize=16, fontname="helv", color=(0.04, 0.2, 0.36))
    page.insert_text(
        (36, 55),
        "Every numbered phrase must remain editable, ordered, and present in the DOCX.",
        fontsize=9,
        fontname="helv",
    )

    if not form_grid:
        for index, text in enumerate(
            (
                "Alpha one verifies ordinary paragraphs.",
                "Bravo two verifies a second baseline line.",
                "Charlie three verifies accents: árbol, acción, lápiz.",
            )
        ):
            page.insert_text((48, 100 + index * 28), text, fontsize=11, fontname="helv")
    else:
        column_width = 224
        column_gap = 20
        top = 88
        for column in range(3):
            left = 36 + column * (column_width + column_gap)
            page.draw_rect(
                pymupdf.Rect(left, top, left + column_width, 548),
                color=(0.1, 0.3, 0.45),
                width=0.8,
            )
            page.draw_rect(
                pymupdf.Rect(left, top, left + column_width, top + 28),
                color=(0.1, 0.3, 0.45),
                fill=(0.88, 0.94, 0.98),
                width=0.8,
            )
            page.insert_text(
                (left + 8, top + 19),
                f"COLUMN {column + 1}",
                fontsize=11,
                fontname="helv",
                color=(0.04, 0.2, 0.36),
            )
            for row in range(6):
                y0 = top + 38 + row * 66
                page.insert_text(
                    (left + 8, y0 + 12),
                    f"Item {column + 1}.{row + 1}: token{column + 1}{row + 1} stays editable.",
                    fontsize=8,
                    fontname="helv",
                )
                page.draw_rect(
                    pymupdf.Rect(left + 8, y0 + 18, left + column_width - 8, y0 + 52),
                    color=(0.55, 0.66, 0.75),
                    width=0.5,
                )
                page.draw_line(
                    pymupdf.Point(left + 18, y0 + 40),
                    pymupdf.Point(left + column_width - 18, y0 + 40),
                    color=(0.72, 0.78, 0.83),
                    width=0.35,
                )

        for index in range(3):
            widget = pymupdf.Widget()
            widget.field_name = f"fixture_field_{index + 1}"
            widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
            widget.field_value = ""
            left = 48 + index * (column_width + column_gap)
            widget.rect = pymupdf.Rect(left, 562, left + 150, 582)
            page.add_widget(widget)

    document.save(destination, garbage=4, deflate=True)
    document.close()


def run_synthetic_regression(output_dir: Path) -> dict[str, object]:
    """Run strict content/editability gates against generated fixtures."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {}
    for name, form_grid in (("baseline", False), ("form_grid", True)):
        pdf_path = output_dir / f"{name}.pdf"
        docx_path = output_dir / f"{name}.docx"
        json_path = output_dir / f"{name}.json"
        generate_synthetic_fixture(pdf_path, form_grid=form_grid)
        result = instrument_pdf2docx(pdf_path, docx_path, {})
        comparison = result["pdf_to_docx"]
        docx = result["docx"]
        gates = {
            "valid_docx": bool(docx["valid_zip"]),
            "editable_text_present": int(docx["word_count"]) > 0,
            "no_missing_words": int(comparison["missing_words"]) == 0,
            "no_extra_words": int(comparison["extra_words"]) == 0,
        }
        result["quality_gates"] = gates
        result["quality_gate_passed"] = all(gates.values())
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        results[name] = result
    return results


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("--pdf", type=Path, required=True)
    analyze.add_argument("--docx", type=Path, required=True)

    convert = subparsers.add_parser("convert")
    convert.add_argument("--pdf", type=Path, required=True)
    convert.add_argument("--docx", type=Path, required=True)
    convert.add_argument("--settings", default="{}")
    convert.add_argument("--json", type=Path)

    synthetic = subparsers.add_parser("synthetic")
    synthetic.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "analyze":
        pdf, pdf_text = pdf_metrics(args.pdf)
        docx, docx_text = docx_metrics(args.docx)
        result = {"pdf": pdf, "docx": docx, "comparison": compare_text(pdf_text, docx_text)}
    elif args.command == "convert":
        settings = json.loads(args.settings)
        result = instrument_pdf2docx(args.pdf, args.docx, settings)
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        result = run_synthetic_regression(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=lambda value: dict(value)))


if __name__ == "__main__":
    main()
