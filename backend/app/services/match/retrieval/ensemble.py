"""Ensemble scorer combining RAG vector search, skills matching, experience scoring, and title matching into weighted final scores."""

from __future__ import annotations
import logging
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, Resume
from app.services.match.retrieval import rag_search, skills_matcher, experience_scorer, title_matcher, employment_stability_scorer
from app.services.match.retrieval.rag_search import cosine_similarity
from app.services.match.retrieval.title_matcher import TitleMatcher
from app.services.resumes.ingestion_pipeline import _extract_profession

logger = logging.getLogger("match.ensemble")

# Initialize title embedder once for efficiency
TITLE_EMBEDDER = None


def get_title_embedder():
    """Lazy-load title embedder on first use"""
    global TITLE_EMBEDDER
    if TITLE_EMBEDDER is None:
        TITLE_EMBEDDER = TitleMatcher.get_embedder()
    return TITLE_EMBEDDER


async def search_and_score_candidates(
    session: AsyncSession,
    job: Job,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Main ensemble scorer combining multiple algorithms.
    
    Pipeline:
    1. RAG vector search - semantic similarity across ALL candidates in DB
    2. Skills matching - deterministic weighted scoring
    3. Experience scoring - seniority and years match
    4. Title matching - role alignment
    5. Weighted combination - produce final ranked list
    
    Args:
        session: Database session
        job: Job to match candidates against
        limit: Number of top candidates to return after scoring ALL
        
    Returns:
        List of top N candidate dicts with scores, breakdown, and metadata
    """
    logger.info("=" * 80)
    logger.info(f"ENSEMBLE SCORING: Job '{job.title}' (id={job.id})")
    logger.info("=" * 80)
    logger.info(f"Will score ALL candidates and return top {limit}")
    logger.info("")
    
    # ===== STAGE 1: RAG Vector Search (Semantic Filtering) =====
    logger.info("Stage 1: RAG vector search - checking ALL candidates in DB...")
    
    job_embedding = await rag_search.get_job_embedding(session, job)
    if job_embedding is None:
        logger.error("No job embedding found - cannot perform matching")
        return []
    
    # Get ALL candidates from vector search (no limit, no threshold)
    rag_candidates = await rag_search.vector_search_candidates(
        session=session,
        job_embedding=job_embedding,
        limit=None,
        min_threshold=None
    )
    
    logger.info(f"RAG search found {len(rag_candidates)} candidates (ALL resumes in DB)")
    
    if not rag_candidates:
        logger.info("No candidates found in DB (no resumes with embeddings)")
        return []

    # ===== STAGE 1.5: Calculate Strong Chunk Coverage =====
    # This is the "Strongest" comparison requested: checking specific requirement coverage
    logger.info("Stage 1.5: Calculating detailed chunk coverage for candidates...")
    resume_ids = [rc["resume_id"] for rc in rag_candidates]
    
    # Calculate coverage scores (0.0 to 1.0) for all candidates at once
    coverage_scores = await rag_search.calculate_chunk_coverage(session, job.id, resume_ids)
    logger.info(f"Calculated coverage scores for {len(coverage_scores)} candidates")
    
    # ===== STAGE 2: Detailed Scoring for Each Candidate =====
    logger.info(f"Stage 2: Detailed scoring for ALL {len(rag_candidates)} candidates...")
    logger.info("")
    
    # Extract job requirements
    job_analysis = job.analysis_json or {}
    job_skills_data = job_analysis.get("skills", {})
    required_skills = job_skills_data.get("must_have", [])
    nice_to_have_skills = job_skills_data.get("nice_to_have", [])
    
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
    logger.info(f"│ Nice to Have Skills: {len(nice_to_have_skills)} skills                          │")
    for skill in nice_to_have_skills:
        logger.info(f"│   ○ {skill[:58]:<58} │")
    logger.info("└═════════════════════════════════════════════════════════════════┘")
    logger.info("")
    
    scored_candidates = []
    
    for idx, rag_result in enumerate(rag_candidates):
        resume_id = rag_result["resume_id"]
        simple_similarity = rag_result["avg_similarity"]
        
        # Get the strong coverage score (default to simple similarity if missing)
        coverage_score = coverage_scores.get(resume_id, 0.0)
        
        # Combined RAG Score: 70% Coverage (Strong) + 30% Global Similarity (Holistic)
        # This ensures candidates who match specific requirements get higher scores
        rag_similarity = (0.7 * coverage_score) + (0.3 * simple_similarity)
        
        try:
            # Load resume
            resume: Resume = await session.get(Resume, resume_id)
            if not resume:
                continue
            
            extraction = resume.extraction_json or {}
            
            # === Calculate Skills Score ===
            # Import the same extraction logic used in ingestion to ensure consistency
            from app.services.resumes.ingestion_pipeline import _extract_skills
            candidate_skills = _extract_skills(extraction)
            
            # Log all candidate skills BEFORE matching
            person = extraction.get("person", {})
            name = person.get("name", "Unknown")
            
            logger.info("┌═════════════════════════════════════════════════════════════════┐")
            logger.info(f"│ CANDIDATE: {name[:51]:<51} │")
            logger.info("├═════════════════════════════════════════════════════════════════┤")
            logger.info(f"│ All Candidate Skills ({len(candidate_skills)} total):                           │")
            
            # Group skills by weight (binary model: 1.0 = experience, 0.6 = general)
            skills_from_work = []
            skills_general = []
            
            for skill in candidate_skills:
                if isinstance(skill, dict):
                    skill_name = skill.get("name", "")
                    skill_weight = skill.get("weight", 0.6)
                    skill_source = skill.get("source", "unknown")
                    skill_category = skill.get("category", "N/A")
                    
                    # Binary classification by weight (handles both 1.0 and legacy values like 0.5)
                    if skill_weight >= 0.9:  # Consider anything >= 0.9 as experience (handles floating point)
                        skills_from_work.append((skill_name, skill_category))
                    else:
                        skills_general.append((skill_name, skill_category, skill_source))
            
            if skills_from_work:
                logger.info("│                                                                 │")
                logger.info(f"│ 💼 EXPERIENCE SKILLS ({len(skills_from_work)} skills, weight=1.0):              │")
                for skill_name, category in sorted(skills_from_work):
                    cat_display = (category or "N/A")[:10]
                    logger.info(f"│   • {skill_name[:45]:<45} [{cat_display:<10}] │")
            
            if skills_general:
                logger.info("│                                                                 │")
                logger.info(f"│ 📋 GENERAL SKILLS ({len(skills_general)} skills, weight=0.6):                   │")
                for skill_name, category, source in sorted(skills_general):
                    cat_display = (category or "N/A")[:10]
                    source_display = (source or "unknown")[:15]
                    logger.info(f"│   • {skill_name[:35]:<35} [{cat_display:<10}] ({source_display}) │")
            
            logger.info("└═════════════════════════════════════════════════════════════════┘")
            logger.info("")
            
            skills_result = skills_matcher.calculate_skills_match(
                candidate_skills=candidate_skills,
                required_skills=required_skills,
                nice_to_have_skills=nice_to_have_skills
            )
            
            # === Log Skills Matching Results ===
            logger.info("┌─────────────────────────────────────────────────────────────────┐")
            logger.info("│                    SKILLS MATCHING RESULTS                      │")
            logger.info("├─────────────────────────────────────────────────────────────────┤")
            
            # Matched Required Skills
            logger.info(f"│ ✅ Matched Required ({len(skills_result.matched_required)}/{len(required_skills)}):                         │")
            for matched in skills_result.matched_required:
                skill_name = matched.get("name", "")
                weight = matched.get("weight", 0.6)
                # Display emoji based on weight (binary model)
                source_emoji = "💼" if weight == 1.0 else "📋"
                source_label = "EXP" if weight == 1.0 else "GEN"
                logger.info(f"│   {source_emoji} {skill_name[:35]:<35} [{source_label}|w={weight:.1f}] │")
            
            if not skills_result.matched_required:
                logger.info("│   (none)                                                        │")
            
            # Missing Required Skills
            logger.info("├─────────────────────────────────────────────────────────────────┤")
            logger.info(f"│ ❌ Missing Required ({len(skills_result.missing_required)}):                              │")
            for missing in skills_result.missing_required:
                logger.info(f"│   ✗ {missing[:58]:<58} │")
            
            if not skills_result.missing_required:
                logger.info("│   (none - perfect match!)                                      │")
            
            # Matched Nice-to-Have Skills
            if nice_to_have_skills:
                logger.info("├─────────────────────────────────────────────────────────────────┤")
                logger.info(f"│ ⭐ Matched Nice-to-Have ({len(skills_result.matched_nice_to_have)}/{len(nice_to_have_skills)}):              │")
                for matched in skills_result.matched_nice_to_have:
                    skill_name = matched.get("name", "")
                    weight = matched.get("weight", 0.6)
                    # Display emoji based on weight (binary model)
                    source_emoji = "💼" if weight == 1.0 else "📋"
                    source_label = "EXP" if weight == 1.0 else "GEN"
                    logger.info(f"│   {source_emoji} {skill_name[:35]:<35} [{source_label}|w={weight:.1f}] │")
                
                if not skills_result.matched_nice_to_have:
                    logger.info("│   (none)                                                        │")
            
            # Skills Score Summary
            logger.info("├─────────────────────────────────────────────────────────────────┤")
            logger.info("│                    SKILLS SCORE BREAKDOWN                       │")
            logger.info("├─────────────────────────────────────────────────────────────────┤")
            
            # Count matched skills by weight (binary model)
            exp_count = sum(1 for m in skills_result.matched_required if m.get("weight") == 1.0)
            gen_count = len(skills_result.matched_required) - exp_count
            
            exp_points = exp_count * 1.0
            gen_points = gen_count * 0.6
            total_points = exp_points + gen_points
            max_points = len(required_skills) * 1.0
            
            logger.info(f"│ 💼 Experience Skills: {exp_count} × 1.0 = {exp_points:.1f} pts              │")
            logger.info(f"│ 📋 General Skills:    {gen_count} × 0.6 = {gen_points:.1f} pts              │")
            logger.info(f"│ ────────────────────────────────────────────────────────────    │")
            logger.info(f"│ Weighted Score: {total_points:.1f}/{max_points:.1f} = {skills_result.weighted_score:.1f}%    │")
            
            logger.info("└─────────────────────────────────────────────────────────────────┘")
            logger.info("")
            
            # === Calculate Experience Score ===
            exp_result = experience_scorer.calculate_experience_match_detailed(
                candidate_extraction=extraction,
                job_analysis=job_analysis
            )
            exp_score = exp_result["score"]
            
            # === Calculate Employment Stability Score ===
            stability_result = employment_stability_scorer.calculate_employment_stability(
                candidate_extraction=extraction,
                job_analysis=job_analysis
            )
            stability_score = stability_result["score"]
            
            # === Calculate Title Match Score (Semantic Similarity) ===
            # Extract resume titles from work history
            experiences = extraction.get("experience", [])
            
            # Extract titles for display
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
            primary_profession = _extract_profession(experiences, education, person)
            
            # 2. Calculate match using the helper that prioritizes profession
            title_match_result = title_matcher.calculate_title_match_with_history(
                job_title=job.title,
                experience_list=experiences,
                candidate_profession=primary_profession,
                top_n=3
            )
            
            title_score_100 = title_match_result["best_score"]
            title_score = title_score_100 / 100.0  # Convert to 0-1 scale
            
            # Best matching title for logging
            best_resume_title = title_match_result["best_matching_title"]
            match_source = title_match_result.get("best_source")
            
            # Add visual indicator if the matched title is the primary profession
            is_primary = match_source == "primary_profession"
            title_display = f"{best_resume_title}"
            if is_primary:
                title_display += " (Primary)"
            
            if not best_resume_title:
                best_resume_title = "No title"
                title_display = "No title"
            
            # === Log Individual Scores ===
            logger.info("┌─────────────────────────────────────────────────────────────────┐")
            logger.info(f"│                    SCORING SUMMARY                              │")
            logger.info("├─────────────────────────────────────────────────────────────────┤")
            logger.info(f"│ 🎯 Skills:      {skills_result.weighted_score:>6.1f}% │ Required: {skills_result.required_match_rate:>3.0f}% │")
            logger.info(f"│ 💼 Experience:  {exp_score * 100:>6.1f}% │ {exp_result.get('verdict', 'N/A')[:22]:<22} │")
            logger.info(f"│ 🔍 RAG:         {rag_similarity * 100:>6.1f}% │ Cov:{coverage_score*100:.0f}% Sim:{simple_similarity*100:.0f}% │")
            logger.info(f"│ 👔 Title:       {title_score * 100:>6.1f}% │ '{title_display[:20]}'")
            logger.info(f"│ 🏢 Stability:   {stability_score * 100:>6.1f}% │ {stability_result.get('verdict', 'N/A')[:22]:<22} │")
            logger.info("└─────────────────────────────────────────────────────────────────┘")
            
            # === Ensemble Weighted Score ===
            # Weights (tunable):
            # - Skills: 40% (Technical match)
            # - Title: 25% (Role alignment)
            # - Experience: 20% (Seniority)
            # - RAG: 10% (Semantic Requirement Coverage)
            # - Stability: 5% (Employment stability)
            
            final_score = (
                0.40 * (skills_result.weighted_score / 100) +
                0.25 * title_score +
                0.20 * exp_score +
                0.10 * rag_similarity +
                0.05 * stability_score
            )
            
            # === RED FLAG: Poor Title Match ===
            # If title match is below 50%, apply a significant penalty
            # This indicates the candidate is likely not suitable for the role
            RED_FLAG_TITLE_THRESHOLD = 0.50  # 50%
            RED_FLAG_PENALTY = 0.40  # Reduce score by 40% (multiplicative)
            
            if title_score < RED_FLAG_TITLE_THRESHOLD:
                penalty_amount = final_score * RED_FLAG_PENALTY
                final_score = final_score * (1.0 - RED_FLAG_PENALTY)
                logger.info("├─────────────────────────────────────────────────────────────────┤")
                logger.info(f"│ 🚩 RED FLAG: Poor title match (<50%) - applying {RED_FLAG_PENALTY*100:.0f}% penalty   │")
                logger.info(f"│    Penalty: -{penalty_amount * 100:.1f}% → New score: {final_score * 100:.1f}%            │")
                logger.info("└─────────────────────────────────────────────────────────────────┘")
            
            logger.info(f"│ ⚡ FINAL SCORE: {final_score * 100:>6.1f}% │ (40%×Skills + 25%×Title + 20%×Exp + 10%×RAG + 5%×Stability) │")
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
            title = None
            experiences = extraction.get("experience", [])
            if experiences and isinstance(experiences, list) and len(experiences) > 0:
                # Get the first (most recent) experience entry
                recent_exp = experiences[0]
                if isinstance(recent_exp, dict):
                    title = recent_exp.get("title")
            
            # === Build Candidate Dict ===
            candidate_dict = {
                "resume_id": resume_id,
                "rag_score": final_score_int,  # Final ensemble score
                "similarity": final_score,  # 0-1 scale for compatibility
                "breakdown": {
                    "skills": int(skills_result.weighted_score),
                    "experience": int(exp_score * 100),
                    "rag_similarity": int(rag_similarity * 100),
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
                "stability_detail": {
                    "score": stability_result.get("score"),
                    "average_tenure": stability_result.get("average_tenure_years"),
                    "expected_tenure": stability_result.get("expected_tenure_years"),
                    "total_jobs": stability_result.get("total_jobs"),
                    "short_stints": stability_result.get("short_stints"),
                    "long_tenures": stability_result.get("long_tenures"),
                    "verdict": stability_result.get("verdict"),
                    "concerns": stability_result.get("concerns", []),
                    "strengths": stability_result.get("strengths", [])
                },
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
                    "skills": skills_set,
                }
            }
            
            scored_candidates.append(candidate_dict)
            
            # Log progress every 10 candidates
            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(rag_candidates)} candidates...")
        
        except Exception as e:
            logger.error(f"Error scoring resume {resume_id}: {e}", exc_info=True)
            continue
    
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
                f"RAG:{b['rag_similarity']}% Title:{b['title']}% Stability:{b['stability']}%)"
            )
    
    logger.info("=" * 80)
    
    return final_candidates
