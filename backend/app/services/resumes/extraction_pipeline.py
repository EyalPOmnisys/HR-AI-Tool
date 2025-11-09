# app/services/resumes/extraction_pipeline.py
# -----------------------------------------------------------------------------
# PURPOSE (English-only header)
# Mandatory LLM-based extraction pipeline with a minimal deterministic “safe”
# prepass. This file wires the SAFE extractor with the robust LLM pipeline that
# performs structured extraction, clustering, validation, and normalization.
# The result is version-tagged and persisted. On failures the LLM stage returns
# a conservative safe JSON instead of risky/incorrect content.
# -----------------------------------------------------------------------------
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resume import Resume
from app.repositories import resume_repo
from app.services.resumes.extraction.deterministic import extract_deterministic_safe
from app.services.resumes.extraction.llm_boost import llm_end_to_end_enhance


def extract_structured(db: Session, resume: Resume) -> Resume:
    if not resume.parsed_text:
        return resume

    safe_base = extract_deterministic_safe(resume.parsed_text)
    enriched = llm_end_to_end_enhance(parsed_text=resume.parsed_text, base_json=safe_base)

    enriched.setdefault("meta", {})["extraction_version"] = getattr(settings, "EXTRACTION_VERSION", 2)
    enriched.setdefault("meta", {})["EXPERIENCE_CLUSTERING_VERSION"] = getattr(settings, "EXPERIENCE_CLUSTERING_VERSION", 2)

    resume_repo.attach_extraction(db, resume, extraction_json=enriched)
    return resume
