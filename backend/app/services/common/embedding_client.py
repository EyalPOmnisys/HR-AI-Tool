# app/services/common/embedding_client.py
from __future__ import annotations
import logging
from typing import List, Optional

from openai import OpenAI, APIConnectionError, RateLimitError, BadRequestError
from app.core.config import settings

logger = logging.getLogger("ai.embed")

_client: Optional[OpenAI] = None


def _require_api_key() -> str:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
    return settings.OPENAI_API_KEY


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _require_api_key()
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("OpenAI embedding client initialized")
    return _client


class OpenAIEmbeddingClient:
    """
    Simple embedding client used by the ingestion pipeline.
    Provides .embed(text) -> List[float]
    """

    def __init__(self, model: Optional[str] = None):
        # Prefer explicit OpenAI embedding model from settings
        self.model = model or settings.OPENAI_EMBEDDING_MODEL

    def embed(self, text: str, timeout: int = 60) -> List[float]:
        """
        Generate a single embedding vector for the given text.
        """
        try:
            client = _get_client()
            resp = client.embeddings.create(model=self.model, input=text, timeout=timeout)
            vec = resp.data[0].embedding
            logger.debug("Generated embedding vector (dim=%d)", len(vec))
            return vec
        except (APIConnectionError, RateLimitError, BadRequestError) as e:
            logger.exception("OpenAI embed error: %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error in embed: %s", e)
            raise


# Export the default instance to match existing imports
default_embedding_client = OpenAIEmbeddingClient()
