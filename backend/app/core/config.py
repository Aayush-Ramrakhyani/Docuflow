"""
Application configuration, loaded from environment variables via Pydantic Settings.

Every value can be overridden by an env var of the same name (case-insensitive).
Secrets (SECRET_KEY, DATABASE_URL, API keys) have NO defaults and must be supplied
by the environment — nothing sensitive is ever hardcoded here.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",            # Load from .env in local dev
        env_file_encoding="utf-8",
        case_sensitive=False,       # ENV vars match field names case-insensitively
        extra="ignore",             # Ignore unknown env vars rather than erroring
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "DocuFlow"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str                 # Required — signs JWTs; must be high-entropy in prod
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]  # CORS allowlist

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str               # Required — e.g. postgresql+asyncpg://user:pass@host/db
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis / Celery ───────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"      # Separate DB index per role
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Auth ──────────────────────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15   # Short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7      # Long-lived refresh token (httpOnly cookie)
    ALGORITHM: str = "HS256"                # JWT signing algorithm

    # ── Storage (S3 / MinIO) ──────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["s3", "minio"] = "minio"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_DOCUMENTS: str = "docuflow-documents"
    S3_BUCKET_EXPORTS: str = "docuflow-exports"
    S3_ENDPOINT_URL: str | None = None            # Set to the MinIO URL in local/dev
    SIGNED_URL_EXPIRATION_SECONDS: int = 3600     # Download URLs expire after 1 hour

    # ── File Upload ───────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_MIME_TYPES: list[str] = [   # Enforced server-side via magic-byte detection
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
    ]

    # ── AI Providers ──────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-6"
    AI_MAX_TOKENS: int = 4096

    # ── Rate Limiting (slowapi limit strings) ─────────────────────────────────
    RATE_LIMIT_AUTH: str = "10/minute"    # Login/register/forgot-password
    RATE_LIMIT_UPLOAD: str = "20/hour"    # Document uploads
    RATE_LIMIT_API: str = "100/minute"    # General API

    # ── Email ─────────────────────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: EmailStr = "noreply@docuflow.app"  # type: ignore[assignment]

    # ── First superadmin (optionally seeded on startup) ───────────────────────
    FIRST_SUPERADMIN_EMAIL: str = ""
    FIRST_SUPERADMIN_PASSWORD: str = ""

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list[str]) -> list[str]:
        # Allow a comma-separated string in the env var → parsed into a list
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        # Used to toggle debug docs, secure cookies, HSTS, etc.
        return self.ENVIRONMENT == "production"

    @property
    def max_upload_bytes(self) -> int:
        # Convenience: configured MB limit expressed in bytes
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    # Cached so the .env file + env vars are parsed exactly once per process
    return Settings()
