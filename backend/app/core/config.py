"""Configuración central. Todo valor ajustable vive aquí y se lee del entorno."""

import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PDFEDITOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EPDF"
    version: str = "0.3.0"
    environment: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Solo loopback: los PDF nunca salen del equipo.
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    rate_limit_requests: int = Field(default=120, ge=1)
    rate_limit_window_seconds: float = Field(default=60.0, gt=0)

    # Límites de subida. El frontend los replica en src/config/limits.ts.
    max_merge_files: int = Field(default=30, ge=2)
    max_upload_file_mb: int = Field(default=100, ge=1)

    # Defensa ante bombas de descompresión (docx/xlsx/pptx/epub son ZIP): un archivo
    # pequeño que se descomprime en gigabytes agotaría la memoria al procesarlo.
    max_archive_uncompressed_mb: int = Field(default=600, ge=1)
    max_archive_ratio: float = Field(default=200.0, gt=1)

    # Trabajos pesados. PyMuPDF no admite varios hilos a la vez (ver su documentación),
    # así que por defecto se procesa un documento cada vez y el resto espera turno.
    max_concurrent_jobs: int = Field(default=1, ge=1)
    job_timeout_seconds: float = Field(default=180.0, gt=0)
    office_timeout_seconds: float = Field(default=150.0, gt=0)
    ocr_timeout_seconds: float = Field(default=900.0, gt=0)
    translate_timeout_seconds: float = Field(default=600.0, gt=0)

    # Traducir PDF (Groq): a diferencia del resto, envía el texto a un servicio externo.
    # Sin clave, la herramienta aparece como no disponible. La clave solo se lee del entorno.
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout_seconds: float = Field(default=60.0, gt=0)

    # Carpeta de trabajos temporales: se vacía sola al responder y al arrancar.
    workspace_dir: Path = Field(default_factory=lambda: Path(tempfile.gettempdir()) / "pdf-local")
    # Fuerza LibreOffice indicando la ruta a soffice (si no, se detecta el software instalado).
    libreoffice_path: Path | None = None
    # Carpeta con los datos de idioma de Tesseract (*.traineddata) para el OCR.
    tessdata_dir: Path | None = None
    # Carpeta con el frontend ya compilado (dist). Si existe, FastAPI la sirve en «/»,
    # así todo vive en un solo puerto (Docker y la app de escritorio). Vacío en desarrollo.
    frontend_dist: Path | None = None

    @field_validator("tessdata_dir", "libreoffice_path", "frontend_dist")
    @classmethod
    def resolve_from_backend_dir(cls, path: Path | None) -> Path | None:
        # Una ruta relativa del .env se interpreta desde backend/, no desde donde se lanzó el proceso.
        return path if path is None or path.is_absolute() else (BACKEND_DIR / path).resolve()

    @field_validator("cors_origins")
    @classmethod
    def forbid_wildcard_origin(cls, origins: list[str]) -> list[str]:
        # Un "*" expondría la API local a cualquier web abierta en el navegador.
        if "*" in origins:
            raise ValueError("cors_origins no admite '*'; lista los orígenes explícitos.")
        return origins

    @model_validator(mode="after")
    def office_timeout_below_job_timeout(self) -> Self:
        # El motor de Office debe matar su subproceso antes de que el trabajo expire.
        if self.office_timeout_seconds >= self.job_timeout_seconds:
            raise ValueError("office_timeout_seconds debe ser menor que job_timeout_seconds.")
        return self

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def max_upload_file_bytes(self) -> int:
        return self.max_upload_file_mb * 1024 * 1024

    @property
    def max_archive_uncompressed_bytes(self) -> int:
        return self.max_archive_uncompressed_mb * 1024 * 1024

    @property
    def max_request_bytes(self) -> int:
        # 1 MB de margen para las cabeceras multipart de cada parte.
        return self.max_merge_files * self.max_upload_file_bytes + 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
