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
    Cleans up common hallucinations from SLMs (Small Language Models).
    Removes single-letter skills, empty strings, and fixes tech_stack structure.
    """
    if not result:
        return result

    # 1. Clean Skills (Remove "r", "c", "f" etc.)
    if "skills" in result:
        for key in ["must_have", "nice_to_have"]:
            if key in result["skills"]:
                valid_skills = []
                for skill in result["skills"][key]:
                    # Keep if length > 1 OR it is explicitly 'C' or 'R'
                    if len(skill) > 1 or skill in ['C', 'R']: 
                        valid_skills.append(skill)
                result["skills"][key] = valid_skills

    # 2. Clean Tech Stack
    if "tech_stack" in result and isinstance(result["tech_stack"], dict):
        for category, items in result["tech_stack"].items():
            if isinstance(items, list):
                # Remove empty strings and single letters (except C/R)
                result["tech_stack"][category] = [
                    i for i in items 
                    if isinstance(i, str) and (len(i) > 1 or i in ['C', 'R'])
                ]
    
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
