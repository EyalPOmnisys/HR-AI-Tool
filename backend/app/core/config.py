# app/core/config.py
from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# Resolve the .env alongside the backend package root (adjust if your layout differs)
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    # --- Database ---
    DATABASE_URL: str = Field(..., description="Full PostgreSQL connection URL")

    # --- App info ---
    APP_NAME: str = Field(default="HR-AI Backend")

    # --- AI Models & Services (Ollama keys kept for backward compatibility if you still use them elsewhere) ---
    OLLAMA_BASE_URL: str | None = Field(default=None, description="Base URL of local Ollama server")
    LLM_CHAT_MODEL: str | None = Field(default=None, description="Model used for job analysis (legacy)")
    EMBEDDING_MODEL: str | None = Field(default=None, description="Model used for text embeddings (legacy)")
    ANALYSIS_VERSION: int = Field(default=1)

    # --- OpenAI Integration ---
    OPENAI_API_KEY: str | None = Field(default=None, description="API key for OpenAI services")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="Default OpenAI model for chat/completions")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-large", description="Default OpenAI model for embeddings")

    # --- CV analysis ---
    USE_LLM_EXTRACTION: bool = True
    EXTRACTION_VERSION: int = 2
    EXPERIENCE_CLUSTERING_VERSION: int = 2

    class Config:
        env_file = str(ENV_PATH)
        case_sensitive = True


settings = Settings()
