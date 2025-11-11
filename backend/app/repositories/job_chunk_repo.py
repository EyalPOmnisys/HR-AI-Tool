# app/repositories/job_chunk_repo.py
from __future__ import annotations
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.job import JobChunk


def delete_by_job_id(db: Session, job_id: UUID) -> int:
    """
    Delete all chunks for a given job. Returns number of rows deleted.
    Note: JobEmbedding rows are removed automatically via ON DELETE CASCADE.
    """
    res = db.execute(delete(JobChunk).where(JobChunk.job_id == job_id))
    return res.rowcount or 0


def bulk_insert(
    db: Session,
    *,
    job_id: UUID,
    chunks: List[dict],
) -> List[JobChunk]:
    """
    Insert many chunk rows for a job in a single transaction.
    Expects each dict to contain: section, ord, text, lang.
    """
    objs = [
        JobChunk(job_id=job_id, section=c.get("section"), ord=c.get("ord", 0), text=c["text"], lang=c.get("lang"))
        for c in chunks
        if c.get("text")
    ]
    if not objs:
        return []
    db.add_all(objs)
    db.commit()
    # Refresh ids
    for obj in objs:
        db.refresh(obj)
    return objs


def list_by_job_id(db: Session, job_id: UUID) -> List[JobChunk]:
    return db.execute(select(JobChunk).where(JobChunk.job_id == job_id).order_by(JobChunk.ord.asc())).scalars().all()
