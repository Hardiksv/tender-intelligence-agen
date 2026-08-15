from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/tender_db"
    TEST_DATABASE_URL: str = "postgresql://test:test@localhost:5432/tender_test"

    # LLM Settings (LiteLLM)
    LLM_API_KEY: str = "mock_key_for_testing"
    LLM_MODEL: str = "gemini/gemini-2.5-flash"
    LLM_FALLBACK_MODEL: str = "gemini/gemini-2.5-pro"

    # Embeddings Settings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Application Settings
    TIMEZONE: str = "Asia/Kolkata"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    LOG_LEVEL: str = "INFO"

    # Feature Flags & Automation
    INGESTION_ENABLED: bool = True
    DISCOVERY_ENABLED: bool = False
    DISCOVERY_INTERVAL_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
