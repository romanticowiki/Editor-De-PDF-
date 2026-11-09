"""Deterministic pixel checks for the Phase 2B Word render."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat


HEADER_REGIONS_PT = {
    "section_4": (224, 262, 504, 285),
    "section_6": (224, 403, 504, 426),
    "section_7": (20, 494, 504, 517),
    "global_score": (522, 516, 760, 542),
}


def _mae(first: Image.Image, second: Image.Image) -> float:
    difference = ImageChops.difference(first.convert("RGB"), second.convert("RGB"))
    return round(sum(ImageStat.Stat(difference).mean) / 3, 6)


def _changed_over(first: Image.Image, second: Image.Image, threshold: int = 16) -> float:
    difference = ImageChops.difference(first.convert("RGB"), second.convert("RGB"))
    pixels = list(difference.get_flattened_data())
    changed = sum(1 for pixel in pixels if max(pixel) > threshold)
    return round(changed * 100 / len(pixels), 6)


def _dark_ratio(image: Image.Image) -> float:
    pixels = list(image.convert("RGB").get_flattened_data())
    dark = sum(1 for red, green, blue in pixels if (red + green + blue) / 3 < 180)
    return round(dark / len(pixels), 6)


def _regions(image: Image.Image, page_width_pt: float, page_height_pt: float) -> dict[str, Image.Image]:
    x_scale = image.width / page_width_pt
    y_scale = image.height / page_height_pt
    return {
        name: image.crop(
            (
                round(x0 * x_scale),
                round(y0 * y_scale),
                round(x1 * x_scale),
                round(y1 * y_scale),
            )
        )
        for name, (x0, y0, x1, y1) in HEADER_REGIONS_PT.items()
    }


def _font(size: int) -> ImageFont.ImageFont:
    path = Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def _montage(
    source_regions: dict[str, Image.Image],
    phase2a_regions: dict[str, Image.Image],
    phase2b_regions: dict[str, Image.Image],
    destination: Path,
) -> None:
    columns = ("PDF original", "Fase 2A", "Fase 2B")
    groups = (source_regions, phase2a_regions, phase2b_regions)
    target_width = 620
    row_header = 34
    column_header = 44
    gap = 16
    scaled_rows: list[list[Image.Image]] = []
    for name in HEADER_REGIONS_PT:
        row = []
        max_height = 0
        for group in groups:
            crop = group[name]
            scale = min(1.0, target_width / crop.width)
            rendered = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS)
            max_height = max(max_height, rendered.height)
            row.append(rendered)
        scaled_rows.append(row)

    row_heights = [max(image.height for image in row) + row_header for row in scaled_rows]
    width = target_width * 3 + gap * 4
    height = column_header + sum(row_heights) + gap * (len(scaled_rows) + 1)
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = _font(22)
    label_font = _font(18)
    for column, title in enumerate(columns):
        x = gap + column * (target_width + gap)
        draw.text((x, 10), title, fill=(17, 59, 96), font=title_font)

    y = column_header + gap
    for (name, row), row_height in zip(zip(HEADER_REGIONS_PT, scaled_rows), row_heights):
        draw.text((gap, y), name.replace("_", " ").upper(), fill=(35, 35, 35), font=label_font)
        image_y = y + row_header
        for column, image in enumerate(row):
            x = gap + column * (target_width + gap)
            canvas.paste(image, (x, image_y))
            draw.rectangle((x, image_y, x + image.width - 1, image_y + image.height - 1), outline=(190, 200, 210))
        y += row_height + gap
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def validate(source_path: Path, phase2a_path: Path, phase2b_path: Path, montage_path: Path) -> dict[str, object]:
    source = Image.open(source_path).convert("RGB")
    phase2a = Image.open(phase2a_path).convert("RGB")
    phase2b = Image.open(phase2b_path).convert("RGB")
    if source.size != phase2a.size or source.size != phase2b.size:
        raise ValueError(f"Rendered page sizes differ: {source.size}, {phase2a.size}, {phase2b.size}")
    source_regions = _regions(source, 792, 612)
    phase2a_regions = _regions(phase2a, 792, 612)
    phase2b_regions = _regions(phase2b, 792, 612)
    _montage(source_regions, phase2a_regions, phase2b_regions, montage_path)
    return {
        "page_size_px": source.size,
        "global": {
            "phase2a_mae": _mae(source, phase2a),
            "phase2b_mae": _mae(source, phase2b),
            "phase2a_changed_over_16_percent": _changed_over(source, phase2a),
            "phase2b_changed_over_16_percent": _changed_over(source, phase2b),
        },
        "headers": {
            name: {
                "phase2a_mae": _mae(source_regions[name], phase2a_regions[name]),
                "phase2b_mae": _mae(source_regions[name], phase2b_regions[name]),
                "source_dark_ratio": _dark_ratio(source_regions[name]),
                "phase2a_dark_ratio": _dark_ratio(phase2a_regions[name]),
                "phase2b_dark_ratio": _dark_ratio(phase2b_regions[name]),
            }
            for name in HEADER_REGIONS_PT
        },
        "montage": str(montage_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--phase2a", type=Path, required=True)
    parser.add_argument("--phase2b", type=Path, required=True)
    parser.add_argument("--montage", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.source, args.phase2a, args.phase2b, args.montage)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
