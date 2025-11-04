# path: backend/app/services/job_service.py
# Purpose: Business logic for Jobs (validation, rules) on top of repository calls.
# Notes: Keep thin for MVP—add rules here later (e.g., allowed status transitions).
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import job_repo
from app.models.job import Job


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
    db: Session, job: Job, *, title: Optional[str], job_description: Optional[str],
    free_text: Optional[str], icon: Optional[str], status: Optional[str]
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
