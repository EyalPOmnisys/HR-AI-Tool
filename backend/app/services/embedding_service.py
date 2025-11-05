# app/services/embedding_service.py
import requests
from typing import List
from app.core.config import settings


OLLAMA_EMBED_URL = f"{settings.OLLAMA_BASE_URL}/api/embeddings"


def get_embedding(text: str) -> List[float]:
    if not text.strip():
        return []

    payload = {
        "model": settings.EMBEDDING_MODEL,
        "prompt": text,
    }

    resp = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("embedding", [])
