# app/services/common/llm_client.py
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI, APIConnectionError, RateLimitError, BadRequestError
from app.core.config import settings

logger = logging.getLogger("ai.llm")


@dataclass
class _JSONResponse:
    """Small wrapper to match `.data` access pattern used in the codebase."""
    data: Dict[str, Any]


def _require_api_key() -> str:
    """Ensure an API key is configured; raise a clear error otherwise."""
    if not settings.OPENAI_API_KEY:
        # Raising a ValueError here is intentional so callers get a deterministic failure.
        raise ValueError("OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
    return settings.OPENAI_API_KEY


def _build_client() -> OpenAI:
    """Instantiate the OpenAI client once per process."""
    api_key = _require_api_key()
    return OpenAI(api_key=api_key)


# Singleton client
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = _build_client()
        logger.info("OpenAI client initialized")
    return _client


def load_prompt(relative_path: str) -> str:
    """
    Load a prompt file from app/prompts/<relative_path>.
    If the exact relative path is not found, also try by basename under app/prompts/.
    This is generic and helps when prompts are stored either in a flat folder
    (e.g., app/prompts/job_analysis.prompt.txt) or in subfolders (e.g., app/prompts/job/...).
    """
    base = Path(__file__).resolve().parents[2] / "prompts"  # points to app/prompts
    # 1) Try the given relative path
    path = base / relative_path
    if path.exists():
        text = path.read_text(encoding="utf-8")
        logger.debug("Loaded prompt: %s (%d chars)", relative_path, len(text))
        return text
    # 2) Fallback: try by basename directly under app/prompts
    alt = base / Path(relative_path).name
    if alt.exists():
        text = alt.read_text(encoding="utf-8")
        logger.debug("Loaded prompt by basename fallback: %s (%d chars)", alt.name, len(text))
        return text
    # Not found
    raise FileNotFoundError(f"Prompt file not found. Tried: {path} and {alt}")


class LLMClient:
    """
    Thin wrapper around OpenAI Chat Completions to provide:
      - chat_text: freeform text output.
      - chat_json: strict JSON output (.data dict), used by pipelines.
    """

    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.OPENAI_MODEL

    def chat_text(self, messages: List[Dict[str, str]], timeout: int = 60) -> str:
        """Run a chat completion expecting plain text output."""
        try:
            client = _get_client()
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                timeout=timeout,
            )
            content = (resp.choices[0].message.content or "").strip()
            logger.debug("chat_text received %d chars", len(content))
            return content
        except (APIConnectionError, RateLimitError, BadRequestError) as e:
            logger.exception("OpenAI chat_text error: %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error in chat_text: %s", e)
            raise

    def chat_json(self, messages: List[Dict[str, str]], timeout: int = 90) -> _JSONResponse:
        """
        Run a chat completion that MUST return valid JSON.
        Uses `response_format={"type":"json_object"}` and parses the output.
        """
        try:
            client = _get_client()
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                timeout=timeout,
            )
            raw = (resp.choices[0].message.content or "").strip()
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError as je:
                logger.error("JSON decode failed; returning error payload")
                data = {"__llm_error__": f"json_decode_error: {je}", "__raw__": raw}
            logger.debug("chat_json parsed keys: %s", list(data.keys()))
            return _JSONResponse(data=data)
        except (APIConnectionError, RateLimitError, BadRequestError) as e:
            logger.exception("OpenAI chat_json error: %s", e)
            return _JSONResponse(data={"__llm_error__": str(e)})
        except Exception as e:
            logger.exception("Unexpected error in chat_json: %s", e)
            return _JSONResponse(data={"__llm_error__": str(e)})


# Export a default instance so existing imports keep working
default_llm_client = LLMClient()
