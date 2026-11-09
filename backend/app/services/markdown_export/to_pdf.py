from pathlib import Path

from app.services.markdown_export.parser import render_html
from app.services.story import write_story_pdf

_CSS = """
body { font-family: sans-serif; font-size: 11pt; line-height: 1.55; color: #27241f; }
h1 { font-size: 22pt; margin: 0 0 10pt 0; }
h2 { font-size: 16pt; margin: 16pt 0 8pt 0; }
h3 { font-size: 13pt; margin: 12pt 0 6pt 0; }
p { margin: 0 0 8pt 0; }
li { margin-bottom: 3pt; }
code { font-family: monospace; }
pre { font-family: monospace; font-size: 9.5pt; background-color: #f4ede0; padding: 8pt; white-space: pre-wrap; }
blockquote { margin: 8pt 0; padding-left: 10pt; border-left: 3pt solid #d9cab0; color: #655e55; }
table { border-collapse: collapse; margin: 8pt 0; }
th, td { border: 1pt solid #d9cab0; padding: 4pt 6pt; }
th { background-color: #f4ede0; }
"""


def markdown_to_pdf(text: str, destination: Path) -> None:
    write_story_pdf(render_html(text), _CSS, destination)
