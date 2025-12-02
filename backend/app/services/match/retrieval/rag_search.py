"""Vector-based candidate search using pgvector for semantic similarity matching between job requirements and resume embeddings."""

from __future__ import annotations
import logging
import numpy as np
from typing import List, Optional, Dict
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
    1. Use job's primary embedding if available (Vector 1536)
    2. Calculate average of all job chunk embeddings
    """
    # Option 1: Use job's primary embedding (Fixed attribute name)
    if job.embedding is not None:
        # pgvector returns numpy array or list depending on driver, ensure numpy
        return np.array(job.embedding) if not isinstance(job.embedding, np.ndarray) else job.embedding
    
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
    min_threshold: Optional[float] = None,
    job_id: Optional[UUID] = None,
    status_filter: Optional[List[str]] = None
) -> List[dict]:
    """
    Fast vector search to find candidate resumes using pgvector.
    Uses the Top-Level Resume Embedding for best semantic retrieval.
    
    Args:
        session: Database session
        job_embedding: Job embedding vector
        limit: Maximum number of candidates to return (None = all)
        min_threshold: Minimum cosine similarity threshold (None = no threshold)
        job_id: Optional Job ID for status filtering
        status_filter: Optional list of statuses to filter by
        
    Returns:
        List of dicts with resume_id, avg_similarity, chunk_count
    """
    # Build query with optional threshold and limit
    where_clause = "WHERE r.embedding IS NOT NULL"
    join_clause = ""
    
    params = {"job_vec": str(job_embedding.tolist() if hasattr(job_embedding, 'tolist') else job_embedding)}
    
    if min_threshold is not None:
        where_clause += f" AND 1 - (r.embedding <=> CAST(:job_vec AS vector)) >= :min_threshold"
        params["min_threshold"] = min_threshold
        
    if status_filter and job_id:
        # Join with job_candidates to check status
        join_clause = "LEFT JOIN job_candidates jc ON jc.resume_id = r.id AND jc.job_id = :job_id"
        # Filter by status (treating NULL as 'new')
        where_clause += " AND COALESCE(jc.status, 'new') = ANY(:status_filter)"
        params["job_id"] = job_id
        params["status_filter"] = status_filter
    
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT :limit"
        params["limit"] = limit
    
    # Optimized Query: Uses the main 'resumes' table embedding (Stronger signal for overall fit)
    # We subquery chunk_count to maintain compatibility with your existing return structure
    sql = text(f"""
        SELECT 
            r.id as resume_id,
            1 - (r.embedding <=> CAST(:job_vec AS vector)) as avg_similarity,
            (SELECT COUNT(*) FROM resume_chunks rc WHERE rc.resume_id = r.id) as chunk_count
        FROM resumes r
        {join_clause}
        {where_clause}
        ORDER BY avg_similarity DESC
        {limit_clause}
    """)
    
    results = (await session.execute(sql, params)).mappings().all()
    
    threshold_info = f"threshold={min_threshold:.3f}" if min_threshold else "no threshold"
    filter_info = f"status={status_filter}" if status_filter else "no status filter"
    logger.info(f"Vector search found {len(results)} candidates ({threshold_info}, {filter_info})")
    
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


async def calculate_chunk_coverage(
    session: AsyncSession,
    job_id: UUID,
    resume_ids: List[UUID]
) -> Dict[UUID, float]:
    """
    The "Strongest" Comparison: Calculates how well resumes cover specific Job Requirements.
    
    Logic:
    For each Job Chunk (Requirement), find the BEST matching Resume Chunk.
    Score = Average of these "Best Matches".
    
    This penalizes resumes that miss entire requirements, even if they are generally similar.
    """
    if not resume_ids:
        return {}

    # 1. Get all Job Chunks with embeddings
    job_chunks_result = await session.execute(
        select(JobChunk)
        .where(JobChunk.job_id == job_id)
        .options(selectinload(JobChunk.embedding_row))
    )
    job_chunks = [jc for jc in job_chunks_result.scalars().all() if jc.embedding_row and jc.embedding_row.embedding is not None]
    
    if not job_chunks:
        return {rid: 0.0 for rid in resume_ids}

    # 2. Get all Resume Chunks for the candidates
    # We do this in Python to allow complex N x M logic without crazy SQL joins
    resume_chunks_result = await session.execute(
        select(ResumeChunk)
        .where(ResumeChunk.resume_id.in_(resume_ids))
        .options(selectinload(ResumeChunk.embedding_row))
    )
    all_resume_chunks = resume_chunks_result.scalars().all()
    
    # Group by resume
    resume_map = {rid: [] for rid in resume_ids}
    for rc in all_resume_chunks:
        if rc.embedding_row and rc.embedding_row.embedding is not None:
            resume_map[rc.resume_id].append(np.array(rc.embedding_row.embedding))

    scores = {}
    
    # 3. Calculate Coverage Score for each resume
    for rid, r_embeddings in resume_map.items():
        if not r_embeddings:
            scores[rid] = 0.0
            continue
            
        # For this resume, calculate best match for EACH job chunk
        best_matches = []
        for jc in job_chunks:
            j_vec = np.array(jc.embedding_row.embedding)
            
            # Find max similarity for this specific job chunk against ALL resume chunks
            # (Did the candidate mention this specific requirement anywhere?)
            similarities = [cosine_similarity(j_vec, r_vec) for r_vec in r_embeddings]
            best_match_for_requirement = max(similarities) if similarities else 0.0
            best_matches.append(best_match_for_requirement)
        
        # Final score is the average of the BEST matches
        # High score = Candidate has a good answer for every requirement
        scores[rid] = float(np.mean(best_matches)) if best_matches else 0.0

    return scores
