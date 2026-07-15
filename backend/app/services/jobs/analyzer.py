# app/services/jobs/analyzer.py
"""Job Analysis Service: uses LLM to extract structured data (skills, tech stack, requirements)
from raw job postings, validates against schema, and returns normalized JSON."""
from __future__ import annotations
import logging
from typing import Tuple

from app.core.config import settings
from app.schemas.job_analysis import JobAnalysis
from app.services.jobs.normalizer import normalize_job_analysis
from app.services.common.llm_client import load_prompt, default_llm_client

logger = logging.getLogger("jobs.analyzer")

JOB_ANALYSIS_PROMPT = load_prompt("jobs/job_analysis.prompt.txt")


def _sanitize_result(result: dict) -> dict:
    """
    Cleans up common hallucinations from SLMs.
    Smartly filters short terms based on a multi-disciplinary allow-list.
    """
    if not result:
        return result

    # Valid short terms from all departments (Dev, Admin, Engineering, Marketing)
    VALID_SHORT_TERMS = {
        # Development & Algo
        'c', 'r', 'go', 'js', 'ts', 'ai', 'ml', 'dl', 'os',
        # QA & System
        'qa', 'qc', 'std',
        # Design & Product
        'ui', 'ux', 'cx', 'pm',
        # HR & Admin & Finance
        'hr', 'cv', 'od', 'cpa', 'mba', 'pmo',
        # Marketing
        'pr', 'seo', 'sem', 'ppc'
    }

    def clean_list(items):
        if not items: 
            return []
        cleaned = []
        for item in items:
            if not isinstance(item, str):
                continue
            
            s_clean = item.strip()
            if not s_clean:
                continue

            # Filter logic:
            # 1. Remove if it's a generic stopword (hallucination common in small models)
            if s_clean.lower() in ['and', 'or', 'the', 'etc', 'skills', 'knowledge', 'tools']:
                continue

            # 2. Handle short terms (1-2 chars)
            # If it's short AND NOT in our valid list -> Skip it (It's likely noise like "f", "x")
            if len(s_clean) < 3 and s_clean.lower() not in VALID_SHORT_TERMS:
                continue

            cleaned.append(s_clean)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(cleaned))

    # 1. Clean Skills
    if "skills" in result:
        for key in ["must_have", "nice_to_have"]:
            if key in result["skills"]:
                result["skills"][key] = clean_list(result["skills"][key])

    # 2. Clean Tech Stack / Tools
    if "tech_stack" in result and isinstance(result["tech_stack"], dict):
        for category, items in result["tech_stack"].items():
            if isinstance(items, list):
                result["tech_stack"][category] = clean_list(items)
    
    return result


def analyze_job_text(*, title: str, description: str, free_text: str | None) -> Tuple[dict, str, int]:
    """
    Run the LLM with the job analysis prompt and return validated/normalized JSON.
    """
    # The true source text: used both as the prompt input and as the reference
    # the normalizer verifies extracted skills against (anti-hallucination).
    source_text = (
        f"Job title:\n{title}\n\n"
        f"Description:\n{description}\n\n"
        f"Additional notes:\n{free_text or ''}"
    )

    # Fill the {{text}} placeholder the prompt file ends with; fall back to
    # appending if the placeholder is ever removed from the prompt.
    if "{{text}}" in JOB_ANALYSIS_PROMPT:
        user_prompt = JOB_ANALYSIS_PROMPT.replace("{{text}}", source_text) + "\n\nReturn JSON only."
    else:
        user_prompt = f"{JOB_ANALYSIS_PROMPT}\n\n{source_text}\n\nReturn JSON only."

    # Use LLM client (Ollama or OpenAI based on config).
    # The model occasionally returns a near-empty JSON (valid schema, no content);
    # Pydantic happily fills defaults and the junk gets stored. Retry with a
    # sanity check instead of accepting the first syntactically-valid response.
    messages = [{"role": "user", "content": user_prompt}]
    max_attempts = 3
    data = None
    for attempt in range(1, max_attempts + 1):
        resp = default_llm_client.chat_json(messages, timeout=120)
        raw = resp.data
        if raw.get("__llm_error__"):
            logger.warning("Job analysis attempt %d/%d: LLM error payload: %s", attempt, max_attempts, raw.get("__llm_error__"))
            continue

        candidate = JobAnalysis.model_validate(raw).model_dump()
        skills = candidate.get("skills") or {}
        has_content = bool(
            candidate.get("role_title")
            or skills.get("must_have")
            or skills.get("nice_to_have")
            or candidate.get("responsibilities")
            or candidate.get("requirements")
        )
        if has_content:
            data = candidate
            break
        logger.warning("Job analysis attempt %d/%d returned an empty analysis; retrying", attempt, max_attempts)

    if data is None:
        raise ValueError(f"Job analysis produced no usable content after {max_attempts} attempts")

    # Validate against our pydantic schema, then normalize with our strict post-processor.
    # Passing source_text makes the normalizer verify skills against the REAL job text
    # instead of the model's own (possibly hallucinated) summary/requirements.
    data = _sanitize_result(data)
    data = normalize_job_analysis(data, source_text=source_text)
    data["version"] = settings.ANALYSIS_VERSION

    # Return the model name from the client
    model_name = default_llm_client.model
    return data, model_name, settings.ANALYSIS_VERSION
