import pytest
from pydantic import ValidationError
from app.config import Settings


def test_h15_production_requires_strong_secret_key():
    with pytest.raises((ValidationError, ValueError)):
        Settings(ENV="production", SECRET_KEY="nexora-super-secret-key-change-in-production-2026-fesc")

    with pytest.raises((ValidationError, ValueError)):
        Settings(ENV="production", SECRET_KEY="too-short")

    prod_settings = Settings(
        ENV="production",
        SECRET_KEY="a-very-strong-random-production-secret-key-2026-xyz",
        BACKEND_CORS_ORIGINS="https://app.nexora.co, *, http://localhost:3000",
    )
    assert prod_settings.ENV == "production"
    assert "*" not in prod_settings.BACKEND_CORS_ORIGINS
    assert "https://app.nexora.co" in prod_settings.BACKEND_CORS_ORIGINS

