# app/services/jobs/embedding_pipeline.py
from __future__ import annotations
import logging
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import Job, EMBED_DIM
from app.repositories import job_chunk_repo, job_embedding_repo
from app.services.common.embedding_client import default_embedding_client

logger = logging.getLogger("jobs.pipeline")


def create_and_embed_chunks(
    db: Session,
    *,
    job: Job,
    chunk_defs: List[Dict[str, Any]],
    embedding_model: str | None = None,
    batch_size: int = 64,
) -> None:
    """
    Full pipeline for chunk-level embeddings:
    1) Remove existing chunks (and associated embeddings via cascade).
    2) Insert new chunks.
    3) Embed all chunk texts in batches.
    4) Insert JobEmbedding rows.
    """
    if chunk_defs is None:
        chunk_defs = []

    # 1) Remove previous
    deleted = job_chunk_repo.delete_by_job_id(db, job.id)
    if deleted:
        logger.info("Removed %d previous chunks for job %s", deleted, str(job.id))

    # 2) Insert new chunk rows
    chunks = job_chunk_repo.bulk_insert(db, job_id=job.id, chunks=chunk_defs)
    if not chunks:
        logger.info("No chunks to embed for job %s", str(job.id))
        return

    texts = [c.text for c in chunks]
    logger.info("Embedding %d chunks for job %s", len(texts), str(job.id))

    # 3) Embed
    model_name = embedding_model or settings.OPENAI_EMBEDDING_MODEL
    vecs = default_embedding_client.embed_many(texts, batch_size=batch_size)
    if not vecs:
        logger.warning("No vectors returned for job %s", str(job.id))
        return

    # Optional safety check against EMBED_DIM
    try:
        if vecs and len(vecs[0]) != EMBED_DIM:
            logger.warning("Vector dim mismatch: expected %d got %d", EMBED_DIM, len(vecs[0]))
    except Exception:
        pass

    # 4) Insert JobEmbedding rows
    chunk_ids: List[UUID] = [c.id for c in chunks]
    job_embedding_repo.bulk_insert_for_chunks(
        db,
        chunk_ids=chunk_ids,
        vectors=vecs,
        embedding_model=model_name,
        embedding_version=1,
    )

    logger.info("Created %d chunk embeddings for job %s", len(chunk_ids), str(job.id))
