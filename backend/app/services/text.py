import re

# Caracteres de control que rompen XML (docx, xlsx, pptx) y no aportan nada visible.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_control_chars(text: str) -> str:
    return _CONTROL_CHARS.sub("", text)


def decode_text(raw: bytes) -> str:
    """UTF-8 primero; si falla, Windows-1252 (lo habitual en .txt antiguos de Windows)."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")
