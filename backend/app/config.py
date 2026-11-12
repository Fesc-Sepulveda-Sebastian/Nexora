import json
import os
from typing import List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_SECRET_KEYS = {
    "",
    "nexora-super-secret-key-change-in-production-2026-fesc",
    "dev-only-insecure-secret-key-nexora-2026",
    "replace-with-32-plus-char-random-secret-key",
    "changeme",
    "secret",
}


class Settings(BaseSettings):
    PROJECT_NAME: str = "Nexora API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = Field(default_factory=lambda: os.getenv("ENV", os.getenv("ENVIRONMENT", "development")))

    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", "dev-only-insecure-secret-key-nexora-2026")
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database - Default to SQLite for zero-config local run, easily switchable to PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./nexora.db",
    )

    # MongoDB for immutable metrics snapshots
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "nexora_analytics")

    # S3 / MinIO Storage (separated internal Docker host vs public client URL)
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9005")
    MINIO_INTERNAL_ENDPOINT: str = os.getenv(
        "MINIO_INTERNAL_ENDPOINT",
        os.getenv("MINIO_ENDPOINT", "localhost:9005"),
    )
    MINIO_PUBLIC_ENDPOINT: str = os.getenv(
        "MINIO_PUBLIC_ENDPOINT",
        os.getenv("MINIO_ENDPOINT", "localhost:9005"),
    )
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "nexora-evidence")
    MINIO_SECURE: bool = False
    LOCAL_STORAGE_DIR: str = os.getenv("LOCAL_STORAGE_DIR", "./uploads")

    # CORS - explicit origins without wildcard alongside allow_credentials=True
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            raw = v.strip()
            if raw.startswith("["):
                return json.loads(raw)
            return [origin.strip() for origin in raw.split(",") if origin.strip() and origin.strip() != "*"]
        if isinstance(v, list):
            return [origin for origin in v if origin != "*"]
        return v

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.ENV.lower() in ("prod", "production"):
            if self.SECRET_KEY in _WEAK_SECRET_KEYS or len(self.SECRET_KEY.strip()) < 32:
                raise ValueError(
                    "En entorno de producción (ENV=production), SECRET_KEY debe configurarse con al menos 32 caracteres aleatorios."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
