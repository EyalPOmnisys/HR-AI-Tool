"""High-level Job service: CRUD plus AI enrichment (analysis, normalization)
coordinating submodules into a single pipeline."""
from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from app.models.job import Job
from app.repositories import job_repo
from app.services.jobs.analyzer import analyze_job_text
from app.services.common.text_normalizer import normalize_text_for_fts, approx_token_count

logger = logging.getLogger("jobs.service")

def create_job(
    db: Session,
    *,
    title: str,
    job_description: str,
    free_text: Optional[str],
    icon: Optional[str],
    status: Optional[str],
) -> Job:
    status_final = status or "draft"
    return job_repo.create(
        db,
        title=title.strip(),
        job_description=job_description.strip(),
        free_text=(free_text.strip() if free_text else None),
        icon=(icon.strip() if icon else None),
        status=status_final,
    )

def get_job(db: Session, job_id: UUID) -> Optional[Job]:
    return job_repo.get(db, job_id)

def list_jobs(db: Session, *, offset: int = 0, limit: int = 20) -> Tuple[list[Job], int]:
    return job_repo.list_paginated(db, offset=offset, limit=limit)

def update_job(
    db: Session,
    job: Job,
    *,
    title: Optional[str],
    job_description: Optional[str],
    free_text: Optional[str],
    icon: Optional[str],
    status: Optional[str],
) -> Job:
    fields = dict(
        title=title.strip() if title else None,
        job_description=job_description.strip() if job_description else None,
        free_text=free_text.strip() if free_text else None,
        icon=icon.strip() if icon else None,
        status=status,
    )
    return job_repo.update(db, job, **fields)

def delete_job(db: Session, job: Job) -> None:
    job_repo.delete(db, job)

def analyze_and_attach_job(db: Session, job_id: UUID) -> Optional[Job]:
    job = job_repo.get(db, job_id)
    if not job:
        return None

    job.ai_started_at = datetime.now(timezone.utc)
    job.ai_error = None
    db.add(job)
    db.commit()

    try:
        logger.info("Analyze job '%s' [%s]", job.title, job.id)

        # Preserve existing additional_skills before AI analysis
        existing_additional_skills = None
        if job.analysis_json and isinstance(job.analysis_json, dict):
            existing_additional_skills = job.analysis_json.get('additional_skills')

        analysis_json, model_name, version = analyze_job_text(
            title=job.title,
            description=job.job_description,
            free_text=job.free_text,
        )
        
        # Restore additional_skills after AI analysis
        if existing_additional_skills is not None:
            analysis_json['additional_skills'] = existing_additional_skills
        
        job.analysis_json = analysis_json
        job.analysis_model = model_name
        job.analysis_version = version

        summary = (analysis_json.get("summary") or "").strip()
        normalized = normalize_text_for_fts(job.title, summary, job.job_description, job.free_text or "")
        job.normalized_text = normalized
        job.tokens = approx_token_count(normalized)

        job.ai_finished_at = datetime.now(timezone.utc)
        job.ai_error = None
        logger.info("Job '%s' enrichment completed", job.title)

    except Exception as exc:
        job.ai_finished_at = datetime.now(timezone.utc)
        job.ai_error = str(exc)
        logger.exception("Failed to enrich job '%s': %s", job.title, exc)

    db.add(job)
    db.commit()
    db.refresh(job)
    return job
