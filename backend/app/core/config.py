# app/core/config.py
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"  # -> /app/app/.env בקונטיינר

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="postgresql+psycopg://omni:supersecret@localhost:5433/omniai")
    APP_NAME: str = "HR-AI Backend"
    OLLAMA_BASE_URL: str = "http://Omniai:11434"
    LLM_CHAT_MODEL: str = "llama3:latest"
    ANALYSIS_VERSION: int = 1

    class Config:
        env_file = str(ENV_PATH)
        case_sensitive = True

settings = Settings()
