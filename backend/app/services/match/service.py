"""Main matching service orchestrating ensemble retrieval (RAG + skills + experience) and LLM evaluation for job-to-resume matching."""

from __future__ import annotations
import logging
from uuid import UUID
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Job, JobCandidate, Resume
from app.services.match.retrieval.ensemble import search_and_score_candidates
from app.services.match.llm_judge import LLMJudge
from app.services.resumes.ingestion_pipeline import _extract_profession

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
        Run the complete matching pipeline with optimization to skip already-reviewed candidates.
        
        Flow:
        1. Check existing candidates: Get candidates already in JobCandidate table
        2. Identify "Stage 1 Complete": Candidates with 'rag_score' are skipped in Stage 1
        3. RAG + Algorithms: Score ONLY NEW candidates (or those missing rag_score)
        4. Persist Stage 1 Scores: Save rag_score for new candidates immediately
        5. Combine & Sort: Merge new + existing candidates, sort by rag_score
        6. Select Top N: Pick the best candidates
        7. LLM: Perform deep evaluation ONLY on top N (if not already evaluated)
        
        Args:
            session: Database session
            job_id: Job to match
            top_n: Number of final candidates to return
            min_threshold: (deprecated) minimum score threshold
            
        Returns:
            Dict with job_id, new_candidates, previously_reviewed_count, and metadata
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
        
        # STEP 0: Get existing candidates
        logger.info("STEP 0: Checking for existing candidates...")
        stmt = select(JobCandidate).where(JobCandidate.job_id == job_id)
        result = await session.execute(stmt)
        existing_candidates = result.scalars().all()
        
        # Map resume_id -> JobCandidate
        existing_candidates_map = {c.resume_id: c for c in existing_candidates}
        
        # Identify which resumes have already completed Stage 1 (have rag_score)
        stage1_complete_ids = {
            c.resume_id for c in existing_candidates 
            if c.rag_score is not None
        }
        
        logger.info(f"Found {len(existing_candidates)} total candidates in DB")
        logger.info(f"Found {len(stage1_complete_ids)} candidates with Stage 1 (RAG) score already calculated")
        logger.info("")
        
        # STEP 1: Ensemble Retrieval (RAG + Skills + Experience) - ONLY NEW/UNSCORED CANDIDATES
        logger.info("STEP 1: Ensemble Retrieval & Scoring (Delta run)")
        logger.info("-" * 80)
        
        # We ask for a large limit to get ALL potential new candidates, 
        # so we can save their scores and not run them again next time.
        new_scored_candidates = await search_and_score_candidates(
            session=session,
            job=job,
            limit=10000,  # Get all matches to persist their scores
            exclude_resume_ids=stage1_complete_ids
        )
        
        logger.info(f"Ensemble scoring found {len(new_scored_candidates)} NEW candidates to update in DB")
        
        # STEP 1.5: Persist Stage 1 Scores for NEW candidates
        # This ensures that next time we run, we don't re-calculate these
        for cand_data in new_scored_candidates:
            resume_id = cand_data["resume_id"]
            rag_score = cand_data["rag_score"]
            breakdown = cand_data.get("breakdown", {})
            stability_detail = cand_data.get("stability_detail", {})
            
            # Get or create JobCandidate
            job_candidate = existing_candidates_map.get(resume_id)
            if not job_candidate:
                job_candidate = JobCandidate(
                    job_id=job_id,
                    resume_id=resume_id,
                    status="new"
                )
                session.add(job_candidate)
                existing_candidates_map[resume_id] = job_candidate
            
            # Update Stage 1 info
            job_candidate.rag_score = rag_score
            
            # Update analysis_json (preserve existing fields if any)
            current_analysis = dict(job_candidate.analysis_json) if job_candidate.analysis_json else {}
            current_analysis["rag_breakdown"] = breakdown
            current_analysis["stability"] = stability_detail
            job_candidate.analysis_json = current_analysis
            
        # Commit Stage 1 scores immediately
        if new_scored_candidates:
            await session.commit()
            logger.info("Persisted Stage 1 scores for new candidates")
        
        # STEP 2: Reconstruct Full Candidate List (Existing + New)
        logger.info("STEP 2: Reconstructing full candidate list...")
        
        all_candidates_data = []
        
        # Helper to reconstruct candidate dict from DB record
        async def reconstruct_candidate_data(jc: JobCandidate) -> dict | None:
            resume = await session.get(Resume, jc.resume_id)
            if not resume:
                return None
                
            extraction = resume.extraction_json or {}
            person = extraction.get("person", {})
            analysis = jc.analysis_json or {}
            
            # Re-extract basic info
            name = person.get("name", "Unknown")
            
            # Extract emails/phones
            emails = person.get("emails", [])
            email = emails[0].get("value") if emails and isinstance(emails, list) and len(emails) > 0 and isinstance(emails[0], dict) else None
            
            phones = person.get("phones", [])
            phone = phones[0].get("value") if phones and isinstance(phones, list) and len(phones) > 0 and isinstance(phones[0], dict) else None
            
            # Experience years
            exp_meta = extraction.get("experience_meta", {})
            rec_primary = exp_meta.get("recommended_primary_years", {})
            experience_years = rec_primary.get("tech")
            
            # Title
            experiences = extraction.get("experience", [])
            education = extraction.get("education", [])
            title = _extract_profession(experiences, education, person)
            
            # Skills set
            skills_set = set()
            # We don't have the full skills extraction here easily without re-running logic,
            # but for the UI list we mainly need the name/title/score.
            # If we need skills tags in UI, we might need to re-extract or store them.
            # For now, let's try to get them from extraction if available
            for s in extraction.get("skills", []):
                if isinstance(s, dict):
                    skills_set.add(s.get("name", "").lower())
                elif isinstance(s, str):
                    skills_set.add(s.lower())

            return {
                "resume_id": jc.resume_id,
                "status": jc.status,
                "rag_score": jc.rag_score or 0,
                "final_score": jc.match_score or jc.rag_score or 0, # Use match_score if available, else rag_score
                "llm_score": jc.llm_score,
                "breakdown": analysis.get("rag_breakdown", {}),
                "stability_detail": analysis.get("stability", {}),
                "llm_analysis": {
                    "verdict": analysis.get("llm_verdict"),
                    "strengths": analysis.get("llm_strengths"),
                    "concerns": analysis.get("llm_concerns")
                },
                "contact": {
                    "name": name,
                    "title": title,
                    "email": email,
                    "phone": phone,
                    "experience_years": experience_years,
                    "resume_url": f"/resumes/{jc.resume_id}/file",
                    "file_name": Path(resume.file_path).name if resume.file_path else None,
                    "skills": skills_set,
                }
            }

        # Add NEW candidates (already in dict format)
        # We use the dicts returned by search_and_score_candidates directly as they are rich
        for c in new_scored_candidates:
            # Ensure final_score is set (it might be just rag_score for now)
            c["final_score"] = c["rag_score"]
            all_candidates_data.append(c)
            
        # Add EXISTING candidates (reconstruct from DB)
        # We only need to reconstruct those that were NOT in new_scored_candidates
        new_ids = {c["resume_id"] for c in new_scored_candidates}
        
        for jc in existing_candidates:
            if jc.resume_id not in new_ids and jc.rag_score is not None:
                data = await reconstruct_candidate_data(jc)
                if data:
                    all_candidates_data.append(data)
        
        # Sort by RAG Score (Stage 1) to find the best ones
        # Note: If we have match_score (Stage 2), we might want to sort by that?
        # But the funnel logic says: Sort by Stage 1 to decide who goes to Stage 2.
        # For the final return list, we probably want to sort by final_score.
        # Let's sort by rag_score first to pick the top N for LLM.
        
        # Filter: Keep only candidates that are effectively "NEW" (Status based)
        # This ensures we keep seeing the best candidates until the human moves them to another status.
        candidates_pool_for_selection = [
            c for c in all_candidates_data 
            if c.get("status", "new") == "new"
        ]
        
        candidates_pool_for_selection.sort(key=lambda x: x["rag_score"], reverse=True)
        
        logger.info(f"Total candidates available for selection (Status=new): {len(candidates_pool_for_selection)}")
        
        # Select Top N for LLM Evaluation
        candidates_for_llm_pool = candidates_pool_for_selection[:top_n]
        
        # STEP 3: LLM Deep Evaluation (Stage 2)
        # Only run LLM on candidates that don't have an LLM score yet
        candidates_needing_llm = []
        for c in candidates_for_llm_pool:
            # Check if we already have a valid LLM score
            # We check the dict key 'llm_score' which we populated in reconstruct or from new
            if c.get("llm_score") is None:
                candidates_needing_llm.append(c)
        
        logger.info("STEP 3: LLM Deep Evaluation")
        logger.info("-" * 80)
        logger.info(f"Top {len(candidates_for_llm_pool)} candidates selected.")
        logger.info(f"Candidates needing LLM evaluation: {len(candidates_needing_llm)}")
        
        if candidates_needing_llm:
            logger.info("Sending candidates to LLM...")
            llm_results = await LLMJudge.evaluate_candidates(
                session=session,
                job=job,
                candidates=candidates_needing_llm
            )
            
            # Update the data in our list with LLM results
            llm_results_map = {c["resume_id"]: c for c in llm_results}
            
            for i, c in enumerate(candidates_for_llm_pool):
                rid = c["resume_id"]
                if rid in llm_results_map:
                    # Replace with the enriched version from LLM (contains final_score, llm_analysis etc)
                    candidates_for_llm_pool[i] = llm_results_map[rid]
        else:
            logger.info("All top candidates already have LLM scores. Skipping LLM.")

        # STEP 4: Final Persistence & Response Building
        logger.info("STEP 4: Finalizing results...")
        
        response_candidates = []
        
        # Helper for string conversion
        def _ensure_string(value):
            if isinstance(value, list):
                return "\n".join(str(item) for item in value)
            return str(value) if value else ""

        # We iterate over the top N pool which now has updated scores
        for candidate in candidates_for_llm_pool:
            resume_id = candidate["resume_id"]
            contact = candidate["contact"]
            
            # Convert skills set to list for JSON
            if isinstance(contact.get("skills"), set):
                contact["skills"] = sorted(list(contact["skills"]))
            
            # Extract LLM analysis fields
            llm_analysis = candidate.get("llm_analysis", {})
            
            # Extract stability data
            stability_detail = candidate.get("stability_detail", {})
            stability_score = stability_detail.get("score", 0.5) if stability_detail else 0.5
            stability_verdict = stability_detail.get("verdict", "unknown") if stability_detail else "unknown"
            
            # Update DB with Final Scores (LLM + Match)
            job_candidate = existing_candidates_map.get(resume_id)
            # (Should exist by now)
            
            if job_candidate:
                # Update scores
                job_candidate.match_score = int(candidate["final_score"])
                # rag_score is already set
                job_candidate.llm_score = int(candidate.get("llm_score", 0)) if candidate.get("llm_score") is not None else None
                
                # Update Analysis JSON with LLM results
                current_analysis = dict(job_candidate.analysis_json) if job_candidate.analysis_json else {}
                current_analysis["llm_verdict"] = llm_analysis.get("verdict")
                current_analysis["llm_strengths"] = llm_analysis.get("strengths")
                current_analysis["llm_concerns"] = llm_analysis.get("concerns")
                # stability and rag_breakdown already set
                job_candidate.analysis_json = current_analysis

            response_candidates.append({
                "resume_id": resume_id,
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
                "status": job_candidate.status if job_candidate else "new",
            })
        
        # Commit final updates
        await session.commit()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("MATCH COMPLETE")
        logger.info("=" * 80)
        
        return {
            "job_id": job_id,
            "requested_top_n": top_n,
            "min_threshold": min_threshold,
            "new_candidates": response_candidates,
            "new_count": len(new_scored_candidates),
            "previously_reviewed_count": len(stage1_complete_ids),
            "all_candidates_already_reviewed": False # Logic changed, we always return mixed list
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
