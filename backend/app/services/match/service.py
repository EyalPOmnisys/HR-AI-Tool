"""Main matching service orchestrating ensemble retrieval (skills/title/experience/stability) and LLM evaluation for job-to-resume matching."""

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
        Run the complete matching pipeline with 'Smart Backfill' optimization.
        
        Flow:
        1. Check existing candidates: Get candidates already in JobCandidate table.
        2. Ensemble scoring: Score ALL candidates (Stage 1) to get a large pool.
        3. Smart Backfill Loop:
           - Categorize candidates into Good (LLM>=70), Bad (LLM<70), Unknown.
           - If not enough Good candidates, take Unknown ones and run LLM.
           - Repeat until target reached or max rounds.
        4. Persist Scores: Save LLM results to DB.
        5. Return Sorted List: Good -> Bad -> Unknown.
        
        Args:
            session: Database session
            job_id: Job to match
            top_n: Number of final candidates to return
            min_threshold: (deprecated) minimum score threshold
            
        Returns:
            Dict with job_id, new_candidates, previously_reviewed_count, and metadata
        """
        logger.info("=" * 80)
        logger.info("MATCH SERVICE: Starting match run (Smart Backfill Mode)")
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
        
        # --- CONFIGURATION ---
        LLM_PASS_THRESHOLD = 70
        MAX_ROUNDS = 3
        # ---------------------

        # STEP 0: Get existing candidates (to check for previous LLM scores)
        logger.info("STEP 0: Checking for existing candidates...")
        stmt = select(JobCandidate).where(JobCandidate.job_id == job_id)
        result = await session.execute(stmt)
        existing_candidates = result.scalars().all()
        
        # Map resume_id -> JobCandidate
        existing_candidates_map = {c.resume_id: c for c in existing_candidates}
        
        # STEP 1: Ensemble Retrieval (Stage 1) - Get Large Pool
        logger.info("STEP 1: Ensemble Retrieval & Scoring (Large Pool)")
        logger.info("-" * 80)
        
        # We ask for a large limit to get all potential candidates
        candidates_pool = await search_and_score_candidates(
            session=session,
            job=job,
            limit=10000,  # Get all matches
            exclude_resume_ids=set() # Re-score everyone to ensure consistent ranking
        )
        
        logger.info(f"Ensemble scoring found {len(candidates_pool)} candidates")
        
        # STEP 1.5: Persist Stage 1 Scores (RAG)
        # We update the DB with the latest RAG scores
        for cand_data in candidates_pool:
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
            
        await session.commit()
        logger.info("Persisted Stage 1 scores")

        # STEP 2: Reconstruct Full Candidate List & Categorize
        logger.info("STEP 2: Smart Backfill Loop (Target: %d good candidates)", top_n)
        
        # Helper to reconstruct candidate dict from DB record + Pool Data
        async def reconstruct_candidate_data(jc: JobCandidate, pool_data: dict) -> dict | None:
            resume = await session.get(Resume, jc.resume_id)
            if not resume:
                return None
                
            extraction = resume.extraction_json or {}
            person = extraction.get("person", {})
            analysis = jc.analysis_json or {}
            
            # Re-extract basic info
            name = person.get("name")
            if not name or name.strip().lower() == "unknown":
                return None
            
            # Extract emails/phones
            emails = person.get("emails", [])
            email = emails[0].get("value") if emails and isinstance(emails, list) and len(emails) > 0 and isinstance(emails[0], dict) else None
            phones = person.get("phones", [])
            phone = phones[0].get("value") if phones and isinstance(phones, list) and len(phones) > 0 and isinstance(phones[0], dict) else None
            
            # Experience years
            exp_meta = extraction.get("experience_meta", {})
            rec_primary = exp_meta.get("recommended_primary_years", {})
            is_tech_role = job.analysis_json.get("is_tech_role", True) if job.analysis_json else True
            experience_years = rec_primary.get("tech", 0) if is_tech_role else rec_primary.get("other", 0)
            
            # Title
            experiences = extraction.get("experience", [])
            education = extraction.get("education", [])
            title = _extract_profession(experiences, education, person)
            
            # Skills set
            skills_set = set()
            for s in extraction.get("skills", []):
                if isinstance(s, dict):
                    skills_set.add(s.get("name", "").lower())
                elif isinstance(s, str):
                    skills_set.add(s.lower())

            return {
                "resume_id": jc.resume_id,
                "status": jc.status,
                "rag_score": jc.rag_score or 0,
                "final_score": jc.match_score or jc.rag_score or 0,
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
                },
                # Keep pool data for context if needed
                "pool_data": pool_data
            }

        # Build the working list
        all_candidates_data = []
        pool_map = {c["resume_id"]: c for c in candidates_pool}
        
        for jc in existing_candidates_map.values():
            if jc.resume_id in pool_map:
                data = await reconstruct_candidate_data(jc, pool_map[jc.resume_id])
                if data:
                    all_candidates_data.append(data)
        
        # Sort by RAG Score (Stage 1) to prioritize checking
        all_candidates_data.sort(key=lambda x: x["rag_score"], reverse=True)
        
        # Filter: Keep only candidates that are effectively "NEW" (Status based)
        # We only run auto-match on 'new' candidates.
        candidates_pool_for_selection = [
            c for c in all_candidates_data 
            if c.get("status", "new") == "new"
        ]
        
        # Categorize ALL candidates to ensure we don't get blocked by "Bad" ones at the top
        good_candidates = []
        bad_candidates = []
        unknown_candidates = []
        
        for cand in candidates_pool_for_selection:
            llm_score = cand.get("llm_score")
            if llm_score is not None:
                if llm_score >= LLM_PASS_THRESHOLD:
                    good_candidates.append(cand)
                else:
                    bad_candidates.append(cand)
            else:
                unknown_candidates.append(cand)
                
        logger.info(f"Initial State: Good={len(good_candidates)}, Bad={len(bad_candidates)}, Unknown={len(unknown_candidates)}")

        # THE LOOP
        for round_num in range(1, MAX_ROUNDS + 1):
            # Check if we have enough
            if len(good_candidates) >= top_n:
                logger.info(f"Target reached! We have {len(good_candidates)} good candidates.")
                break
            
            if not unknown_candidates:
                logger.info("No more unknown candidates to check.")
                break
                
            needed = top_n - len(good_candidates)
            # Fetch a batch. We take a bit more than needed (1.5x) to increase hit rate
            # CHANGE 4: Increase batch size multiplier to give LLM more options
            # If algorithm isn't perfect, giving LLM more candidates helps it find the needle in the haystack
            batch_size = max(5, int(needed * 3.0)) 
            
            batch_to_test = unknown_candidates[:batch_size]
            unknown_candidates = unknown_candidates[batch_size:] # Remove from pool
            
            logger.info(f"--- ROUND {round_num}/{MAX_ROUNDS} ---")
            logger.info(f"Need {needed} more. Sending {len(batch_to_test)} candidates to LLM...")
            
            # Run LLM
            llm_results = await LLMJudge.evaluate_candidates(
                session=session,
                job=job,
                candidates=batch_to_test
            )
            
            # Process results
            llm_results_map = {c["resume_id"]: c for c in llm_results}
            
            for cand in batch_to_test:
                rid = cand["resume_id"]
                if rid in llm_results_map:
                    result = llm_results_map[rid]
                    
                    # Update candidate object
                    final_score = result.get("final_score", 0) # This is the blended score from LLMJudge
                    llm_score_only = result.get("llm_score", 0)
                    
                    cand["final_score"] = final_score
                    cand["llm_score"] = llm_score_only
                    cand["llm_analysis"] = result.get("llm_analysis", {})
                    
                    # Update DB
                    jc = existing_candidates_map.get(rid)
                    if jc:
                        jc.match_score = final_score
                        jc.llm_score = llm_score_only
                        
                        current_analysis = dict(jc.analysis_json) if jc.analysis_json else {}
                        current_analysis["llm_verdict"] = cand["llm_analysis"].get("verdict")
                        current_analysis["llm_strengths"] = cand["llm_analysis"].get("strengths")
                        current_analysis["llm_concerns"] = cand["llm_analysis"].get("concerns")
                        jc.analysis_json = current_analysis
                        session.add(jc)
                    
                    # Categorize
                    # We use the LLM score (Stage 2) to decide Good/Bad, not the blended final score
                    # because we want to know if the LLM liked them.
                    if llm_score_only >= LLM_PASS_THRESHOLD:
                        good_candidates.append(cand)
                    else:
                        bad_candidates.append(cand)
            
            await session.commit()

        # STEP 3: Final Assembly & Response Building
        logger.info("STEP 3: Finalizing results...")
        
        # Sort Good by score descending
        good_candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        # Sort Bad by score descending
        bad_candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        # Sort Unknown by RAG score descending
        unknown_candidates.sort(key=lambda x: x.get("rag_score", 0), reverse=True)
        
        # Combine: Good first, then Bad (so user sees they were checked), then Unknown
        final_list = good_candidates + bad_candidates + unknown_candidates
        
        # Helper for string conversion
        def _ensure_string(value):
            if isinstance(value, list):
                return "\n".join(str(item) for item in value)
            return str(value) if value else ""

        response_candidates = []
        for candidate in final_list[:top_n]: # Return requested amount (or maybe more?)
            # User requested top_n. If we have 10 good and 5 bad, and top_n=10, we return 10 good.
            # If we have 5 good and 5 bad, and top_n=10, we return all 10.
            
            resume_id = candidate["resume_id"]
            contact = candidate["contact"]
            llm_analysis = candidate.get("llm_analysis", {})
            stability_detail = candidate.get("stability_detail", {})
            
            # Convert skills set to list for JSON
            skills_list = []
            if isinstance(contact.get("skills"), set):
                skills_list = sorted(list(contact["skills"]))
            elif isinstance(contact.get("skills"), list):
                skills_list = contact["skills"]

            response_candidates.append({
                "resume_id": resume_id,
                "match": candidate.get("final_score", 0),
                "candidate": contact.get("name"),
                "title": contact.get("title"),
                "experience": _format_experience(contact.get("experience_years")),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "resume_url": contact.get("resume_url"),
                "file_name": contact.get("file_name"),
                "rag_score": candidate.get("rag_score", 0),
                "llm_score": candidate.get("llm_score"),
                "rag_breakdown": candidate.get("breakdown", {}),
                "llm_strengths": _ensure_string(llm_analysis.get("strengths", "")),
                "llm_concerns": _ensure_string(llm_analysis.get("concerns", "")),
                "stability_score": int(stability_detail.get("score", 0) * 100) if stability_detail else 0,
                "stability_verdict": stability_detail.get("verdict", "unknown") if stability_detail else 0,
                "status": candidate.get("status", "new"),
            })
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("MATCH COMPLETE")
        logger.info("=" * 80)
        
        return {
            "job_id": job_id,
            "requested_top_n": top_n,
            "min_threshold": min_threshold,
            "new_candidates": response_candidates,
            "new_count": len(candidates_pool),
            "previously_reviewed_count": 0, # We re-scored everyone
            "all_candidates_already_reviewed": False
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
