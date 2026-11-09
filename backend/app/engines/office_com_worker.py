"""Convierte un documento a PDF con Microsoft Office vía COM, en un proceso aislado.

Uso: python office_com_worker.py <word|excel|powerpoint> <entrada> <salida.pdf>

Vive en su propio proceso a propósito: si Office se cuelga, el servidor lo mata por
timeout sin verse afectado. No importa nada de `app` para arrancar rápido.
"""

import sys
from collections.abc import Callable
from typing import Any

import pythoncom
import win32com.client

# Nunca ejecutar macros de documentos recibidos.
MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 3
WD_EXPORT_FORMAT_PDF = 17
WD_DO_NOT_SAVE_CHANGES = 0
XL_TYPE_PDF = 0
PP_ALERTS_NONE = 1
PP_SAVE_AS_PDF = 32
# Una contraseña falsa hace que un documento protegido falle al instante
# en vez de abrir un diálogo invisible que bloquearía el proceso.
_DUMMY_PASSWORD = "pdf-local-sin-contrasena"


def _convert_word(app: Any, source: str, target: str) -> None:
    app.Visible = False
    app.DisplayAlerts = 0
    document = app.Documents.Open(
        FileName=source,
        ConfirmConversions=False,
        ReadOnly=True,
        AddToRecentFiles=False,
        PasswordDocument=_DUMMY_PASSWORD,
        Visible=False,
        NoEncodingDialog=True,
    )
    try:
        document.ExportAsFixedFormat(OutputFileName=target, ExportFormat=WD_EXPORT_FORMAT_PDF)
    finally:
        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)


def _convert_excel(app: Any, source: str, target: str) -> None:
    app.Visible = False
    app.DisplayAlerts = False
    app.AskToUpdateLinks = False
    workbook = app.Workbooks.Open(
        Filename=source,
        UpdateLinks=0,
        ReadOnly=True,
        Password=_DUMMY_PASSWORD,
        IgnoreReadOnlyRecommended=True,
        AddToMru=False,
    )
    try:
        workbook.ExportAsFixedFormat(Type=XL_TYPE_PDF, Filename=target)
    finally:
        workbook.Close(SaveChanges=False)


def _convert_powerpoint(app: Any, source: str, target: str) -> None:
    app.DisplayAlerts = PP_ALERTS_NONE
    presentation = app.Presentations.Open(FileName=source, ReadOnly=True, Untitled=False, WithWindow=False)
    try:
        presentation.SaveAs(FileName=target, FileFormat=PP_SAVE_AS_PDF)
    finally:
        presentation.Close()


_APPS: dict[str, tuple[str, Callable[[Any, str, str], None]]] = {
    "word": ("Word.Application", _convert_word),
    "excel": ("Excel.Application", _convert_excel),
    "powerpoint": ("PowerPoint.Application", _convert_powerpoint),
}


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[1] not in _APPS:
        print("Uso: office_com_worker.py <word|excel|powerpoint> <entrada> <salida.pdf>", file=sys.stderr)
        return 2

    prog_id, convert = _APPS[argv[1]]
    pythoncom.CoInitialize()
    try:
        # DispatchEx: instancia nueva y privada; nunca toca los documentos que tengas abiertos.
        app = win32com.client.DispatchEx(prog_id)
        try:
            app.AutomationSecurity = MSO_AUTOMATION_SECURITY_FORCE_DISABLE
            convert(app, argv[2], argv[3])
        finally:
            try:
                app.Quit()
            except Exception:  # noqa: BLE001 - cerrar Office nunca debe ocultar el error original
                pass
    finally:
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
