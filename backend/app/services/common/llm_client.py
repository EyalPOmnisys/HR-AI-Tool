# app/services/common/llm_client.py
"""Unified LLM client supporting both Ollama and OpenAI: handles text and structured JSON responses,
prompt loading, and provider abstraction for all AI-powered extraction and analysis."""
from __future__ import annotations
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from app.core.config import settings

try:
    from openai import OpenAI, APIConnectionError, RateLimitError, BadRequestError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger("ai.llm")


@dataclass
class _JSONResponse:
    """Small wrapper to match `.data` access pattern used in the codebase."""
    data: Dict[str, Any]


# Default Ollama chat options
DEFAULT_CHAT_OPTIONS: Dict[str, Any] = {
    "temperature": 0,
    "seed": 7,
    "repeat_penalty": 1.05,
    "num_ctx": 8192,
    "num_predict": 2048,
}


def _require_api_key() -> str:
    """Ensure an API key is configured; raise a clear error otherwise."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
    return settings.OPENAI_API_KEY


def _build_openai_client() -> "OpenAI":
    """Instantiate the OpenAI client once per process."""
    if not OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI library is not installed")
    api_key = _require_api_key()
    return OpenAI(api_key=api_key)


# Singleton OpenAI client
_openai_client: Optional["OpenAI"] = None


def _get_openai_client() -> "OpenAI":
    global _openai_client
    if _openai_client is None:
        _openai_client = _build_openai_client()
        logger.info("OpenAI client initialized")
    return _openai_client


def _build_ollama_chat_url() -> str:
    """Build the Ollama chat endpoint URL."""
    if not settings.OLLAMA_BASE_URL:
        raise ValueError("OLLAMA_BASE_URL is not set. Please add it to your environment or .env file.")
    return f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"


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
    Unified wrapper supporting both Ollama and OpenAI:
      - chat_text: freeform text output.
      - chat_json: strict JSON output (.data dict), used by pipelines.
    
    Provider selection:
      - If LLM_CHAT_MODEL is set → use Ollama
      - If OPENAI_MODEL is set and LLM_CHAT_MODEL is not → use OpenAI
    """

    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None):
        # Determine provider
        if provider:
            self.provider = provider.lower()
        elif settings.LLM_CHAT_MODEL:
            self.provider = "ollama"
        elif settings.OPENAI_MODEL:
            self.provider = "openai"
        else:
            # Default to Ollama if nothing is set, assuming local setup
            self.provider = "ollama"
            logger.warning("No LLM provider configured explicitly. Defaulting to Ollama.")
        
        # Set model based on provider
        if self.provider == "ollama":
            self.model = model or settings.LLM_CHAT_MODEL or "llama3.2"
            self.chat_url = _build_ollama_chat_url()
            self.default_options = DEFAULT_CHAT_OPTIONS.copy()
            logger.info(f"🤖 LLM Client initialized with Ollama: {self.model} @ {settings.OLLAMA_BASE_URL}")
        elif self.provider == "openai":
            self.model = model or settings.OPENAI_MODEL
            logger.info(f"🤖 LLM Client initialized with OpenAI: {self.model}")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def chat_text(
        self,
        messages: List[Dict[str, str]],
        timeout: int = 60,
        *,
        options: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Run a chat completion expecting plain text output."""
        if self.provider == "ollama":
            return self._chat_text_ollama(messages, timeout, options=options)
        else:
            return self._chat_text_openai(messages, timeout, max_tokens=max_tokens)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        timeout: int = 90,
        *,
        options: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
    ) -> _JSONResponse:
        """
        Run a chat completion that MUST return valid JSON.
        """
        if self.provider == "ollama":
            return self._chat_json_ollama(messages, timeout, options=options)
        else:
            return self._chat_json_openai(messages, timeout, max_tokens=max_tokens)

    # ===== Ollama Implementation =====
    def _chat_text_ollama(self, messages: List[Dict[str, str]], timeout: int, *, options: Optional[Dict[str, Any]] = None) -> str:
        try:
            merged_options = self.default_options.copy()
            if options:
                merged_options.update(options)
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": merged_options,
                "keep_alive": "30m",
            }
            response = requests.post(self.chat_url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            content = response.json().get("message", {}).get("content", "").strip()
            logger.debug("🤖 Ollama chat_text received %d chars", len(content))
            return content
        except requests.RequestException as e:
            logger.exception("Ollama chat_text error: %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error in Ollama chat_text: %s", e)
            raise

    def _chat_json_ollama(self, messages: List[Dict[str, str]], timeout: int, *, options: Optional[Dict[str, Any]] = None) -> _JSONResponse:
        try:
            merged_options = self.default_options.copy()
            if options:
                merged_options.update(options)
            payload = {
                "model": self.model,
                "messages": messages,
                "format": "json",
                "stream": False,
                "options": merged_options,
                "keep_alive": "30m",
            }
            response = requests.post(self.chat_url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            raw = response.json().get("message", {}).get("content", "").strip()
            try:
                data = self._coerce_json(raw) if raw else {}
            except json.JSONDecodeError as je:
                preview = (raw or "")[:1200]
                logger.error("JSON decode failed; returning error payload")
                data = {"__llm_error__": f"json_decode_error: {je}", "__raw__": raw, "__raw_preview__": preview}
            
            logger.debug("🤖 Ollama chat_json parsed keys: %s", list(data.keys()))
            return _JSONResponse(data=data)
        except requests.RequestException as e:
            logger.exception("Ollama chat_json error: %s", e)
            return _JSONResponse(data={"__llm_error__": str(e)})
        except Exception as e:
            logger.exception("Unexpected error in Ollama chat_json: %s", e)
            return _JSONResponse(data={"__llm_error__": str(e)})

    # ===== OpenAI Implementation =====
    def _chat_text_openai(self, messages: List[Dict[str, str]], timeout: int, *, max_tokens: Optional[int] = None) -> str:
        try:
            client = _get_openai_client()
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "timeout": timeout,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            resp = client.chat.completions.create(**kwargs)
            content = (resp.choices[0].message.content or "").strip()
            logger.debug("OpenAI chat_text received %d chars", len(content))
            return content
        except (APIConnectionError, RateLimitError, BadRequestError) as e:
            logger.exception("OpenAI API error in chat_text: %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error in OpenAI chat_text: %s", e)
            raise

    def _chat_json_openai(self, messages: List[Dict[str, str]], timeout: int, *, max_tokens: Optional[int] = None) -> _JSONResponse:
        try:
            client = _get_openai_client()
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "timeout": timeout,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            resp = client.chat.completions.create(**kwargs)
            raw = (resp.choices[0].message.content or "").strip()
            try:
                data = self._coerce_json(raw) if raw else {}
            except json.JSONDecodeError as je:
                preview = (raw or "")[:1200]
                logger.error("JSON decode failed; returning error payload")
                data = {"__llm_error__": f"json_decode_error: {je}", "__raw__": raw, "__raw_preview__": preview}
            logger.debug("OpenAI chat_json parsed keys: %s", list(data.keys()))
            return _JSONResponse(data=data)
        except (APIConnectionError, RateLimitError, BadRequestError) as e:
            logger.exception("OpenAI API error in chat_json: %s", e)
            return _JSONResponse(data={"__llm_error__": str(e)})
        except Exception as e:
            logger.exception("Unexpected error in OpenAI chat_json: %s", e)
            return _JSONResponse(data={"__llm_error__": str(e)})

    @staticmethod
    def _coerce_json(text: str) -> Dict[str, Any]:
        """Best-effort JSON object parser for LLM responses.

        Handles common failure modes:
        - Markdown code fences (```json ... ```)
        - Extra commentary before/after JSON
        - JSON embedded inside a larger string
        """

        def strip_code_fences(s: str) -> str:
            # Remove leading/trailing ``` / ```json fences if present.
            s = s.strip()
            s = re.sub(r"^\s*```(?:json)?\s*", "", s, flags=re.IGNORECASE)
            s = re.sub(r"\s*```\s*$", "", s)
            return s.strip()

        def extract_first_json_object(s: str) -> Optional[str]:
            # Find the first balanced {...} object. This avoids grabbing too much
            # when the response contains additional braces later.
            start = s.find("{")
            if start == -1:
                return None
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(s)):
                ch = s[i]
                if in_string:
                    if escape:
                        escape = False
                        continue
                    if ch == "\\":
                        escape = True
                        continue
                    if ch == '"':
                        in_string = False
                    continue
                else:
                    if ch == '"':
                        in_string = True
                        continue
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            return s[start : i + 1]
            return None

        stripped = strip_code_fences(text or "")
        if not stripped:
            return {}

        # Fast path: already valid JSON object.
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                return obj
            # Sometimes a model returns a single-element list with a dict.
            if isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict):
                return obj[0]
        except json.JSONDecodeError:
            pass

        # Attempt to extract the first embedded JSON object.
        candidate = extract_first_json_object(stripped)
        if candidate:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
            if isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict):
                return obj[0]

        # Last resort: let json raise a useful error.
        obj = json.loads(stripped)
        if not isinstance(obj, dict):
            raise json.JSONDecodeError("Expected JSON object", stripped, 0)
        return obj


# Export a default instance so existing imports keep working
default_llm_client = LLMClient()
