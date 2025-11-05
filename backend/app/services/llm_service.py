# app/services/llm_service.py
import json
import requests
from typing import Any, Dict, Tuple
from pathlib import Path
from app.core.config import settings
from app.schemas.job_analysis import JobAnalysis
from app.services.normalizer import normalize_job_analysis

OLLAMA_CHAT_URL = f"{settings.OLLAMA_BASE_URL}/api/chat"
MODEL_NAME = settings.LLM_CHAT_MODEL
SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "job_analysis.prompt.txt"

def _load_system_prompt() -> str:
    return Path(SYSTEM_PROMPT_PATH).read_text(encoding="utf-8")

def _post_chat(messages: list[dict], timeout: int = 120) -> Dict[str, Any]:
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0, "seed": 7, "repeat_penalty": 1.05, "num_ctx": 8192, "num_predict": 2048},
        "keep_alive": "30m",
    }
    resp = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "")
    return json.loads(content)

def _repair_json(text: str) -> Dict[str, Any]:
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(s[start: end + 1])
    return json.loads(s)

def analyze_job_text(*, title: str, description: str, free_text: str | None) -> Tuple[dict, str, int]:
    system_prompt = _load_system_prompt()
    user_prompt = f"Job title:\n{title}\n\nDescription:\n{description}\n\nAdditional notes:\n{free_text or ''}\n\nReturn JSON only."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    try:
        raw = _post_chat(messages)
    except requests.HTTPError as e:
        text = e.response.text if e.response is not None else ""
        raw = _repair_json(text)
    data = JobAnalysis.model_validate(raw).model_dump()
    data = normalize_job_analysis(data)
    data["version"] = settings.ANALYSIS_VERSION
    return data, MODEL_NAME, settings.ANALYSIS_VERSION
