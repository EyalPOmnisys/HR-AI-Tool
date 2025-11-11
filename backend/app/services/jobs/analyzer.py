# app/services/jobs/analyzer.py
"""
Job-centric wrapper around the LLM client.
Builds a *strict* extraction prompt and converts raw job text into a normalized structure.
The emphasis here is on **precision**: extract only facts explicitly present in the input.
"""
from __future__ import annotations
from typing import Tuple

from app.core.config import settings
from app.schemas.job_analysis import JobAnalysis
from app.services.common.openai_service import run_json_completion
from app.services.jobs.normalizer import normalize_job_analysis


# IMPORTANT:
# We still load the base prompt from disk to keep flexibility,
# but we *prepend* a short "strict extraction" guardrail to reduce hallucinations.
from app.services.common.llm_client import load_prompt
JOB_ANALYSIS_PROMPT = load_prompt("jobs/job_analysis.prompt.txt")


STRICT_GUARDRAILS = """
You are a precise HR extraction assistant.

Core rules (must follow exactly):
- Extract **only factual information explicitly written** in the given text (title/description/notes).
- Never infer, assume, generalize, or add content that is not explicitly present.
- Keep the wording as-is when possible; short paraphrases only if quoting is impossible.
- Separate **requirements** (must/advantage) from **responsibilities** (what the role will do).
- Technologies must come only from the text. Do not add technologies that are not mentioned.
- If a field is not present in the text, leave it empty or null (do not guess).
- Return **valid JSON** only.
""".strip()


def analyze_job_text(*, title: str, description: str, free_text: str | None) -> Tuple[dict, str, int]:
    """
    Run the LLM once with strict guardrails and return validated/normalized JSON.
    """
    # Build user prompt with strict preamble + project prompt
    user_prompt = (
        f"{STRICT_GUARDRAILS}\n\n"
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
