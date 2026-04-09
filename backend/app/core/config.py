"""
core/config.py - Centralised, typed application settings.

All tunables live here. Override via environment variables or .env file.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration loaded from env vars / defaults."""

    # -- Ollama ---------------------------------------------------------------
    ollama_url: str = Field(
        default="http://localhost:11434/api/generate",
        description="Ollama generation endpoint",
    )
    ollama_model: str = Field(
        default="llama3",
        description="Model name to use for generation",
    )
    ollama_timeout: int = Field(
        default=300,
        description="HTTP timeout in seconds for Ollama requests",
    )
    ollama_retries: int = Field(
        default=2,
        description="Number of attempts per Ollama call",
    )

    # -- Paths ----------------------------------------------------------------
    spec_dir: str = Field(default="spec", description="Directory for generated specs")
    spec_file: str = Field(default="spec/api.json", description="Main spec output path")
    backup_dir: str = Field(default="spec/backups", description="Spec backup directory")
    sdk_dir: str = Field(default="sdk", description="Root SDK output directory")
    sample_backend_dir: str = Field(
        default="sample_backend",
        description="Directory to watch for code changes",
    )
    default_backend_file: str = Field(
        default="sample_backend/app.py",
        description="Default backend file for generation",
    )

    # -- SDK ------------------------------------------------------------------
    sdk_languages: list[str] = Field(
        default=["python", "javascript"],
        description="Languages to generate SDKs for",
    )

    # -- Watcher --------------------------------------------------------------
    watcher_debounce: float = Field(
        default=3.0,
        description="Seconds to wait after file change before regenerating",
    )

    model_config = {"env_prefix": "APIDOC_", "env_file": ".env", "extra": "ignore"}


# Singleton instance
settings = Settings()
