"""Structural and Microsoft Word validation for Phase 2B DOCX files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from docx import Document
import win32com.client


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


EXPECTED_HEADERS = {
    "4  COBERTURA DE LAS 15 ESTRATEGIAS": "11608E",
    "6  LECCIONES APRENDIDAS": "267249",
    "7  ENTREGA Y REFLEXIÓN": "113B60",
    "CALIFICACIÓN GLOBAL": "113B60",
}


def _cell_records(document_xml: bytes) -> list[dict[str, object]]:
    root = ET.fromstring(document_xml)
    records = []
    for cell in root.iter(f"{W}tc"):
        text = "".join(node.text or "" for node in cell.iter(f"{W}t"))
        fills = [node.get(f"{W}fill") for node in cell.iter(f"{W}shd") if node.get(f"{W}fill")]
        colors = [node.get(f"{W}val") for node in cell.iter(f"{W}color") if node.get(f"{W}val")]
        records.append({"text": text, "fills": fills, "text_colors": colors})
    return records


def structural_validation(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        records = _cell_records(archive.read("word/document.xml"))
        full_page_images = len(
            [name for name in archive.namelist() if name.startswith("word/media/") and not name.endswith("/")]
        )
    headers: dict[str, object] = {}
    for label, expected_fill in EXPECTED_HEADERS.items():
        matches = [record for record in records if label in str(record["text"])]
        normalized_fills = {
            str(fill).upper() for record in matches for fill in record["fills"]
        }
        normalized_colors = {
            str(color).upper() for record in matches for color in record["text_colors"]
        }
        headers[label] = {
            "present": bool(matches),
            "expected_fill": expected_fill,
            "matching_fills": sorted({fill for record in matches for fill in record["fills"]}),
            "matching_text_colors": sorted({color for record in matches for color in record["text_colors"]}),
            "has_expected_fill": expected_fill in normalized_fills,
            "has_white_text": "FFFFFF" in normalized_colors,
        }

    with tempfile.TemporaryDirectory(prefix="epdf-phase2b-") as temp:
        edited = Path(temp) / "edit-save-reopen.docx"
        document = Document(path)
        original_paragraphs = len(document.paragraphs)
        document.add_paragraph("EPDF_EDITABILITY_PROBE")
        document.save(edited)
        reopened = Document(edited)
        editable = any(paragraph.text == "EPDF_EDITABILITY_PROBE" for paragraph in reopened.paragraphs)
    return {
        "valid_zip": bad_member is None,
        "headers": headers,
        "media_files": full_page_images,
        "no_full_page_raster": full_page_images == 0,
        "editable_save_reopen": editable,
        "original_top_level_paragraphs": original_paragraphs,
    }


def word_validation(docx_paths: list[Path], pdf_dir: Path) -> dict[str, object]:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    application = win32com.client.DispatchEx("Word.Application")
    application.Visible = False
    application.DisplayAlerts = 0
    results: dict[str, object] = {}
    try:
        version = str(application.Version)
        build = str(application.Build)
        for path in docx_paths:
            destination = pdf_dir / f"{path.stem}.pdf"
            document = application.Documents.Open(str(path.resolve()), ReadOnly=True, AddToRecentFiles=False)
            try:
                pages = int(document.ComputeStatistics(2))
                document.ExportAsFixedFormat(str(destination.resolve()), 17)
            finally:
                document.Close(False)
            results[str(path)] = {
                "pages": pages,
                "exported_pdf": str(destination),
                "exported_pdf_bytes": destination.stat().st_size,
            }
    finally:
        application.Quit()
    return {"word_version": version, "word_build": build, "documents": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-docx", type=Path, required=True)
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    phase2b_documents = sorted(args.matrix_dir.glob("*-phase2b.docx"))
    documents = [args.main_docx, *phase2b_documents]
    result = {
        "structural": structural_validation(args.main_docx),
        "word": word_validation(documents, args.pdf_dir),
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
