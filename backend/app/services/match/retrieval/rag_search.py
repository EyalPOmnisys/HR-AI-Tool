# Vector-based candidate search using pgvector for semantic similarity.
# Fast filtering stage that returns candidates for detailed scoring.

from __future__ import annotations
import logging
import numpy as np
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobChunk, Resume, ResumeChunk

logger = logging.getLogger("match.rag")


def cosine_similarity(vec1: np.ndarray | list, vec2: np.ndarray | list) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector (numpy array or list)
        vec2: Second vector (numpy array or list)
        
    Returns:
        Similarity score between 0 and 1
    """
    # Convert to numpy arrays if needed
    v1 = np.array(vec1) if not isinstance(vec1, np.ndarray) else vec1
    v2 = np.array(vec2) if not isinstance(vec2, np.ndarray) else vec2
    
    # Calculate cosine similarity
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    
    similarity = dot_product / (norm_v1 * norm_v2)
    
    # Clamp to [0, 1] range (handle floating point errors)
    return float(max(0.0, min(1.0, similarity)))


async def get_job_embedding(session: AsyncSession, job: Job) -> Optional[np.ndarray]:
    """
    Get job embedding vector for matching.
    
    Priority:
    1. Use job's primary embedding_vector_768 if available
    2. Calculate average of all job chunk embeddings
    
    Args:
        session: Database session
        job: Job object
        
    Returns:
        Job embedding vector or None if unavailable
    """
    # Option 1: Use job's primary embedding
    if hasattr(job, 'embedding_vector_768'):
        embedding = job.embedding_vector_768
        if embedding is not None:
            try:
                # For numpy arrays, check size
                if hasattr(embedding, 'size') and embedding.size > 0:
                    logger.info("Using job primary embedding (768d)")
                    return embedding
                # For lists, check length
                elif isinstance(embedding, (list, tuple)) and len(embedding) > 0:
                    logger.info("Using job primary embedding (768d)")
                    return np.array(embedding)
            except Exception as e:
                logger.warning(f"Error accessing job primary embedding: {e}")
    
    # Option 2: Average of job chunk embeddings
    job_chunks: List[JobChunk] = (await session.execute(
        select(JobChunk)
        .where(JobChunk.job_id == job.id)
        .options(selectinload(JobChunk.embedding_row))
    )).scalars().all()
    
    embeddings = []
    for chunk in job_chunks:
        embrow = getattr(chunk, "embedding_row", None)
        if embrow and embrow.embedding is not None:
            embeddings.append(embrow.embedding)
    
    if len(embeddings) == 0:
        logger.warning("No embeddings found for job chunks")
        return None
    
    avg_embedding = np.mean(embeddings, axis=0)
    logger.info("Using average of %d job chunk embeddings", len(embeddings))
    return avg_embedding


async def vector_search_candidates(
    session: AsyncSession,
    job_embedding: np.ndarray,
    limit: Optional[int] = None,
    min_threshold: Optional[float] = None
) -> List[dict]:
    """
    Fast vector search to find candidate resumes using pgvector.
    
    Args:
        session: Database session
        job_embedding: Job embedding vector
        limit: Maximum number of candidates to return (None = all)
        min_threshold: Minimum cosine similarity threshold (None = no threshold)
        
    Returns:
        List of dicts with resume_id, avg_similarity, chunk_count
    """
    # Build query with optional threshold and limit
    where_clause = ""
    if min_threshold is not None:
        where_clause = "WHERE avg_similarity >= :min_threshold"
    
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT :limit"
    
    sql = text(f"""
        WITH resume_scores AS (
            SELECT 
                rc.resume_id,
                AVG(1 - (re.embedding <=> CAST(:job_vec AS vector))) as avg_similarity,
                COUNT(*) as chunk_count
            FROM resume_embeddings re
            JOIN resume_chunks rc ON rc.id = re.chunk_id
            WHERE re.embedding IS NOT NULL
            GROUP BY rc.resume_id
        )
        SELECT 
            resume_id,
            avg_similarity,
            chunk_count
        FROM resume_scores
        {where_clause}
        ORDER BY avg_similarity DESC
        {limit_clause}
    """)
    
    job_vec_str = str(job_embedding.tolist() if hasattr(job_embedding, 'tolist') else job_embedding)
    
    params = {"job_vec": job_vec_str}
    if min_threshold is not None:
        params["min_threshold"] = min_threshold
    if limit is not None:
        params["limit"] = limit
    
    results = (await session.execute(sql, params)).mappings().all()
    
    threshold_info = f"threshold={min_threshold:.3f}" if min_threshold else "no threshold"
    logger.info(f"Vector search found {len(results)} candidates ({threshold_info})")
    
    return [dict(row) for row in results]


async def get_resume_chunks_embeddings(
    session: AsyncSession,
    resume_id: UUID,
    section: Optional[str] = None,
    limit: int = 5
) -> List[tuple]:
    """
    Get resume chunk embeddings for similarity calculations.
    
    Args:
        session: Database session
        resume_id: Resume ID
        section: Optional section filter (e.g., "work experience")
        limit: Maximum number of chunks to retrieve
        
    Returns:
        List of (chunk, embedding) tuples
    """
    query = select(ResumeChunk).where(ResumeChunk.resume_id == resume_id)
    
    if section:
        query = query.where(ResumeChunk.section == section)
    
    query = query.options(selectinload(ResumeChunk.embedding_row)).limit(limit)
    
    chunks = (await session.execute(query)).scalars().all()
    
    result = []
    for chunk in chunks:
        emb_row = getattr(chunk, "embedding_row", None)
        if emb_row and emb_row.embedding is not None:
            result.append((chunk, emb_row.embedding))
    
    return result


async def get_job_chunks_embeddings(
    session: AsyncSession,
    job_id: UUID,
    section: Optional[str] = None,
    limit: int = 5
) -> List[tuple]:
    """
    Get job chunk embeddings for similarity calculations.
    
    Args:
        session: Database session
        job_id: Job ID
        section: Optional section filter (e.g., "responsibility")
        limit: Maximum number of chunks to retrieve
        
    Returns:
        List of (chunk, embedding) tuples
    """
    query = select(JobChunk).where(JobChunk.job_id == job_id)
    
    if section:
        query = query.where(JobChunk.section == section)
    
    query = query.options(selectinload(JobChunk.embedding_row)).limit(limit)
    
    chunks = (await session.execute(query)).scalars().all()
    
    result = []
    for chunk in chunks:
        emb_row = getattr(chunk, "embedding_row", None)
        if emb_row and emb_row.embedding is not None:
            result.append((chunk, emb_row.embedding))
    
    return result
