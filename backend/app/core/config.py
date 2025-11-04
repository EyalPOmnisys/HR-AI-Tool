# path: backend/app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://omni:supersecret@localhost:5433/omniai"
    )
    APP_NAME: str = "HR-AI Backend"

    class Config:
        env_file = ".env"


settings = Settings()
