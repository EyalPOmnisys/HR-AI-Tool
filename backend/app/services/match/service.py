# Main orchestrator for job-to-resume matching pipeline.
# Coordinates ensemble retrieval (RAG + skills + experience) and LLM evaluation.

from __future__ import annotations
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job
from app.services.match.retrieval.ensemble import search_and_score_candidates
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
        1. RAG + Algorithms: Score ALL candidates in DB using ensemble method
        2. Select: Pick top N candidates with highest scores (user specified)
        3. LLM: Perform deep qualitative evaluation in batches of 5
        
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
        
        # STEP 1: Ensemble Retrieval (RAG + Skills + Experience)
        # Score ALL candidates and return top N
        logger.info("STEP 1/2: Ensemble Retrieval & Scoring (ALL candidates)")
        logger.info("-" * 80)
        candidates = await search_and_score_candidates(
            session=session,
            job=job,
            limit=top_n  # Get exactly what user requested
        )
        
        if not candidates:
            logger.warning("No candidates found by ensemble scoring")
            return {
                "job_id": job_id,
                "requested_top_n": top_n,
                "returned": 0,
                "candidates": []
            }
        
        logger.info("Ensemble scoring found %d candidates (requested: %d)", len(candidates), top_n)
        logger.info("")
        
        # STEP 2: LLM Deep Evaluation on ALL selected candidates
        logger.info("STEP 2/2: LLM Deep Evaluation (batches of 5)")
        logger.info("-" * 80)
        logger.info("Sending all %d candidates to LLM for qualitative analysis", len(candidates))
        
        final_candidates = await LLMJudge.evaluate_candidates(
            session=session,
            job=job,
            candidates=candidates  # Pass all candidates from ensemble
        )
        
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
            
            # Extract LLM analysis fields
            llm_analysis = candidate.get("llm_analysis", {})
            
            response_candidates.append({
                "resume_id": candidate["resume_id"],
                "match": candidate["final_score"],
                "candidate": contact.get("name"),
                "experience": _format_experience(contact.get("experience_years")),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "resume_url": contact.get("resume_url"),
                "rag_score": candidate["rag_score"],
                "rag_breakdown": candidate.get("breakdown", {}),
                "llm_strengths": llm_analysis.get("strengths", ""),
                "llm_concerns": llm_analysis.get("concerns", ""),
                "llm_recommendation": llm_analysis.get("recommendation", ""),
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
