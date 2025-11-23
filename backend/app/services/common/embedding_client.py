# app/services/common/embedding_client.py
"""OpenAI embedding client for vector generation: single-text and batched embedding creation
with retry logic, used across jobs and resumes for semantic search and RAG."""
from __future__ import annotations
import logging
import time
import random
from typing import List, Optional, Sequence

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
    Generic embedding client.
    Safe to reuse across domains (resumes, jobs, etc.).
    """

    def __init__(self, model: Optional[str] = None):
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

    def embed_many(
        self,
        texts: Sequence[str],
        *,
        timeout: int = 90,
        batch_size: int = 64,
        max_retries: int = 3,
        base_backoff_sec: float = 1.0,
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using batched requests.
        This function is domain-agnostic and can be used anywhere in the app.
        """
        if not texts:
            return []

        client = _get_client()
        vectors: List[List[float]] = []

        # Simple chunking over input
        def _chunks(seq: Sequence[str], size: int):
            for i in range(0, len(seq), size):
                yield seq[i : i + size]

        for batch in _chunks(texts, max(1, batch_size)):
            attempt = 0
            while True:
                try:
                    resp = client.embeddings.create(model=self.model, input=list(batch), timeout=timeout)
                    batch_vecs = [d.embedding for d in resp.data]
                    vectors.extend(batch_vecs)
                    logger.debug("Embedded batch of %d items (dim=%d)", len(batch_vecs), len(batch_vecs[0]) if batch_vecs else -1)
                    break
                except (APIConnectionError, RateLimitError) as e:
                    attempt += 1
                    if attempt > max_retries:
                        logger.exception("OpenAI embed_many failed after retries: %s", e)
                        raise
                    sleep_for = base_backoff_sec * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                    logger.warning("embed_many transient error: %s; retrying in %.2fs (attempt %d/%d)", str(e), sleep_for, attempt, max_retries)
                    time.sleep(sleep_for)
                except BadRequestError as e:
                    # Usually won't recover (e.g., input too long); log and re-raise.
                    logger.exception("embed_many bad request: %s", e)
                    raise
                except Exception as e:
                    logger.exception("Unexpected error in embed_many: %s", e)
                    raise
        return vectors


# Export the default instance to match existing imports
default_embedding_client = OpenAIEmbeddingClient()
