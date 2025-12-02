"""Main matching service orchestrating ensemble retrieval (RAG + skills + experience) and LLM evaluation for job-to-resume matching."""

from __future__ import annotations
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Job, JobCandidate
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
        min_threshold: int,  # Kept for API compatibility, not used anymore
        status_filter: list[str] | None = None
    ):
        """
        Run the complete matching pipeline.
        
        Flow:
        1. RAG + Algorithms: Score ALL candidates in DB using ensemble method
        2. Select: Pick top N candidates with highest scores (user specified)
        3. LLM: Perform deep evaluation in batches of 3 - LLM provides FINAL authoritative score
        
        Args:
            session: Database session
            job_id: Job to match
            top_n: Number of final candidates to return
            min_threshold: (deprecated) minimum score threshold
            status_filter: List of statuses to include (e.g. ["new", "reviewed"])
            
        Returns:
            Dict with job_id, candidates list, and metadata
        """
        logger.info("=" * 80)
        logger.info("MATCH SERVICE: Starting match run")
        logger.info("=" * 80)
        logger.info("Job ID: %s", job_id)
        logger.info("Requested top N: %d", top_n)
        if status_filter:
            logger.info("Status filter: %s", status_filter)
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
            limit=top_n,  # Get exactly what user requested
            status_filter=status_filter
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
        logger.info("STEP 2/2: LLM Deep Evaluation (batches of 3)")
        logger.info("-" * 80)
        logger.info("Sending all %d candidates to LLM for authoritative scoring", len(candidates))
        
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
        
        # Fetch existing statuses for these candidates
        resume_ids = [c["resume_id"] for c in final_candidates]
        stmt = select(JobCandidate).where(
            JobCandidate.job_id == job_id,
            JobCandidate.resume_id.in_(resume_ids)
        )
        result = await session.execute(stmt)
        existing_candidates = {c.resume_id: c.status for c in result.scalars().all()}

        # Build API response
        response_candidates = []
        for candidate in final_candidates:
            contact = candidate["contact"]
            
            # Convert skills set to list for JSON
            if isinstance(contact.get("skills"), set):
                contact["skills"] = sorted(list(contact["skills"]))
            
            # Extract LLM analysis fields
            llm_analysis = candidate.get("llm_analysis", {})
            
            # Convert list to string if needed (Ollama sometimes returns lists)
            def _ensure_string(value):
                if isinstance(value, list):
                    return "\n".join(str(item) for item in value)
                return str(value) if value else ""
            
            # Extract stability data
            stability_detail = candidate.get("stability_detail", {})
            stability_score = stability_detail.get("score", 0.5) if stability_detail else 0.5
            stability_verdict = stability_detail.get("verdict", "unknown") if stability_detail else "unknown"
            
            # Get status or default to "new"
            status = existing_candidates.get(candidate["resume_id"], "new")

            response_candidates.append({
                "resume_id": candidate["resume_id"],
                "match": candidate["final_score"],
                "candidate": contact.get("name"),
                "title": contact.get("title"),
                "experience": _format_experience(contact.get("experience_years")),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "resume_url": contact.get("resume_url"),
                "file_name": contact.get("file_name"),
                "rag_score": candidate["rag_score"],
                "rag_breakdown": candidate.get("breakdown", {}),
                "llm_strengths": _ensure_string(llm_analysis.get("strengths", "")),
                "llm_concerns": _ensure_string(llm_analysis.get("concerns", "")),
                "stability_score": int(stability_score * 100),
                "stability_verdict": stability_verdict,
                "status": status,
            })
        
        return {
            "job_id": job_id,
            "requested_top_n": top_n,
            "returned": len(response_candidates),
            "candidates": response_candidates
        }


def _format_experience(years: float | None) -> str:
    """Format experience years for display."""
    if years is None or years == 0:
        return "0 yrs"
    if years < 1:
        return "<1 yr"
    if years % 1 == 0:
        return f"{int(years)} yrs"
    return f"{years:.1f} yrs"
