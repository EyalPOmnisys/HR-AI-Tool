"""
Centralized LLM client utilities shared by both the job and resume flows.
Keeping the HTTP logic in one place means future changes to the model or payload
shape will automatically propagate everywhere that consumes this client.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import requests

from app.core.config import settings


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

DEFAULT_CHAT_OPTIONS: Dict[str, Any] = {
    "temperature": 0,
    "seed": 7,
    "repeat_penalty": 1.05,
    "num_ctx": 8192,
    "num_predict": 2048,
}


@dataclass(slots=True)
class ChatResult:
    """Lightweight container for the parsed JSON content and model metadata."""

    data: Dict[str, Any]
    model: str


class LLMClient:
    """Typed wrapper around the Ollama chat endpoint for JSON-style prompts."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        default_options: Mapping[str, Any] | None = None,
    ) -> None:
        self._chat_url = f"{base_url.rstrip('/')}/api/chat"
        self._model = model
        self._default_options = dict(default_options or DEFAULT_CHAT_OPTIONS)

    def chat_json(
        self,
        messages: Iterable[Dict[str, Any]],
        *,
        timeout: int = 120,
        options: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        payload = {
            "model": self._model,
            "messages": list(messages),
            "format": "json",
            "stream": False,
            "options": self._merge_options(options),
            "keep_alive": "30m",
        }
        response = requests.post(self._chat_url, json=payload, timeout=timeout)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - delegates to coercion
            content = (exc.response.text if exc.response is not None else "").strip()
            return ChatResult(data=self._coerce_json(content), model=self._model)

        raw_content = response.json().get("message", {}).get("content", "")
        return ChatResult(data=self._coerce_json(raw_content), model=self._model)

    def _merge_options(self, options: Mapping[str, Any] | None) -> Dict[str, Any]:
        merged = dict(self._default_options)
        if options:
            merged.update(options)
        return merged

    @staticmethod
    def _coerce_json(text: str) -> Dict[str, Any]:
        """Attempt to repair common failures when the LLM returns markdown-wrapped JSON."""
        stripped = text.strip()
        if not stripped:
            return {}
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        return json.loads(stripped)


def load_prompt(relative_path: str) -> str:
    """
    Read a prompt file from the shared prompts directory.
    The helper uses UTF-8 so prompt authors can include multilingual guidance safely.
    """
    path = PROMPTS_DIR / relative_path
    return path.read_text(encoding="utf-8")


default_llm_client = LLMClient(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.LLM_CHAT_MODEL,
)

