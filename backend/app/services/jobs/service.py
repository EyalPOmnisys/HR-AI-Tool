"""Job service orchestrating CRUD and AI enrichment for job postings."""
from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.job import Job
from app.repositories import job_repo
from app.services.common.embedding_client import default_embedding_client
from app.services.jobs.analyzer import analyze_job_text


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
    # Orchestrates the full AI enrichment flow so API handlers can stay thin.
    job = job_repo.get(db, job_id)
    if not job:
        return None

    job.ai_started_at = datetime.now(timezone.utc)
    job.ai_error = None
    db.add(job)
    db.commit()

    try:
        analysis_json, model_name, version = analyze_job_text(
            title=job.title,
            description=job.job_description,
            free_text=job.free_text,
        )
        job.analysis_json = analysis_json
        job.analysis_model = model_name
        job.analysis_version = version

        combined_text = " ".join(filter(None, [job.title, job.job_description, job.free_text]))
        embedding = default_embedding_client.embed(combined_text)
        job.embedding = embedding

        print(f"[Embedding] Created embedding for job '{job.title}' (length {len(embedding)})")

        job.ai_finished_at = datetime.now(timezone.utc)
        job.ai_error = None

    except Exception as exc:
        job.ai_finished_at = datetime.now(timezone.utc)
        job.ai_error = str(exc)
        print(f"[Embedding] Failed to create embedding for job '{job.title}': {exc}")

    db.add(job)
    db.commit()
    db.refresh(job)
    return job
