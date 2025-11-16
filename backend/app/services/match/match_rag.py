# app/services/match/match_rag.py
"""
RAG Matcher - Vector-based similarity search between jobs and resumes.
Uses embedding cosine similarity to find and score the most relevant candidates.
"""
from __future__ import annotations
import logging
from typing import Dict, List
from uuid import UUID
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobChunk, Resume
from app.services.match.config import CFG

logger = logging.getLogger("match.rag")


class RAGMatcher:
    """Handles RAG-based matching between job and resumes."""
    
    @staticmethod
    async def match_job_to_resumes(
        session: AsyncSession,
        job: Job,
        top_n: int = 50
    ) -> List[Dict]:
        """
        Match job to all resumes using RAG (vector similarity).
        
        Args:
            session: Database session
            job: Job to match against
            top_n: Number of top candidates to return
            
        Returns:
            List of candidate dicts with rag_score, resume_id, and metadata
        """
        logger.info("=" * 80)
        logger.info("RAG MATCHING: Job '%s' against all resumes", job.title)
        logger.info("=" * 80)
        
        # Step 1: Get job embedding (use job's main embedding or job chunks)
        job_embedding = await RAGMatcher._get_job_embedding(session, job)
        if job_embedding is None:
            logger.error("No job embedding found")
            return []
        
        # Step 2: Find top N resumes by cosine similarity
        logger.info("Searching for top %d matches...", top_n)
        
        # Query all resume embeddings and rank by similarity
        sql = text("""
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
            WHERE avg_similarity >= :min_threshold
            ORDER BY avg_similarity DESC
            LIMIT :top_n
        """)
        
        # Convert embedding to string for pgvector
        job_vec_str = str(job_embedding.tolist() if hasattr(job_embedding, 'tolist') else job_embedding)
        
        results = (await session.execute(
            sql,
            {
                "job_vec": job_vec_str,
                "min_threshold": CFG.min_cosine_for_evidence,
                "top_n": top_n * 2  # Get extra to filter later
            }
        )).mappings().all()
        
        logger.info("Found %d candidate matches", len(results))
        
        # Step 3: Load resume metadata and create candidate objects
        candidates = []
        for row in results:
            resume_id = row["resume_id"]
            similarity = row["avg_similarity"]
            
            # Load resume data
            resume: Resume = await session.get(Resume, resume_id)
            if not resume:
                continue
            
            # Extract contact info
            extraction = resume.extraction_json or {}
            person = extraction.get("person", {})
            
            # Get email
            emails = person.get("emails", [])
            email = None
            if emails and isinstance(emails, list) and len(emails) > 0:
                email_obj = emails[0]
                email = email_obj.get("value") if isinstance(email_obj, dict) else email_obj
            
            # Get phone
            phones = person.get("phones", [])
            phone = None
            if phones and isinstance(phones, list) and len(phones) > 0:
                phone_obj = phones[0]
                phone = phone_obj.get("value") if isinstance(phone_obj, dict) else phone_obj
            
            # Get name
            name = person.get("name")
            
            # Get skills
            skills_raw = extraction.get("skills", [])
            skills = set()
            if isinstance(skills_raw, list):
                for skill in skills_raw:
                    if isinstance(skill, dict):
                        skill_name = skill.get("name")
                        if skill_name:
                            skills.add(skill_name.lower().strip())
                    elif isinstance(skill, str):
                        skills.add(skill.lower().strip())
            
            # Get experience years
            experience_years = None
            exp_meta = extraction.get("experience_meta", {})
            rec_primary = exp_meta.get("recommended_primary_years", {})
            if isinstance(rec_primary, dict):
                experience_years = rec_primary.get("tech")
            
            # Calculate RAG score (0-100)
            rag_score = RAGMatcher._similarity_to_score(similarity)
            
            candidates.append({
                "resume_id": resume_id,
                "rag_score": rag_score,
                "similarity": float(similarity),
                "contact": {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "experience_years": experience_years,
                    "resume_url": f"/resumes/{resume_id}/file",
                    "skills": skills,
                }
            })
        
        # Sort by RAG score and take top N
        candidates.sort(key=lambda x: x["rag_score"], reverse=True)
        candidates = candidates[:top_n]
        
        logger.info("=" * 80)
        logger.info("RAG MATCHING COMPLETE")
        logger.info("Returning %d candidates", len(candidates))
        if candidates:
            logger.info("Top 5 scores: %s", [c["rag_score"] for c in candidates[:5]])
        logger.info("=" * 80)
        
        return candidates
    
    @staticmethod
    async def _get_job_embedding(session: AsyncSession, job: Job):
        """Get job embedding vector for matching."""
        # Option 1: Use job's primary embedding if exists
        if hasattr(job, 'embedding_vector_768'):
            embedding = job.embedding_vector_768
            # Check if it's not None and not an empty array
            if embedding is not None:
                try:
                    # For numpy arrays, check size
                    if hasattr(embedding, 'size') and embedding.size > 0:
                        logger.info("Using job primary embedding (768d)")
                        return embedding
                    # For lists, check length
                    elif isinstance(embedding, (list, tuple)) and len(embedding) > 0:
                        logger.info("Using job primary embedding (768d)")
                        return embedding
                except:
                    pass  # Fall through to option 2
        
        # Option 2: Get average of all job chunk embeddings
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        job_chunks: List[JobChunk] = (await session.execute(
            select(JobChunk)
            .where(JobChunk.job_id == job.id)
            .options(selectinload(JobChunk.embedding_row))
        )).scalars().all()
        
        # Get embeddings from chunks
        embeddings = []
        for chunk in job_chunks:
            embrow = getattr(chunk, "embedding_row", None)
            if embrow and embrow.embedding is not None:
                embeddings.append(embrow.embedding)
        
        if len(embeddings) == 0:
            logger.warning("No embeddings found for job chunks")
            return None
        
        # Average the embeddings
        import numpy as np
        avg_embedding = np.mean(embeddings, axis=0)
        logger.info("Using average of %d job chunk embeddings", len(embeddings))
        return avg_embedding
    
    @staticmethod
    def _similarity_to_score(similarity: float) -> int:
        """
        Convert cosine similarity (0-1) to score (0-100).
        Maps [0.35, 0.95] to [0, 100] for better spread.
        """
        # Clamp to reasonable range
        sim = max(0.0, min(1.0, similarity))
        
        # Map [0.35, 0.95] to [0, 100]
        if sim < 0.35:
            return 0
        if sim > 0.95:
            return 100
        
        # Linear mapping
        norm = (sim - 0.35) / (0.95 - 0.35)
        return round(norm * 100)
