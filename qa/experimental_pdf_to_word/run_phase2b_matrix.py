"""Run the anonymous Phase 2B regression matrix without touching production code."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from qa.experimental_pdf_to_word.fixtures import generate_all
from qa.experimental_pdf_to_word.merge_repair import convert_with_merge_repair
from qa.phase1_pdf_to_word_lab import compare_text, docx_metrics, pdf_metrics, peak_memory_sampler


VARIANTS = {
    "baseline": {"repair_overlaps": False, "recover_backgrounds": False},
    "phase2a": {"repair_overlaps": True, "recover_backgrounds": False},
    "phase2b": {"repair_overlaps": True, "recover_backgrounds": True},
}


def run(output_dir: Path) -> dict[str, object]:
    fixture_dir = output_dir / "fixtures"
    document_dir = output_dir / "docx"
    fixtures = generate_all(fixture_dir)
    results: dict[str, object] = {}
    for name, source in fixtures.items():
        source_metrics, source_text = pdf_metrics(source)
        variants: dict[str, object] = {}
        for variant, options in VARIANTS.items():
            destination = document_dir / f"{name}-{variant}.docx"
            destination.parent.mkdir(parents=True, exist_ok=True)
            with peak_memory_sampler() as peak:
                conversion = convert_with_merge_repair(source, destination, **options)
            target_metrics, target_text = docx_metrics(destination)
            variants[variant] = {
                "conversion": conversion,
                "peak_rss_bytes": peak["rss"],
                "docx": target_metrics,
                "text": compare_text(source_text, target_text),
            }
        results[name] = {"pdf": source_metrics, "variants": variants}
    return results


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output_dir)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        name: {
            variant: {
                "words": data["docx"]["word_count"],
                "missing": data["text"]["missing_words"],
                "extra": data["text"]["extra_words"],
                "pages": data["docx"]["reported_pages"],
                "tables": data["docx"]["tables"],
                "background_changes": data["conversion"]["backgrounds"]["changed_regions"],
                "seconds": data["conversion"]["phases_s"]["total_s"],
            }
            for variant, data in fixture["variants"].items()
        }
        for name, fixture in result.items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
