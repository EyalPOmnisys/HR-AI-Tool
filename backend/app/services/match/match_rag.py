# app/services/match/match_rag.py
"""
Weighted RAG Matcher - Multi-factor similarity scoring between jobs and resumes.
Uses fast exact/keyword matching with balanced weights: skills (30%), title (30%), experience (30%), description (10%).
LLM Judge provides deep semantic evaluation for final scoring.
"""
from __future__ import annotations
import logging
import numpy as np
from typing import Dict, List
from uuid import UUID
from sqlalchemy import text, bindparam, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobChunk, Resume, ResumeChunk
from app.services.match.config import CFG
from app.services.match.utils import get_embedding, cosine_similarity, calculate_skills_similarity

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
        Match job to all resumes using weighted RAG scoring.
        Two-stage process: quick filter (vector search) then detailed weighted scoring.
        
        Args:
            session: Database session
            job: Job to match against
            top_n: Number of top candidates to return
            
        Returns:
            List of candidate dicts with rag_score, breakdown, resume_id, and metadata
        """
        logger.info("=" * 80)
        logger.info("WEIGHTED RAG MATCHING: Job '%s' against all resumes", job.title)
        logger.info("=" * 80)
        
        # ===== STAGE 1: Quick Vector Filter (get ~200 candidates) =====
        logger.info("Stage 1: Quick vector-based filtering...")
        
        job_embedding = await RAGMatcher._get_job_embedding(session, job)
        if job_embedding is None:
            logger.error("No job embedding found")
            return []
        
        # Query for candidates using fast vector search
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
            LIMIT :limit
        """)
        
        job_vec_str = str(job_embedding.tolist() if hasattr(job_embedding, 'tolist') else job_embedding)
        
        quick_results = (await session.execute(
            sql,
            {
                "job_vec": job_vec_str,
                "min_threshold": CFG.min_cosine_for_evidence,
                "limit": 200  # Get more candidates for detailed scoring
            }
        )).mappings().all()
        
        logger.info(f"Quick filter found {len(quick_results)} candidates")
        
        if not quick_results:
            logger.info("No candidates passed quick filter threshold")
            return []
        
        # ===== STAGE 2: Detailed Weighted Scoring =====
        logger.info("Stage 2: Calculating detailed weighted scores...")
        
        candidates = []
        for idx, row in enumerate(quick_results):
            resume_id = row["resume_id"]
            
            # Load resume data
            resume: Resume = await session.get(Resume, resume_id)
            if not resume:
                continue
            
            # Calculate weighted score with breakdown
            try:
                weighted_result = await RAGMatcher.calculate_weighted_score(session, job, resume)
                total_score = weighted_result["total_score"]
                breakdown = weighted_result["breakdown"]
                
                # Convert to 0-100 scale
                rag_score = int(total_score * 100)
                
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
                    tech_years = rec_primary.get("tech")
                    if tech_years is not None and isinstance(tech_years, (int, float)):
                        experience_years = float(tech_years)
                
                candidates.append({
                    "resume_id": resume_id,
                    "rag_score": rag_score,
                    "similarity": total_score,  # 0-1 scale for compatibility
                    "breakdown": {
                        "title": int(breakdown["title_similarity"] * 100),
                        "skills": int(breakdown["skills_match"] * 100),
                        "experience": int(breakdown["experience_match"] * 100),
                        "description": int(breakdown["description_similarity"] * 100)
                    },
                    "contact": {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "experience_years": experience_years,
                        "resume_url": f"/resumes/{resume_id}/file",
                        "skills": skills,
                    }
                })
                
                # Log progress every 50 candidates
                if (idx + 1) % 50 == 0:
                    logger.info(f"Processed {idx + 1}/{len(quick_results)} candidates...")
                    
            except Exception as e:
                logger.error(f"Error scoring resume {resume_id}: {e}", exc_info=True)
                continue
        
        # Sort by RAG score and take top N
        candidates.sort(key=lambda x: x["rag_score"], reverse=True)
        final_candidates = candidates[:top_n]
        
        logger.info("=" * 80)
        logger.info("WEIGHTED RAG MATCHING COMPLETE")
        logger.info(f"Returning {len(final_candidates)} candidates")
        if final_candidates:
            top_5 = final_candidates[:5]
            logger.info("Top 5 scores:")
            for i, c in enumerate(top_5, 1):
                b = c["breakdown"]
                logger.info(f"  {i}. Score={c['rag_score']} (T:{b['title']} S:{b['skills']} E:{b['experience']} D:{b['description']})")
        logger.info("=" * 80)
        
        return final_candidates
    
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
    
    @staticmethod
    async def calculate_weighted_score(
        session: AsyncSession,
        job: Job,
        resume: Resume
    ) -> Dict:
        """
        Calculate weighted RAG score based on multiple factors.
        Weights: Skills 30%, Title 30%, Experience 30%, Description 10%.
        
        Args:
            session: Database session
            job: Job to match
            resume: Resume to score
            
        Returns:
            Dict with total_score (0-1) and breakdown of component scores
        """
        # Extract job data
        job_analysis = job.analysis_json or {}
        job_title = job_analysis.get("role_title") or job.title or ""
        
        # Extract resume data
        resume_extraction = resume.extraction_json or {}
        
        # ===== 1. TITLE SIMILARITY (25%) =====
        # Use simple keyword overlap instead of embeddings for speed
        # LLM Judge will handle semantic title matching
        title_score = 0.0
        try:
            experiences = resume_extraction.get("experience", [])
            if experiences and isinstance(experiences, list) and len(experiences) > 0:
                resume_title = experiences[0].get("title", "").lower()
                
                if job_title and resume_title:
                    # Simple keyword overlap
                    job_words = set(job_title.lower().split())
                    resume_words = set(resume_title.split())
                    
                    common_words = job_words & resume_words
                    if common_words:
                        # Jaccard similarity
                        title_score = len(common_words) / len(job_words | resume_words)
                    else:
                        title_score = 0.0
                    
                    logger.debug(f"Title overlap: '{job_title}' vs '{resume_title}' = {title_score:.3f}")
                else:
                    title_score = 0.0
            else:
                title_score = 0.0
        except Exception as e:
            logger.warning(f"Error calculating title similarity: {e}")
            title_score = 0.0
        
        # ===== 2. SKILLS MATCH (30%) =====
        skills_score = 0.0
        try:
            # Get job skills
            job_skills = job_analysis.get("skills", {})
            must_have_list = job_skills.get("must_have", [])
            nice_to_have_list = job_skills.get("nice_to_have", [])
            
            # Normalize to lowercase sets
            must_have = set(s.lower().strip() for s in must_have_list if s)
            nice_to_have = set(s.lower().strip() for s in nice_to_have_list if s)
            
            # Get resume skills
            resume_skills_list = resume_extraction.get("skills", [])
            resume_skills = set()
            for skill in resume_skills_list:
                if isinstance(skill, dict):
                    skill_name = skill.get("name")
                    if skill_name:
                        resume_skills.add(skill_name.lower().strip())
                elif isinstance(skill, str):
                    resume_skills.add(skill.lower().strip())
            
            # Calculate weighted skills match
            if must_have or nice_to_have:
                skills_score = calculate_skills_similarity(must_have, nice_to_have, resume_skills)
                logger.debug(f"Skills match: {len(must_have & resume_skills)}/{len(must_have)} must-have, score={skills_score:.3f}")
            else:
                skills_score = 0.5  # No skills specified, give neutral score
        except Exception as e:
            logger.warning(f"Error calculating skills match: {e}")
            skills_score = 0.5
        
        # ===== 3. EXPERIENCE MATCH (30%) =====
        exp_score = 0.0
        try:
            # Get required years from job
            job_exp = job_analysis.get("experience", {})
            job_min_years = job_exp.get("years_min", 0) or 0
            
            # Get candidate years from resume
            exp_meta = resume_extraction.get("experience_meta", {})
            rec_primary = exp_meta.get("recommended_primary_years", {})
            resume_years = rec_primary.get("tech", 0) or 0
            
            # Calculate experience match
            if job_min_years > 0:
                if resume_years >= job_min_years:
                    exp_score = 1.0  # Meets or exceeds requirement
                elif resume_years >= job_min_years * 0.8:
                    exp_score = 0.8  # Within 20% (close enough)
                else:
                    exp_score = resume_years / job_min_years  # Proportional
                    
                logger.debug(f"Experience: requires {job_min_years}y, has {resume_years}y, score={exp_score:.3f}")
            else:
                # No experience requirement specified
                exp_score = 1.0 if resume_years > 0 else 0.5
        except Exception as e:
            logger.warning(f"Error calculating experience match: {e}")
            exp_score = 0.5
        
        # ===== 4. DESCRIPTION SIMILARITY (10%) =====
        desc_score = 0.0
        try:
            # Get job responsibility chunks
            job_chunks_result = await session.execute(
                select(JobChunk)
                .where(JobChunk.job_id == job.id, JobChunk.section == "responsibility")
                .options(selectinload(JobChunk.embedding_row))
                .limit(5)  # Limit to top 5 for performance
            )
            job_chunks = job_chunks_result.scalars().all()
            
            # Get resume work experience chunks  
            resume_chunks_result = await session.execute(
                select(ResumeChunk)
                .where(ResumeChunk.resume_id == resume.id, ResumeChunk.section == "work experience")
                .options(selectinload(ResumeChunk.embedding_row))
                .limit(5)
            )
            resume_chunks = resume_chunks_result.scalars().all()
            
            # Calculate average similarity between chunks
            similarities = []
            for job_chunk in job_chunks:
                job_emb_row = getattr(job_chunk, "embedding_row", None)
                if not job_emb_row or job_emb_row.embedding is None:
                    continue
                    
                for resume_chunk in resume_chunks:
                    res_emb_row = getattr(resume_chunk, "embedding_row", None)
                    if not res_emb_row or res_emb_row.embedding is None:
                        continue
                    
                    sim = cosine_similarity(job_emb_row.embedding, res_emb_row.embedding)
                    similarities.append(sim)
            
            if similarities:
                desc_score = float(np.mean(similarities))
                logger.debug(f"Description similarity: avg of {len(similarities)} chunk pairs = {desc_score:.3f}")
            else:
                desc_score = 0.5  # No chunks to compare, neutral score
        except Exception as e:
            logger.warning(f"Error calculating description similarity: {e}")
            desc_score = 0.5
        
        # ===== WEIGHTED TOTAL =====
        # Balanced weights for fast matching:
        # Skills 30% - exact matching for technical requirements
        # Title 30% - keyword overlap for role alignment  
        # Experience 30% - years comparison for seniority
        # Description 10% - chunk similarity for soft skills/culture
        # LLM Judge handles deep semantic evaluation & transferable skills
        total_score = (
            0.30 * title_score +
            0.30 * skills_score +
            0.30 * exp_score +
            0.10 * desc_score
        )
        
        return {
            "total_score": float(total_score),
            "breakdown": {
                "title_similarity": float(title_score),
                "skills_match": float(skills_score),
                "experience_match": float(exp_score),
                "description_similarity": float(desc_score)
            }
        }

