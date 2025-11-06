"""
Job-centric wrapper around the shared LLM client.
The function below converts raw job text into a normalized structure using the prompt in app/prompts/jobs.
"""
from __future__ import annotations

from typing import Tuple

from app.core.config import settings
from app.schemas.job_analysis import JobAnalysis
from app.services.common.llm_client import default_llm_client, load_prompt
from app.services.jobs.normalizer import normalize_job_analysis


JOB_ANALYSIS_PROMPT = load_prompt("jobs/job_analysis.prompt.txt")


def analyze_job_text(*, title: str, description: str, free_text: str | None) -> Tuple[dict, str, int]:
    user_prompt = (
        f"Job title:\n{title}\n\n"
        f"Description:\n{description}\n\n"
        f"Additional notes:\n{free_text or ''}\n\n"
        "Return JSON only."
    )
    messages = [
        {"role": "system", "content": JOB_ANALYSIS_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    result = default_llm_client.chat_json(messages)
    data = JobAnalysis.model_validate(result.data).model_dump()
    data = normalize_job_analysis(data)
    data["version"] = settings.ANALYSIS_VERSION
    return data, result.model, settings.ANALYSIS_VERSION

