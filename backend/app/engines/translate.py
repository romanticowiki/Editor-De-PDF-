"""Traducción de texto con un servicio externo rápido (Groq).

A diferencia del resto de herramientas, esta **envía el texto a traducir fuera del equipo**
(a la API de Groq). Por eso solo está disponible si hay una clave configurada en el entorno
(`PDFEDITOR_GROQ_API_KEY`). La clave se lee solo de ahí y nunca se registra ni se devuelve.

Se usa `urllib` de la biblioteca estándar para no añadir dependencias. El motor corre en un
hilo aparte (ver JobRunner), así que la llamada síncrona no bloquea el bucle de eventos.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Protocol

from app.services.errors import ToolError

logger = logging.getLogger(__name__)

# Códigos ISO 639-1 admitidos y su nombre para el prompt.
SUPPORTED_LANGUAGES: dict[str, str] = {
    "es": "español",
    "en": "inglés",
    "fr": "francés",
    "de": "alemán",
    "ko": "coreano",
}

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Cuánto texto agrupamos por llamada: menos llamadas, sin acercarnos al límite del modelo.
_MAX_CHARS_PER_BATCH = 6_000
_SERVICE_ERROR = "El servicio de traducción no respondió bien. Inténtalo de nuevo en un momento."


class TranslationEngine(Protocol):
    name: str

    def translate_many(self, texts: list[str], *, source: str, target: str) -> list[str]: ...


class GroqTranslationEngine:
    name = "Groq"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds

    def translate_many(self, texts: list[str], *, source: str, target: str) -> list[str]:
        results: list[str] = []
        for batch in _batches(texts, _MAX_CHARS_PER_BATCH):
            results.extend(self._translate_batch(batch, source, target))
        return results

    def _translate_batch(self, batch: list[str], source: str, target: str) -> list[str]:
        system = (
            f"Eres un traductor profesional. Traduce cada cadena del array 'items' de {SUPPORTED_LANGUAGES[source]} "
            f"a {SUPPORTED_LANGUAGES[target]}. Conserva el tono y el formato. Devuelve SOLO un objeto JSON "
            '{"translations": [...]} con la misma cantidad de elementos y en el mismo orden, sin comentarios.'
        )
        payload = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps({"items": batch}, ensure_ascii=False)},
            ],
        }
        content = self._call(payload)
        return _parse_translations(content, expected=len(batch))

    def _call(self, payload: dict[str, object]) -> str:
        request = urllib.request.Request(
            _GROQ_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # No registramos el cuerpo (podría repetir datos) ni la clave: solo el código.
            logger.warning("Groq respondió con código %s", exc.code)
            raise ToolError(_SERVICE_ERROR) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("No se pudo contactar con el servicio de traducción: %s", type(exc).__name__)
            raise ToolError(_SERVICE_ERROR) from exc
        except json.JSONDecodeError as exc:
            raise ToolError(_SERVICE_ERROR) from exc

        try:
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ToolError(_SERVICE_ERROR) from exc


def _parse_translations(content: str, *, expected: int) -> list[str]:
    try:
        data = json.loads(content)
        translations = data["translations"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ToolError(_SERVICE_ERROR) from exc

    if not isinstance(translations, list) or len(translations) != expected:
        raise ToolError(_SERVICE_ERROR)
    return [str(item) for item in translations]


def _batches(texts: list[str], max_chars: int) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    size = 0
    for text in texts:
        # Un texto que por sí solo supera el tope va en su propia llamada.
        if current and size + len(text) > max_chars:
            batches.append(current)
            current, size = [], 0
        current.append(text)
        size += len(text)
    if current:
        batches.append(current)
    return batches


def detect_translation_engine(*, api_key: str, model: str, timeout_seconds: float) -> TranslationEngine | None:
    key = api_key.strip()
    if not key:
        return None
    return GroqTranslationEngine(key, model, timeout_seconds)
