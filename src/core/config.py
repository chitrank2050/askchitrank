"""
Central configuration module for askchitrank.

Defines application settings using Pydantic BaseSettings.
Settings are resolved in this priority order:
    1. Environment variables
    2. .env.<APP_ENV> file (e.g. .env.dev, .env.prod)
    3. Default values below

Responsibility: single source of truth for all runtime configuration.
Does NOT: handle requests, define routes, or run inference.

Usage:
    from src.core.config import settings
"""

import os
from importlib.metadata import metadata
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_meta = metadata("askchitrank")
_APP_ENV = os.getenv("APP_ENV", "dev")


class _Settings(BaseSettings):
    """Application settings with environment variable override support."""

    # ----------------------------------------------------------------
    # 📦  Application metadata
    # ----------------------------------------------------------------
    APP_NAME: str = _meta["Name"].replace("-", " ").title()
    APP_VERSION: str = _meta["Version"]
    APP_DESCRIPTION: str = _meta["Summary"]
    APP_ENV: str = _APP_ENV

    # ----------------------------------------------------------------
    # 🌐  API
    # ----------------------------------------------------------------
    API_TITLE: str = "Ask Chitrank API"
    API_DESCRIPTION: str = (
        "RAG-powered AI assistant that answers questions about Chitrank "
        "using resume, portfolio, and work history."
    )
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_DEBUG: bool = False
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"
    API_OPENAPI_URL: str = "/openapi.json"
    API_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    API_ALLOW_CREDENTIALS: bool = True
    API_ALLOWED_METHODS: list[str] = ["*"]
    API_ALLOWED_HEADERS: list[str] = ["*"]

    # ----------------------------------------------------------------
    # 🤖  LLM
    # ----------------------------------------------------------------
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.1  # low — factual answers only

    # ----------------------------------------------------------------
    # 🧠  Embeddings
    # ----------------------------------------------------------------
    VOYAGE_API_KEY: str = ""
    VOYAGE_MODEL: str = "voyage-3-lite"
    EMBEDDING_DIMENSIONS: int = 512

    # ----------------------------------------------------------------
    # 🗄️  Database
    # ----------------------------------------------------------------
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ----------------------------------------------------------------
    # 📝  Sanity CMS
    # ----------------------------------------------------------------
    SANITY_PROJECT_ID: str = ""
    SANITY_DATASET: str = "production"
    SANITY_API_TOKEN: str = ""
    SANITY_API_VERSION: str = "2024-01-01"

    # ----------------------------------------------------------------
    # 🔍  RAG
    # ----------------------------------------------------------------
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 8

    # ----------------------------------------------------------------
    # 💾  Cache
    # ----------------------------------------------------------------
    CACHE_SIMILARITY_THRESHOLD: float = 0.95
    CACHE_TTL_DAYS: int = 7

    # ----------------------------------------------------------------
    # ⚙️  Environment
    # ----------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=[".env", f".env.{_APP_ENV}"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----------------------------------------------------------------
    # 📝  Logging
    # ----------------------------------------------------------------
    LOG_SILENCE_MODULES: list[str] = [
        "httpx",
        "httpcore",
        "urllib3",
    ]
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: str = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>"
    )
    ENABLE_LOG_FILE: bool = False
    LOG_FILE_NAME: str = "askchitrank.log"
    LOG_FILE_RETENTION: str = "30 days"
    LOG_FILE_FORMAT: str = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )

    # ----------------------------------------------------------------
    # ✅  Validators
    # ----------------------------------------------------------------
    @field_validator("API_PORT")
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        """Validate API_PORT is within valid TCP port range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"API_PORT must be between 1 and 65535, got {v}")
        return v

    @field_validator("LLM_TEMPERATURE")
    @classmethod
    def temperature_must_be_valid(cls, v: float) -> float:
        """Validate LLM temperature is within 0-1 range."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"LLM_TEMPERATURE must be between 0 and 1, got {v}")
        return v


# Singleton
settings = _Settings()
