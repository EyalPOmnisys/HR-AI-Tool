# app/services/match/service.py
"""
Match Service - Main orchestrator for the job-to-resume matching pipeline.
Coordinates RAG vector search and LLM deep evaluation to rank and return top candidates.
"""
from __future__ import annotations
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job
from app.services.match.match_rag import RAGMatcher
from app.services.match.llm_judge import LLMJudge

logger = logging.getLogger("match.service")


class MatchService:
    """Main service for matching jobs to resumes."""
    
    @staticmethod
    async def run(
        session: AsyncSession,
        job_id: UUID,
        top_n: int,
        min_threshold: int  # Kept for API compatibility, not used anymore
    ):
        """
        Run the complete matching pipeline.
        
        Flow:
        1. RAG: Compare job embeddings to all resume embeddings → Get top 50 candidates
        2. Select: Pick top N candidates (user specified)
        3. LLM: Load full resumes and perform deep evaluation
        
        Args:
            session: Database session
            job_id: Job to match
            top_n: Number of final candidates to return
            min_threshold: (deprecated) minimum score threshold
            
        Returns:
            Dict with job_id, candidates list, and metadata
        """
        logger.info("=" * 80)
        logger.info("MATCH SERVICE: Starting match run")
        logger.info("=" * 80)
        logger.info("Job ID: %s", job_id)
        logger.info("Requested top N: %d", top_n)
        logger.info("")
        
        # Load job
        job: Job = await session.get(Job, job_id)
        if not job:
            logger.error("Job not found: %s", job_id)
            raise ValueError(f"Job {job_id} not found")
        
        logger.info("Job loaded: '%s'", job.title)
        logger.info("")
        
        # STEP 1: RAG Matching
        # Get top 50 candidates by vector similarity (we'll narrow down to top_n after LLM)
        logger.info("STEP 1/3: RAG Matching")
        logger.info("-" * 80)
        rag_candidates = await RAGMatcher.match_job_to_resumes(
            session=session,
            job=job,
            top_n=50  # Get broader pool for LLM to refine
        )
        
        if not rag_candidates:
            logger.warning("No candidates found by RAG matching")
            return {
                "job_id": job_id,
                "requested_top_n": top_n,
                "returned": 0,
                "candidates": []
            }
        
        logger.info("RAG matching found %d candidates", len(rag_candidates))
        logger.info("")
        
        # STEP 2: Select top candidates for deep evaluation
        # Take more than requested to give LLM choices, but not too many (token limits)
        logger.info("STEP 2/3: Selecting candidates for LLM evaluation")
        logger.info("-" * 80)
        
        # Take top N*2 or min 15 candidates for LLM
        llm_pool_size = max(15, min(top_n * 2, 30))
        selected_for_llm = rag_candidates[:llm_pool_size]
        
        logger.info("Selected %d candidates for LLM deep evaluation", len(selected_for_llm))
        logger.info("")
        
        # STEP 3: LLM Deep Evaluation
        logger.info("STEP 3/3: LLM Deep Evaluation")
        logger.info("-" * 80)
        
        final_candidates = await LLMJudge.evaluate_candidates(
            session=session,
            job=job,
            candidates=selected_for_llm
        )
        
        # Take only top_n final results
        final_candidates = final_candidates[:top_n]
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("MATCH COMPLETE")
        logger.info("=" * 80)
        logger.info("Returning %d candidates (requested: %d)", len(final_candidates), top_n)
        if final_candidates:
            logger.info("Top 5 scores: %s", [c["final_score"] for c in final_candidates[:5]])
        logger.info("=" * 80)
        
        # Build API response
        response_candidates = []
        for candidate in final_candidates:
            contact = candidate["contact"]
            
            # Convert skills set to list for JSON
            if isinstance(contact.get("skills"), set):
                contact["skills"] = sorted(list(contact["skills"]))
            
            response_candidates.append({
                "resume_id": candidate["resume_id"],
                "match": candidate["final_score"],
                "candidate": contact.get("name"),
                "experience": _format_experience(contact.get("experience_years")),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "resume_url": contact.get("resume_url"),
                "rag_score": candidate["rag_score"],
                "rag_breakdown": candidate.get("breakdown", {}),  # Add weighted breakdown
                "llm_score": candidate.get("llm_score", 0),
                "llm_verdict": candidate.get("llm_verdict", "not_evaluated"),
                "llm_strengths": candidate.get("llm_strengths", ""),
                "llm_concerns": candidate.get("llm_concerns", ""),
                "llm_recommendation": candidate.get("llm_recommendation", ""),
            })
        
        return {
            "job_id": job_id,
            "requested_top_n": top_n,
            "returned": len(response_candidates),
            "candidates": response_candidates
        }


def _format_experience(years: float | None) -> str | None:
    """Format experience years for display."""
    if years is None:
        return None
    if years < 1:
        return "<1 yr"
    if years % 1 == 0:
        return f"{int(years)} yrs"
    return f"{years:.1f} yrs"
