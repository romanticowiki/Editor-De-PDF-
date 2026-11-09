"""Conversión a PDF/A-2b (archivo a largo plazo) sin programas externos.

Primero se revisa lo que la norma prohíbe y no se puede arreglar sin alterar el contenido
(fuentes sin incrustar, adjuntos). Lo que sí es seguro corregir se corrige solo:
JavaScript, cifrado, metadatos XMP y perfil de color de salida.
"""

from functools import lru_cache
from pathlib import Path

import pikepdf
from PIL import ImageCms

from app.services.errors import ToolError
from app.services.pdf_io import damaged_message, locked_message, open_pdf

PDFA_PART = "2"
PDFA_CONFORMANCE = "B"
_SRGB_IDENTIFIER = "sRGB IEC61966-2.1"
_PDFA_OUTPUT_INTENT = pikepdf.Name("/GTS_PDFA1")
_MAX_LISTED_FONTS = 3
_NOT_EMBEDDED = "n/a"


def convert_to_pdfa(source: Path, destination: Path, *, name: str) -> None:
    _preflight(source, name)

    try:
        pdf = pikepdf.open(source)
    except pikepdf.PasswordError as exc:
        raise ToolError(locked_message(name)) from exc
    except pikepdf.PdfError as exc:
        raise ToolError(damaged_message(name)) from exc

    with pdf:
        _remove_javascript(pdf)
        _ensure_output_intent(pdf)
        _write_pdfa_metadata(pdf, title=Path(name).stem)
        # La norma prohíbe el cifrado.
        pdf.save(destination, encryption=False, min_version="1.7")


def _preflight(source: Path, name: str) -> None:
    with open_pdf(source, name) as document:
        missing_fonts = sorted(
            {
                basefont
                for page in document
                for (_xref, extension, font_type, basefont, *_rest) in page.get_fonts()
                if extension == _NOT_EMBEDDED and font_type != "Type3"
            }
        )
        if missing_fonts:
            listed = ", ".join(missing_fonts[:_MAX_LISTED_FONTS])
            raise ToolError(
                f"«{name}» usa fuentes sin incrustar ({listed}). "
                "Expórtalo de nuevo incrustando las fuentes y vuelve a intentarlo."
            )
        if document.embfile_count() > 0:
            raise ToolError(f"«{name}» lleva archivos adjuntos y el formato de archivo no los admite. Quítalos primero.")


def _remove_javascript(pdf: pikepdf.Pdf) -> None:
    names = pdf.Root.get("/Names")
    if isinstance(names, pikepdf.Dictionary) and "/JavaScript" in names:
        del names["/JavaScript"]

    open_action = pdf.Root.get("/OpenAction")
    if isinstance(open_action, pikepdf.Dictionary) and open_action.get("/S") == pikepdf.Name.JavaScript:
        del pdf.Root["/OpenAction"]

    # Acciones automáticas (al abrir, cerrar, imprimir…) del documento y de cada página.
    for holder in (pdf.Root, *(page.obj for page in pdf.pages)):
        if "/AA" in holder:
            del holder["/AA"]


def _ensure_output_intent(pdf: pikepdf.Pdf) -> None:
    intents = pdf.Root.get("/OutputIntents")
    if isinstance(intents, pikepdf.Array) and any(intent.get("/S") == _PDFA_OUTPUT_INTENT for intent in intents):
        return

    profile = pdf.make_stream(_srgb_icc_profile())
    profile["/N"] = 3
    intent = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.OutputIntent,
            S=_PDFA_OUTPUT_INTENT,
            OutputConditionIdentifier=_SRGB_IDENTIFIER,
            Info=_SRGB_IDENTIFIER,
            DestOutputProfile=profile,
        )
    )
    pdf.Root.OutputIntents = pikepdf.Array([intent])


def _write_pdfa_metadata(pdf: pikepdf.Pdf, *, title: str) -> None:
    with pdf.open_metadata(set_pikepdf_as_editor=False) as metadata:
        metadata["pdfaid:part"] = PDFA_PART
        metadata["pdfaid:conformance"] = PDFA_CONFORMANCE
        if not metadata.get("dc:title"):
            metadata["dc:title"] = title


@lru_cache(maxsize=1)
def _srgb_icc_profile() -> bytes:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
