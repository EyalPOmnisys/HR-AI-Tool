# app/core/config.py
from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# Resolve the .env alongside the backend package root (adjust if your layout differs)
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    
    # --- Database ---
    DATABASE_URL: str = Field(..., description="Full PostgreSQL connection URL (sync, e.g., postgresql+psycopg://...)")
    DATABASE_URL_ASYNC: str | None = Field(
        default=None,
        description="Async PostgreSQL URL (e.g., postgresql+asyncpg://...). Optional; derived if missing.",
    )

    # --- App info ---
    APP_NAME: str = Field(default="HR-AI Backend")

    # --- AI Models & Services (legacy-friendly fields kept for compatibility) ---
    OLLAMA_BASE_URL: str | None = Field(default=None, description="Base URL of local Ollama server")
    LLM_CHAT_MODEL: str | None = Field(default=None, description="Model used for job analysis (legacy)")
    EMBEDDING_MODEL: str | None = Field(default=None, description="Model used for text embeddings (legacy)")
    ANALYSIS_VERSION: int = Field(default=1)

    # --- OpenAI Integration ---
    OPENAI_API_KEY: str | None = Field(default=None, description="API key for OpenAI services")
    OPENAI_MODEL: str | None = Field(default=None, description="Default OpenAI model for chat/completions (optional if using Ollama)")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-large", description="Default OpenAI model for embeddings")

    # --- Semantic Matching ---
    SENTENCE_TRANSFORMER_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="SentenceTransformer model for semantic title matching (fast, ~80MB, enhanced with keyword boost)"
    )

    # --- CV analysis ---
    USE_LLM_EXTRACTION: bool = True
    EXTRACTION_VERSION: int = 2
    EXPERIENCE_CLUSTERING_VERSION: int = 2

    class Config:
        env_file = str(ENV_PATH)
        case_sensitive = True

    @property
    def database_url_async_effective(self) -> str:
        """
        Prefer DATABASE_URL_ASYNC; if it's missing, derive from DATABASE_URL by swapping
        '+psycopg' -> '+asyncpg'. If no swap is possible, return DATABASE_URL as-is.
        """
        if self.DATABASE_URL_ASYNC:
            return self.DATABASE_URL_ASYNC
        if "+psycopg" in self.DATABASE_URL:
            return self.DATABASE_URL.replace("+psycopg", "+asyncpg")
        return self.DATABASE_URL


settings = Settings()
