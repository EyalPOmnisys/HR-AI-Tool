# app/services/jobs/analyzer.py
"""Job Analysis Service: uses LLM to extract structured data (skills, tech stack, requirements)
from raw job postings, validates against schema, and returns normalized JSON."""
from __future__ import annotations
from typing import Tuple

from app.core.config import settings
from app.schemas.job_analysis import JobAnalysis
from app.services.jobs.normalizer import normalize_job_analysis
from app.services.common.llm_client import load_prompt, default_llm_client
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
    # Build user prompt with job data
    user_prompt = (
        f"{JOB_ANALYSIS_PROMPT}\n\n"
        f"Job title:\n{title}\n\n"
        f"Description:\n{description}\n\n"
        f"Additional notes:\n{free_text or ''}\n\n"
        "Return JSON only."
    )

    # Use LLM client (Ollama or OpenAI based on config)
    messages = [{"role": "user", "content": user_prompt}]
    resp = default_llm_client.chat_json(messages, timeout=120)
    raw = resp.data

    # Validate against our pydantic schema, then normalize with our strict post-processor
    data = JobAnalysis.model_validate(raw).model_dump()
    data = _sanitize_result(data)
    data = normalize_job_analysis(data)
    data["version"] = settings.ANALYSIS_VERSION

    # Return the model name from the client
    model_name = default_llm_client.model
    return data, model_name, settings.ANALYSIS_VERSION
