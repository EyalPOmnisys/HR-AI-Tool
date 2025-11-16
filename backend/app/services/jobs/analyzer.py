# app/services/jobs/analyzer.py
"""
Job Analysis Service - Uses LLM to extract structured data from raw job postings.
Loads prompts, validates against schema, and returns normalized job information.
"""
from __future__ import annotations
from typing import Tuple

from app.core.config import settings
from app.schemas.job_analysis import JobAnalysis
from app.services.common.openai_service import run_json_completion
from app.services.jobs.normalizer import normalize_job_analysis


from app.services.common.llm_client import load_prompt
JOB_ANALYSIS_PROMPT = load_prompt("jobs/job_analysis.prompt.txt")


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

    raw = run_json_completion(user_prompt, model=settings.OPENAI_MODEL)

    # Validate against our pydantic schema, then normalize with our strict post-processor
    data = JobAnalysis.model_validate(raw).model_dump()
    data = normalize_job_analysis(data)
    data["version"] = settings.ANALYSIS_VERSION

    return data, settings.OPENAI_MODEL, settings.ANALYSIS_VERSION
