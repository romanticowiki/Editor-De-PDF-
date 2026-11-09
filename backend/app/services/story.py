"""HTML/CSS a PDF paginado con el motor Story de MuPDF (sin navegador ni acceso a red)."""

from pathlib import Path

import pymupdf

PAGE = pymupdf.paper_rect("a4")
MARGIN_POINTS = 56  # ~2 cm


def write_story_pdf(html: str, css: str, destination: Path) -> None:
    story = pymupdf.Story(html=html, user_css=css)
    content_area = PAGE + (MARGIN_POINTS, MARGIN_POINTS, -MARGIN_POINTS, -MARGIN_POINTS)

    writer = pymupdf.DocumentWriter(str(destination))
    try:
        has_more = True
        while has_more:
            device = writer.begin_page(PAGE)
            has_more, _ = story.place(content_area)
            story.draw(device)
            writer.end_page()
    finally:
        writer.close()
