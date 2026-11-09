from fastapi.testclient import TestClient

from app.api.dependencies import get_translation_engine
from app.engines.translate import GroqTranslationEngine, _batches, _parse_translations, detect_translation_engine
from app.services.errors import ToolError
from tests.factories import pdf_bytes, pdf_text, scanned_pdf_bytes, upload

URL = "/api/v1/translate"


class FakeTranslationEngine:
    """Traduce de mentira: antepone el idioma destino. Registra lo que se le pide."""

    name = "Fake Translate"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, tuple[str, ...]]] = []

    def translate_many(self, texts: list[str], *, source: str, target: str) -> list[str]:
        self.calls.append((source, target, tuple(texts)))
        return [f"[{target}] {text}" for text in texts]


def _use(client: TestClient, engine: object) -> None:
    client.app.dependency_overrides[get_translation_engine] = lambda: engine  # type: ignore[attr-defined]


def test_translate_replaces_text_and_keeps_the_page(client: TestClient) -> None:
    engine = FakeTranslationEngine()
    _use(client, engine)

    response = client.post(
        URL,
        files=[upload("informe.pdf", pdf_bytes(text="Hola mundo"))],
        data={"source_lang": "es", "target_lang": "en", "consent": "true"},
    )

    assert response.status_code == 200, response.text
    assert "informe-en.pdf" in response.headers["content-disposition"]
    assert response.headers["x-result-count"] == "1"
    text = pdf_text(response.content)
    assert "[en] Hola mundo" in text
    assert "Hola mundo" not in text.replace("[en] Hola mundo", "")  # el original quedó borrado
    assert engine.calls == [("es", "en", ("Hola mundo",))]


def test_translate_rejects_same_language(client: TestClient) -> None:
    _use(client, FakeTranslationEngine())

    response = client.post(
        URL,
        files=[upload("a.pdf", pdf_bytes(text="Hola"))],
        data={"source_lang": "es", "target_lang": "es", "consent": "true"},
    )

    assert response.status_code == 422
    assert "destino" in response.json()["detail"]


def test_translate_rejects_unsupported_language(client: TestClient) -> None:
    _use(client, FakeTranslationEngine())

    response = client.post(
        URL,
        files=[upload("a.pdf", pdf_bytes(text="Hola"))],
        data={"source_lang": "es", "target_lang": "it", "consent": "true"},
    )

    assert response.status_code == 422  # el enum de FastAPI rechaza "it"


def test_translate_explains_documents_without_text(client: TestClient) -> None:
    _use(client, FakeTranslationEngine())

    response = client.post(
        URL,
        files=[upload("escaneo.pdf", scanned_pdf_bytes("Factura"))],
        data={"source_lang": "es", "target_lang": "en", "consent": "true"},
    )

    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]


def test_translate_unavailable_without_key(client: TestClient) -> None:
    _use(client, None)

    response = client.post(
        URL,
        files=[upload("a.pdf", pdf_bytes(text="Hola"))],
        data={"source_lang": "es", "target_lang": "en", "consent": "true"},
    )

    assert response.status_code == 503
    assert "Groq" in response.json()["detail"]


def test_translate_requires_explicit_external_service_consent(client: TestClient) -> None:
    engine = FakeTranslationEngine()
    _use(client, engine)

    response = client.post(
        URL,
        files=[upload("nombre-confidencial.pdf", pdf_bytes(text="Texto privado"))],
        data={"source_lang": "es", "target_lang": "en"},
    )

    assert response.status_code == 422
    assert "aceptar" in response.json()["detail"]
    assert engine.calls == []


# ——— Unidades del motor, sin red ———


def test_detect_engine_needs_a_key() -> None:
    assert detect_translation_engine(api_key="   ", model="m", timeout_seconds=1) is None
    engine = detect_translation_engine(api_key="secreta", model="m", timeout_seconds=1)
    assert isinstance(engine, GroqTranslationEngine)


def test_batches_group_by_char_budget() -> None:
    # Con tope 10, "aaaaa"(5)+"bbbbb"(5) caben juntos; "cccccc"(6) abre otro grupo.
    assert _batches(["aaaaa", "bbbbb", "cccccc"], 10) == [["aaaaa", "bbbbb"], ["cccccc"]]
    # Un texto mayor que el tope va solo, sin romperse.
    assert _batches(["x" * 50], 10) == [["x" * 50]]


def test_parse_translations_validates_shape() -> None:
    assert _parse_translations('{"translations": ["hola", "mundo"]}', expected=2) == ["hola", "mundo"]
    for bad in ('{"translations": ["solo uno"]}', "no es json", '{"otra": []}'):
        try:
            _parse_translations(bad, expected=2)
        except ToolError:
            continue
        raise AssertionError(f"Debió rechazar: {bad!r}")
