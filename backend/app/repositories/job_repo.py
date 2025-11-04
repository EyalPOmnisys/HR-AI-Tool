# path: backend/app/repositories/job_repo.py
# Purpose: Data-access only (CRUD) for Job. No business rules here.
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.job import Job


def create(db: Session, *, title: str, job_description: str, free_text: Optional[str], icon: Optional[str], status: str) -> Job:
    job = Job(
        title=title,
        job_description=job_description,
        free_text=free_text,
        icon=icon,
        status=status or "draft",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get(db: Session, job_id: UUID) -> Optional[Job]:
    return db.get(Job, job_id)


def list_paginated(db: Session, *, offset: int = 0, limit: int = 20) -> Tuple[list[Job], int]:
    total = db.execute(select(func.count()).select_from(Job)).scalar_one()
    rows = db.execute(
        select(Job).order_by(Job.created_at.desc()).offset(offset).limit(limit)
    ).scalars().all()
    return rows, total


def update(db: Session, job: Job, **fields) -> Job:
    for k, v in fields.items():
        if v is not None:
            setattr(job, k, v)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def delete(db: Session, job: Job) -> None:
    db.delete(job)
    db.commit()
