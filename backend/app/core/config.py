# app/core/config.py
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    # --- Database ---
    DATABASE_URL: str = Field(..., description="Full PostgreSQL connection URL")

    # --- App info ---
    APP_NAME: str = Field(default="HR-AI Backend")

    # --- AI Models & Services ---
    OLLAMA_BASE_URL: str = Field(..., description="Base URL of local Ollama server")
    LLM_CHAT_MODEL: str = Field(..., description="Model used for job analysis")
    EMBEDDING_MODEL: str = Field(..., description="Model used for text embeddings")
    ANALYSIS_VERSION: int = Field(default=1)

    # --- CV analysis ---
    USE_LLM_EXTRACTION: bool = True
    EXTRACTION_VERSION: int = 1

    class Config:
        env_file = str(ENV_PATH)
        case_sensitive = True


settings = Settings()
