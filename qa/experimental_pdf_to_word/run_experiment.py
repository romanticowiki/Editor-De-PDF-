"""CLI de medición para el prototipo aislado de Fase 2A."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from qa.experimental_pdf_to_word.merge_repair import convert_with_merge_repair
from qa.phase1_pdf_to_word_lab import compare_text, docx_metrics, pdf_metrics, peak_memory_sampler


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--docx", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--reconcile-row-heights", action="store_true")
    parser.add_argument("--suppress-stream-inside-lattice", action="store_true")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--recover-backgrounds", action="store_true")
    args = parser.parse_args()

    args.docx.parent.mkdir(parents=True, exist_ok=True)
    with peak_memory_sampler() as peak:
        result = convert_with_merge_repair(
            args.pdf,
            args.docx,
            reconcile_row_heights=args.reconcile_row_heights,
            suppress_stream_inside_lattice=args.suppress_stream_inside_lattice,
            repair_overlaps=not args.baseline,
            recover_backgrounds=args.recover_backgrounds,
        )
    pdf, pdf_text = pdf_metrics(args.pdf)
    docx, docx_text = docx_metrics(args.docx)
    result.update(
        {
            "peak_rss_bytes": peak["rss"],
            "pdf": pdf,
            "docx": docx,
            "pdf_to_docx": compare_text(pdf_text, docx_text),
        }
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
