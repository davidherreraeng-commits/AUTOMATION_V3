from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Configuración central de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RPA_",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = (
        "development"
    )

    app_name: str = "Automatización Gestión Transparente"
    api_prefix: str = "/api/v1"

    database_path: Path = Path("data/rpa.sqlite3")
    upload_directory: Path = Path("data/uploads")
    upload_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
    )
    default_budget_year: int = Field(default=2026, ge=2000, le=2100)

    jwt_secret_key: SecretStr = SecretStr(
        "development-only-change-this-secret-key-2026"
    )
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "modulo-automatizacion"
    jwt_audience: str = "rpa-frontend"
    access_token_minutes: int = Field(default=60, ge=5, le=1440)

    auth_cookie_name: str = "rpa_access_token"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    fernet_key: SecretStr = SecretStr("")

    portal_login_url: str = (
        "https://rendicioncga.gestiontransparente.com/login/"
    )
    portal_credential_test_headless: bool = False
    portal_credential_test_timeout_seconds: float = Field(
        default=25.0,
        ge=5.0,
        le=120.0,
    )
    portal_driver_path: Path | None = None
    portal_chrome_binary: Path | None = None

    batch_execution_enabled: bool = False
    batch_execution_headless: bool = False
    batch_execution_timeout_seconds: float = Field(
        default=25.0,
        ge=5.0,
        le=120.0,
    )
    batch_execution_credential_max_age_hours: int = Field(
        default=24,
        ge=1,
        le=168,
    )
    batch_execution_reject_unit_test_values: bool = True
    batch_execution_workers: int = Field(default=1, ge=1, le=4)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]
        return value

    @field_validator("api_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        normalized = "/" + str(value).strip().strip("/")
        return normalized if normalized != "/" else ""

    @field_validator("portal_login_url")
    @classmethod
    def validate_portal_login_url(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized.startswith(("http://", "https://")):
            raise ValueError(
                "RPA_PORTAL_LOGIN_URL debe ser una URL HTTP o HTTPS."
            )
        return normalized

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        jwt_secret = self.jwt_secret_key.get_secret_value()
        fernet_key = self.fernet_key.get_secret_value().strip()

        if self.environment == "production" and len(jwt_secret) < 32:
            raise ValueError(
                "RPA_JWT_SECRET_KEY debe tener al menos "
                "32 caracteres en producción."
            )

        if self.environment == "production" and not fernet_key:
            raise ValueError(
                "RPA_FERNET_KEY es obligatoria en producción."
            )

        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SameSite=None requiere cookies Secure.")

        return self

    @cached_property
    def resolved_database_path(self) -> Path:
        return self._resolve_project_path(self.database_path)

    @cached_property
    def resolved_upload_directory(self) -> Path:
        return self._resolve_project_path(self.upload_directory)

    @staticmethod
    def _resolve_project_path(path: Path) -> Path:
        resolved = path.expanduser()
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / resolved
        return resolved.resolve()

    def ensure_runtime_directories(self) -> None:
        self.resolved_database_path.parent.mkdir(parents=True, exist_ok=True)
        self.resolved_upload_directory.mkdir(parents=True, exist_ok=True)
