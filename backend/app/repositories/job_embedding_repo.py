# app/repositories/job_embedding_repo.py
from __future__ import annotations
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.job import JobEmbedding


def bulk_insert_for_chunks(
    db: Session,
    *,
    chunk_ids: List[UUID],
    vectors: List[List[float]],
    embedding_model: str,
    embedding_version: int = 1,
) -> List[JobEmbedding]:
    """
    Create JobEmbedding rows for each chunk_id. Length of vectors must match chunk_ids.
    """
    if not chunk_ids:
        return []
    assert len(chunk_ids) == len(vectors), "chunk_ids and vectors length mismatch"

    rows: List[JobEmbedding] = []
    for cid, vec in zip(chunk_ids, vectors):
        rows.append(
            JobEmbedding(
                chunk_id=cid,
                embedding=vec,
                embedding_model=embedding_model,
                embedding_version=embedding_version,
            )
        )
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows
