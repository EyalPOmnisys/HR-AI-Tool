"""
Job-centric wrapper around OpenAI client.
Converts raw job text into a normalized structure using the prompt in app/prompts/jobs.
"""
from __future__ import annotations

from typing import Tuple

from app.core.config import settings
from app.schemas.job_analysis import JobAnalysis
from app.services.common.openai_service import run_json_completion
from app.services.common.llm_client import load_prompt  # keep using the same loader for file-based prompts
from app.services.jobs.normalizer import normalize_job_analysis


JOB_ANALYSIS_PROMPT = load_prompt("jobs/job_analysis.prompt.txt")


def analyze_job_text(*, title: str, description: str, free_text: str | None) -> Tuple[dict, str, int]:
    """
    Uses OpenAI (chat/completions) to produce a structured job analysis JSON.
    Returns: (data, model_name, version)
    """
    # We inline the system prompt content + explicit "Return JSON only" contract.
    user_prompt = (
        f"{JOB_ANALYSIS_PROMPT}\n\n"
        f"Job title:\n{title}\n\n"
        f"Description:\n{description}\n\n"
        f"Additional notes:\n{free_text or ''}\n\n"
        "Return JSON only."
    )

    # Ask OpenAI to return JSON and parse it
    raw = run_json_completion(user_prompt, model=settings.OPENAI_MODEL)

    # Validate & normalize
    data = JobAnalysis.model_validate(raw).model_dump()
    data = normalize_job_analysis(data)
    data["version"] = settings.ANALYSIS_VERSION

    model_name = settings.OPENAI_MODEL
    return data, model_name, settings.ANALYSIS_VERSION
