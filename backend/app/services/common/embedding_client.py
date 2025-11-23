# app/services/common/embedding_client.py
"""Embedding client for vector generation: supports OpenAI and Ollama (local) models.
Used across jobs and resumes for semantic search and RAG."""
from __future__ import annotations
import logging
import time
import random
import requests
from typing import List, Optional, Sequence

from openai import OpenAI, APIConnectionError, RateLimitError, BadRequestError
from app.core.config import settings

logger = logging.getLogger("ai.embed")

_client: Optional[OpenAI] = None


def _require_api_key() -> str:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
    return settings.OPENAI_API_KEY


def _get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _require_api_key()
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("OpenAI embedding client initialized")
    return _client


class EmbeddingClient:
    """
    Generic embedding client supporting both OpenAI and Ollama.
    """

    def __init__(self, model: Optional[str] = None):
        # Prioritize passed model, then EMBEDDING_MODEL (Ollama), then OPENAI_EMBEDDING_MODEL
        self.model = model or settings.EMBEDDING_MODEL or settings.OPENAI_EMBEDDING_MODEL
        # Determine provider based on configuration
        # If EMBEDDING_MODEL is set (and not empty), we assume it's for Ollama/Local.
        self.use_ollama = bool(settings.EMBEDDING_MODEL)
        
        if self.use_ollama:
            logger.info(f"Initialized EmbeddingClient with Ollama model: {self.model} at {settings.OLLAMA_BASE_URL}")
        else:
            logger.info(f"Initialized EmbeddingClient with OpenAI model: {self.model}")

    def embed(self, text: str, timeout: int = 60) -> List[float]:
        """
        Generate a single embedding vector for the given text.
        """
        if self.use_ollama:
            return self._embed_ollama(text, timeout=timeout)
        return self._embed_openai(text, timeout=timeout)

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
        Generate embeddings for a list of texts.
        """
        if not texts:
            return []

        if self.use_ollama:
            # Ollama /api/embeddings does not support batching in the same way.
            # We will do sequential calls.
            vectors = []
            for text in texts:
                vectors.append(self._embed_ollama(text, timeout=timeout))
            return vectors

        return self._embed_openai_many(
            texts, 
            timeout=timeout, 
            batch_size=batch_size, 
            max_retries=max_retries, 
            base_backoff_sec=base_backoff_sec
        )

    def _embed_ollama(self, text: str, timeout: int) -> List[float]:
        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        url = f"{base_url}/api/embeddings"
        try:
            payload = {
                "model": self.model,
                "prompt": text
            }
            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            vec = data.get("embedding")
            if not vec:
                raise ValueError("No embedding returned from Ollama")
            return vec
        except Exception as e:
            logger.exception("Ollama embed error: %s", e)
            raise

    def _embed_openai(self, text: str, timeout: int) -> List[float]:
        try:
            client = _get_openai_client()
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

    def _embed_openai_many(
        self,
        texts: Sequence[str],
        *,
        timeout: int,
        batch_size: int,
        max_retries: int,
        base_backoff_sec: float,
    ) -> List[List[float]]:
        client = _get_openai_client()
        vectors: List[List[float]] = []

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
                    logger.exception("embed_many bad request: %s", e)
                    raise
                except Exception as e:
                    logger.exception("Unexpected error in embed_many: %s", e)
                    raise
        return vectors


# Export the default instance to match existing imports
# Alias for backward compatibility
OpenAIEmbeddingClient = EmbeddingClient
default_embedding_client = EmbeddingClient()
