"""Ensemble scorer combining deterministic matchers (skills/experience/title/stability) into weighted final scores."""

from __future__ import annotations
import logging
import asyncio
from typing import List, Dict, Any
from uuid import UUID
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, Resume
from app.services.match.retrieval import skills_matcher, experience_scorer, title_matcher, employment_stability_scorer
from app.services.match.retrieval.title_matcher import TitleMatcher
from app.services.resumes.ingestion_pipeline import _extract_profession, _extract_skills

logger = logging.getLogger("match.ensemble")

# Initialize title embedder once for efficiency
TITLE_EMBEDDER = None

# Static object for stability details (since we disabled it) - saves re-creating it 1000 times
EMPTY_STABILITY_DETAIL = {
    "score": 0,
    "average_tenure": 0,
    "expected_tenure": 0,
    "total_jobs": 0,
    "short_stints": 0,
    "long_tenures": 0,
    "verdict": "N/A (Disabled)",
    "concerns": [],
    "strengths": []
}

def get_title_embedder():
    """Lazy-load title embedder on first use"""
    global TITLE_EMBEDDER
    if TITLE_EMBEDDER is None:
        TITLE_EMBEDDER = TitleMatcher.get_embedder()
    return TITLE_EMBEDDER


async def search_and_score_candidates(
    session: AsyncSession,
    job: Job,
    limit: int = 50,
    exclude_resume_ids: set[UUID] | None = None,
    specific_resume_ids: List[UUID] | None = None
) -> List[Dict[str, Any]]:
    """
    Main ensemble scorer combining multiple algorithms.
    
    Pipeline:
    1. Candidate selection - load resumes from DB (optionally excluding already-reviewed)
    2. Skills matching - deterministic weighted scoring
    3. Experience scoring - seniority and years match
    4. Title matching - role alignment
    5. Employment stability - tenure pattern scoring
    6. Weighted combination - produce final ranked list
    
    Args:
        session: Database session
        job: Job to match candidates against
        limit: Number of top candidates to return after scoring ALL
        exclude_resume_ids: Set of resume IDs to exclude from search (already reviewed)
        specific_resume_ids: List of specific resume IDs to score (for delta updates)
        
    Returns:
        List of top N candidate dicts with scores, breakdown, and metadata
    """
    logger.info("=" * 80)
    logger.info(f"ENSEMBLE SCORING: Job '{job.title}' (id={job.id})")
    logger.info("=" * 80)
    
    if specific_resume_ids:
        logger.info(f"Scoring SPECIFIC {len(specific_resume_ids)} candidates (Delta Update)")
    else:
        logger.info(f"Will score ALL candidates and return top {limit}")
        
    if exclude_resume_ids:
        logger.info(f"Excluding {len(exclude_resume_ids)} already-reviewed candidates")
    logger.info("")
    
    # ===== STAGE 1: Candidate Selection (No RAG) =====
    logger.info("Stage 1: Candidate selection (no RAG) - loading resumes from DB...")

    stmt = select(Resume).where(Resume.extraction_json.isnot(None))
    
    if specific_resume_ids:
        stmt = stmt.where(Resume.id.in_(specific_resume_ids))
    elif exclude_resume_ids:
        stmt = stmt.where(~Resume.id.in_(exclude_resume_ids))

    # Load candidates to score (DB selection is the only filtering stage)
    resumes: list[Resume] = (await session.execute(stmt)).scalars().all()
    logger.info("Loaded %d resumes to score", len(resumes))
    if not resumes:
        logger.info("No candidates found in DB")
        return []

    # ===== STAGE 2: Detailed Scoring for Each Candidate =====
    logger.info(f"Stage 2: Detailed scoring for ALL {len(resumes)} candidates...")
    logger.info("")
    
    # Extract job requirements
    job_analysis = job.analysis_json or {}
    job_skills_data = job_analysis.get("skills", {})
    required_skills = job_skills_data.get("must_have", [])
    nice_to_have_skills = job_skills_data.get("nice_to_have", [])
    additional_skills = job_skills_data.get("additional_skills", [])

    # Include Tech Stack in required skills
    tech_stack = job_analysis.get("tech_stack", {})
    if tech_stack:
        for category in ["languages", "frameworks", "databases", "cloud", "tools", "business"]:
            items = tech_stack.get(category, [])
            if items:
                required_skills.extend(items)
        
        # Remove duplicates while preserving order
        required_skills = list(dict.fromkeys(required_skills))
    
    # Log job requirements once at the start
    logger.info("┌═════════════════════════════════════════════════════════════════┐")
    logger.info("│                    JOB REQUIREMENTS                             │")
    logger.info("├═════════════════════════════════════════════════════════════════┤")
    logger.info(f"│ Job Title: {job.title[:50]:<50} │")
    logger.info("├─────────────────────────────────────────────────────────────────┤")
    logger.info(f"│ Required Skills (Must Have): {len(required_skills)} skills                     │")
    for skill in required_skills:
        logger.info(f"│   ✓ {skill[:58]:<58} │")
    logger.info("├─────────────────────────────────────────────────────────────────┤")
    logger.info(f"│ Additional Skills (Manual): {len(additional_skills)} skills                     │")
    for skill in additional_skills:
        logger.info(f"│   + {skill[:58]:<58} │")
    logger.info("├─────────────────────────────────────────────────────────────────┤")
    logger.info(f"│ Nice to Have Skills: {len(nice_to_have_skills)} skills                          │")
    for skill in nice_to_have_skills:
        logger.info(f"│   ○ {skill[:58]:<58} │")
    logger.info("└═════════════════════════════════════════════════════════════════┘")
    logger.info("")
    
    scored_candidates = []
    
    verbose = logger.isEnabledFor(logging.DEBUG)

    # === OPTIMIZATION: Pre-calculate Job Title Embedding ONCE ===
    # Instead of doing this N times inside the loop
    job_title_embedding = await TitleMatcher.get_embedding_from_ollama_async(
        TitleMatcher.normalize_title(job.title)
    )

    # Helper function for parallel processing
    async def process_candidate_async(resume):
        resume_id = resume.id
        
        # Initialize variables to avoid UnboundLocalError
        title_score = 0.0
        title_score_100 = 0.0
        best_resume_title = "Unknown"
        match_source = None

        try:
            extraction = resume.extraction_json or {}
            
            # === Calculate Skills Score ===
            candidate_skills = _extract_skills(extraction)
            
            # Log all candidate skills BEFORE matching
            person = extraction.get("person", {})
            name = person.get("name", "Unknown")

            if verbose:
                logger.debug("Candidate resume_id=%s name=%s", resume_id, name)
            
            skills_result = skills_matcher.calculate_skills_match(
                candidate_skills=candidate_skills,
                required_skills=required_skills,
                nice_to_have_skills=nice_to_have_skills,
                additional_skills=additional_skills,
                candidate_text=resume.parsed_text
            )
            
            if verbose:
                logger.debug(
                    "Skills matched_required=%d missing_required=%d weighted_score=%.1f", 
                    len(skills_result.matched_required),
                    len(skills_result.missing_required),
                    skills_result.weighted_score,
                )
            
            # === Calculate Experience Score ===
            exp_result = experience_scorer.calculate_experience_match_detailed(
                candidate_extraction=extraction,
                job_analysis=job_analysis
            )
            exp_score = exp_result["score"]
            
            # === Calculate Employment Stability Score ===
            # Calculated for display but NOT used in scoring (Weight = 0%)
            stability_result = employment_stability_scorer.calculate_employment_stability(
                candidate_extraction=extraction,
                job_analysis=job_analysis
            )
            stability_score = stability_result.get("score", 0.0)
            
            # === OPTIMIZATION 2: THE FUNNEL (Fast Fail) ===
            # Calculate partial score of "cheap" components
            # Skills (45%) + Experience (25%) = 70% of total weight
            partial_score = (
                0.45 * (skills_result.weighted_score / 100) +
                0.25 * exp_score
            )
            
            # If partial score is very low (e.g. < 0.15), skip expensive Title Match
            # This means candidate has poor skills AND poor experience match
            # CHANGED: Disabled optimization to ensure we don't miss candidates with bad parsing but good titles
            SKIP_THRESHOLD = -1.0 # 0.15
            
            title_score = 0.0
            best_resume_title = ""
            match_source = None
            
            # Extract resume titles from work history (needed for display anyway)
            experiences = extraction.get("experience", [])
            resume_titles = []
            if experiences and isinstance(experiences, list):
                for exp in experiences:
                    if isinstance(exp, dict):
                        t = exp.get("title")
                        if t:
                            resume_titles.append(t)

            education = extraction.get("education", [])
            person = extraction.get("person", {})
            
            # 1. Get the "Frontend Profession" (what the user sees on the card)
            from app.services.resumes.ingestion_pipeline import _extract_profession
            primary_profession = _extract_profession(experiences, education, person)

            if partial_score >= SKIP_THRESHOLD:
                # === Calculate Title Match Score (EXPENSIVE) ===
                # Only run if candidate passed the initial filter
                
                # 2. Calculate match using the helper that prioritizes profession
                # NOW ASYNC!
                # CHANGED: We pass experience_list=experiences so the matcher can check HISTORY for management roles
                # BUT we rely on candidate_profession for the main semantic match.
                title_match_result = await title_matcher.calculate_title_match_with_history_async(
                    job_title=job.title,
                    experience_list=experiences, # <--- CHANGED: Pass full history again!
                    candidate_profession=primary_profession,
                    top_n=1,
                    job_embedding_vector=job_title_embedding # <--- PASS PRE-CALCULATED EMBEDDING
                )
                
                title_score_100 = title_match_result["best_score"]
                title_score = title_score_100 / 100.0  # Convert to 0-1 scale
                best_resume_title = title_match_result["best_matching_title"]
                match_source = title_match_result.get("best_source")
            else:
                # Fallback for skipped candidates
                best_resume_title = "Skipped (Low Match)"
                if verbose:
                    logger.debug(f"Skipping Title Match for {resume_id} (Partial Score: {partial_score:.2f})")
            
            # Add visual indicator if the matched title is the primary profession
            is_primary = match_source == "primary_profession"
            title_display = f"{best_resume_title}"
            if is_primary:
                title_display += " (Primary)"
            
            if not best_resume_title:
                best_resume_title = "No title"
                title_display = "No title"
            
            if verbose:
                logger.debug(
                    "Score components skills=%.1f title=%.1f exp=%.1f stability=%.1f",
                    skills_result.weighted_score,
                    title_score * 100,
                    exp_score * 100,
                    stability_score * 100,
                )
            
            # === Ensemble Weighted Score ===
            # Weights Updated:
            # - Title: 55% (Dominant)
            # - Experience: 25% (Very Important)
            # - Skills: 20% (Secondary)
            # - Stability: 0% (Removed)
            
            final_score = (
                0.55 * title_score +
                0.25 * exp_score +
                0.20 * (skills_result.weighted_score / 100)
            )
            
            # === RED FLAG: Poor Title Match ===
            # If title match is below 70%, apply a MASSIVE penalty.
            # This ensures "QA Automation" doesn't get matched for "QA Lead"
            RED_FLAG_TITLE_THRESHOLD = 0.75 # Was 0.70
            RED_FLAG_PENALTY = 0.10  # Was 0.30 (Now keeps only 10% of score instead of 30%)
            
            if title_score < RED_FLAG_TITLE_THRESHOLD:
                penalty_amount = final_score * (1.0 - RED_FLAG_PENALTY) # Calculate amount lost
                final_score = final_score * RED_FLAG_PENALTY
                logger.info("├─────────────────────────────────────────────────────────────────┤")
                logger.info(f"│ 🚩 RED FLAG: Poor title match (<{RED_FLAG_TITLE_THRESHOLD*100:.0f}%) - applying {(1-RED_FLAG_PENALTY)*100:.0f}% penalty   │")
                logger.info(f"│    Penalty: -{penalty_amount * 100:.1f}% → New score: {final_score * 100:.1f}%            │")
                logger.info("└─────────────────────────────────────────────────────────────────┘")
            
            logger.info(f"│ ⚡ FINAL SCORE: {final_score * 100:>6.1f}% │ (55%×Title + 25%×Exp + 20%×Skills) │")
            logger.info("")
            
            # Convert to 0-100 scale
            final_score_int = int(final_score * 100)
            
            # === Extract Additional Contact Info ===
            emails = person.get("emails", [])
            email = None
            if emails and isinstance(emails, list) and len(emails) > 0:
                email_obj = emails[0]
                email = email_obj.get("value") if isinstance(email_obj, dict) else email_obj
            
            phones = person.get("phones", [])
            phone = None
            if phones and isinstance(phones, list) and len(phones) > 0:
                phone_obj = phones[0]
                phone = phone_obj.get("value") if isinstance(phone_obj, dict) else phone_obj
            
            # Extract skill names for display
            skills_set = set()
            for skill in candidate_skills:
                if isinstance(skill, dict):
                    skill_name = skill.get("name")
                    if skill_name:
                        skills_set.add(skill_name.lower().strip())
                elif isinstance(skill, str):
                    skills_set.add(skill.lower().strip())
            
            # Get experience years
            exp_meta = extraction.get("experience_meta", {})
            rec_primary = exp_meta.get("recommended_primary_years", {})
            experience_years = rec_primary.get("tech")
            
            # Extract current/most recent job title
            # Use the sophisticated logic from _extract_profession (calculated earlier)
            # This handles sorting by date, filtering out projects/volunteer, and student status
            title = primary_profession
            
            # Fallback to naive extraction if primary_profession failed
            if not title:
                experiences = extraction.get("experience", [])
                if experiences and isinstance(experiences, list) and len(experiences) > 0:
                    # Get the first (most recent) experience entry
                    recent_exp = experiences[0]
                    if isinstance(recent_exp, dict):
                        title = recent_exp.get("title")
            
            # === Build Candidate Dict ===
            candidate_dict = {
                "resume_id": resume_id,
                "rag_score": final_score_int,  # Final ensemble score (legacy field name)
                "similarity": final_score,  # 0-1 scale for compatibility
                "breakdown": {
                    "skills": int(skills_result.weighted_score),
                    "experience": int(exp_score * 100),
                    "title": int(title_score * 100),
                    "stability": int(stability_score * 100)
                },
                "skills_detail": {
                    "required_match_rate": skills_result.required_match_rate,
                    "matched_required": [s["name"] for s in skills_result.matched_required],
                    "missing_required": skills_result.missing_required,
                    "matched_nice_to_have": [s["name"] for s in skills_result.matched_nice_to_have],
                },
                "experience_detail": {
                    "candidate_years": exp_result.get("candidate_years"),
                    "required_years": exp_result.get("required_years"),
                    "verdict": exp_result.get("verdict")
                },
                "stability_detail": stability_result,
                "title_detail": {
                    "job_title": job.title,
                    "resume_titles": resume_titles,
                    "best_match_score": title_score_100
                },
                "contact": {
                    "name": name,
                    "title": title,
                    "email": email,
                    "phone": phone,
                    "experience_years": experience_years,
                    "resume_url": f"/resumes/{resume_id}/file",
                    "file_name": Path(resume.file_path).name if resume.file_path else None,
                    "skills": skills_set,
                }
            }
            
            return candidate_dict
        
        except Exception as e:
            logger.error(f"Error scoring resume {resume_id}: {e}", exc_info=True)
            return None

    # Create tasks for all candidates
    tasks = [process_candidate_async(resume) for resume in resumes]
    
    # Run all tasks concurrently
    logger.info(f"Processing {len(tasks)} candidates in parallel...")
    results = await asyncio.gather(*tasks)
    
    # Filter out failures
    scored_candidates = [r for r in results if r is not None]
    
    # ===== STAGE 3: Sort and Return Top N =====
    scored_candidates.sort(key=lambda x: x["rag_score"], reverse=True)
    final_candidates = scored_candidates[:limit]
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("ENSEMBLE SCORING COMPLETE")
    logger.info(f"Total candidates scored: {len(scored_candidates)}")
    logger.info(f"Returning top {len(final_candidates)} candidates (requested: {limit})")
    logger.info("")
    
    if final_candidates:
        logger.info("Top 5 candidates:")
        for i, c in enumerate(final_candidates[:5], 1):
            b = c["breakdown"]
            logger.info(
                f"  {i}. Score={c['rag_score']} "
                f"(Skills:{b['skills']}% Exp:{b['experience']}% "
                f"Title:{b['title']}% Stability:{b['stability']}%)"
            )
    
    logger.info("=" * 80)
    
    return final_candidates
