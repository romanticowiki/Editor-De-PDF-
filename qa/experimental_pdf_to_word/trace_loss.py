"""Localiza bloques perdidos y fusiones solapadas sin modificar pdf2docx."""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import sys
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

import pymupdf

_message_warning = pymupdf.message_warning
try:
    pymupdf.message_warning = lambda *_args, **_kwargs: None
    import fitz as _legacy_fitz  # noqa: F401
    from pdf2docx import Converter
finally:
    pymupdf.message_warning = _message_warning

from qa.phase1_pdf_to_word_lab import docx_metrics, tokens


def _flat_text(layout: Any) -> str:
    values: list[str] = []
    for block in layout.blocks:
        if getattr(block, "is_table_block", False):
            for row in block:
                for cell in row:
                    if cell:
                        values.append(_flat_text(cell))
        elif getattr(block, "text", ""):
            values.append(block.text)
    return " ".join(value for value in values if value)


def _overlap(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    r0, c0, r1, c1 = first
    u0, v0, u1, v1 = second
    return not (r1 <= u0 or u1 <= r0 or c1 <= v0 or v1 <= c0)


def trace(source: Path, baseline_docx: Path) -> dict[str, Any]:
    converter = Converter(str(source))
    settings = converter.default_settings
    try:
        converter.load_pages()
        converter.parse_document(**settings)
        converter.parse_pages(**settings)
        token_records: list[dict[str, Any]] = []
        table_overlaps: list[dict[str, Any]] = []

        def walk(layout: Any, path: str) -> None:
            for block_index, block in enumerate(layout.blocks):
                block_path = f"{path}/block[{block_index}]"
                if getattr(block, "is_table_block", False):
                    anchors: list[tuple[tuple[int, int, int, int], Any, str]] = []
                    for row_index, row in enumerate(block):
                        for column_index, cell in enumerate(row):
                            if not cell:
                                continue
                            rows, columns = cell.merged_cells
                            region = (row_index, column_index, row_index + rows, column_index + columns)
                            anchors.append((region, cell, _flat_text(cell)))
                    for index, (first_region, _first_cell, first_text) in enumerate(anchors):
                        for second_region, _second_cell, second_text in anchors[index + 1 :]:
                            if _overlap(first_region, second_region):
                                table_overlaps.append(
                                    {
                                        "table_path": block_path,
                                        "first_region": first_region,
                                        "first_text": first_text,
                                        "second_region": second_region,
                                        "second_text": second_text,
                                    }
                                )
                    for row_index, row in enumerate(block):
                        for column_index, cell in enumerate(row):
                            if cell:
                                walk(cell, f"{block_path}/cell[{row_index},{column_index}]")
                    continue

                text = getattr(block, "text", "")
                if not text:
                    continue
                record = {
                    "path": block_path,
                    "text": text,
                    "bbox": [round(value, 3) for value in block.bbox],
                }
                for token in tokens(text):
                    token_records.append({"token": token, "block": record})

        for page_index, page in enumerate(converter.pages):
            for section_index, section in enumerate(page.sections):
                for column_index, column in enumerate(section):
                    walk(column, f"page[{page_index}]/section[{section_index}]/column[{column_index}]")

        _docx, docx_text = docx_metrics(baseline_docx)
        layout_tokens = [record["token"] for record in token_records]
        output_tokens = tokens(docx_text)
        differences: list[dict[str, Any]] = []
        matcher = SequenceMatcher(None, layout_tokens, output_tokens, autojunk=False)
        for tag, source_start, source_end, target_start, target_end in matcher.get_opcodes():
            if tag == "equal":
                continue
            blocks: list[dict[str, Any]] = []
            for record in token_records[source_start:source_end]:
                if record["block"] not in blocks:
                    blocks.append(record["block"])
            differences.append(
                {
                    "kind": tag,
                    "layout_range": [source_start, source_end],
                    "docx_range": [target_start, target_end],
                    "layout_tokens": layout_tokens[source_start:source_end],
                    "docx_tokens": output_tokens[target_start:target_end],
                    "layout_blocks": blocks,
                }
            )
        return {
            "source": str(source),
            "baseline_docx": str(baseline_docx),
            "layout_tokens": len(layout_tokens),
            "docx_tokens": len(output_tokens),
            "layout_to_docx_differences": differences,
            "overlapping_merge_pairs": table_overlaps,
            "overlapping_merge_pair_count": len(table_overlaps),
        }
    finally:
        converter.close()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--docx", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    result = trace(args.pdf, args.docx)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
