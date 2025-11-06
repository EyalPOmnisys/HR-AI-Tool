"""
Shared embedding helper so job and resume flows reuse the same HTTP wrapper.
Keeping this code generic avoids duplicating request logic across domains.
"""
from __future__ import annotations

from typing import List

import requests

from app.core.config import settings


class EmbeddingClient:
    """Tiny wrapper around the Ollama embeddings endpoint."""

    def __init__(self, *, base_url: str, model: str) -> None:
        self._embed_url = f"{base_url.rstrip('/')}/api/embeddings"
        self._model = model

    def embed(self, text: str, *, timeout: int = 60) -> List[float]:
        if not text or not text.strip():
            return []

        payload = {"model": self._model, "prompt": text}
        response = requests.post(self._embed_url, json=payload, timeout=timeout)
        response.raise_for_status()
        body = response.json()
        return body.get("embedding", [])


default_embedding_client = EmbeddingClient(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.EMBEDDING_MODEL,
)

