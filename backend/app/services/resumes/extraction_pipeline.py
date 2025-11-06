"""Pipeline for structured field extraction (deterministic + LLM enhancement)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resume import Resume
from app.repositories import resume_repo
from app.services.resumes.extraction.deterministic import extract_deterministic
from app.services.resumes.extraction.llm_boost import llm_enhance


def extract_structured(db: Session, resume: Resume) -> Resume:
    """
    Run deterministic and optional LLM-based extraction.
    LLM runs only when needed (missing name/education/experience).
    """
    if not resume.parsed_text:
        return resume

    base = extract_deterministic(resume.parsed_text)
    enriched = llm_enhance(resume.parsed_text, base)
    enriched.setdefault("meta", {})["extraction_version"] = getattr(
        settings, "EXTRACTION_VERSION", 1
    )

    resume_repo.attach_extraction(db, resume, extraction_json=enriched)
    return resume
