# Ensemble scorer combining RAG, skills matching, and future algorithms.
# Main entry point for candidate retrieval and scoring.

from __future__ import annotations
import logging
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, Resume
from app.services.match.retrieval import rag_search, skills_matcher, experience_scorer, title_matcher
from app.services.match.retrieval.rag_search import cosine_similarity
from app.services.match.config import CFG

logger = logging.getLogger("match.ensemble")


async def search_and_score_candidates(
    session: AsyncSession,
    job: Job,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Main ensemble scorer combining multiple algorithms.
    
    Pipeline:
    1. RAG vector search - fast semantic filtering (top 200)
    2. Skills matching - deterministic weighted scoring
    3. Experience scoring - (future enhancement)
    4. Weighted combination - produce final ranked list
    
    Args:
        session: Database session
        job: Job to match candidates against
        limit: Number of top candidates to return
        
    Returns:
        List of candidate dicts with scores, breakdown, and metadata
    """
    logger.info("=" * 80)
    logger.info(f"ENSEMBLE SCORING: Job '{job.title}' (id={job.id})")
    logger.info("=" * 80)
    
    # ===== STAGE 1: RAG Vector Search (Semantic Filtering) =====
    logger.info("Stage 1: RAG vector search for semantic filtering...")
    
    job_embedding = await rag_search.get_job_embedding(session, job)
    if job_embedding is None:
        logger.error("No job embedding found - cannot perform matching")
        return []
    
    # Get ~200 candidates from vector search
    rag_candidates = await rag_search.vector_search_candidates(
        session=session,
        job_embedding=job_embedding,
        limit=200,
        min_threshold=CFG.min_cosine_for_evidence
    )
    
    logger.info(f"RAG search found {len(rag_candidates)} candidates")
    
    if not rag_candidates:
        logger.info("No candidates passed RAG threshold")
        return []
    
    # ===== STAGE 2: Detailed Scoring for Each Candidate =====
    logger.info(f"Stage 2: Detailed scoring for {len(rag_candidates)} candidates...")
    
    # Extract job requirements
    job_analysis = job.analysis_json or {}
    job_skills_data = job_analysis.get("skills", {})
    required_skills = job_skills_data.get("must_have", [])
    nice_to_have_skills = job_skills_data.get("nice_to_have", [])
    
    scored_candidates = []
    
    for idx, rag_result in enumerate(rag_candidates):
        resume_id = rag_result["resume_id"]
        rag_similarity = rag_result["avg_similarity"]
        
        try:
            # Load resume
            resume: Resume = await session.get(Resume, resume_id)
            if not resume:
                continue
            
            extraction = resume.extraction_json or {}
            
            # === Calculate Skills Score ===
            candidate_skills = extraction.get("skills", [])
            
            skills_result = skills_matcher.calculate_skills_match(
                candidate_skills=candidate_skills,
                required_skills=required_skills,
                nice_to_have_skills=nice_to_have_skills
            )
            
            # === Calculate Experience Score ===
            exp_result = experience_scorer.calculate_experience_match_detailed(
                candidate_extraction=extraction,
                job_analysis=job_analysis
            )
            exp_score = exp_result["score"]
            
            # === Calculate Title Match Score ===
            title_result = title_matcher.calculate_title_match_from_extraction(
                job_analysis=job_analysis,
                resume_extraction=extraction
            )
            title_score = title_result["score"]
            
            # === Log Individual Scores ===
            logger.info("┌─────────────────────────────────────────────────────────────────┐")
            logger.info(f"│ Candidate: {resume.full_name[:45]:<45} │")
            logger.info("├─────────────────────────────────────────────────────────────────┤")
            logger.info(f"│ 🎯 Skills:      {skills_result.weighted_score:>6.1f}% │ Required: {skills_result.required_match_rate:>3.0f}% │")
            logger.info(f"│ 💼 Experience:  {exp_score * 100:>6.1f}% │ {exp_result.get('verdict', 'N/A')[:22]:<22} │")
            logger.info(f"│ 🔍 RAG:         {rag_similarity * 100:>6.1f}% │ Vector similarity        │")
            logger.info(f"│ 👔 Title:       {title_score * 100:>6.1f}% │ Jaccard similarity       │")
            logger.info("└─────────────────────────────────────────────────────────────────┘")
            
            # === Ensemble Weighted Score ===
            # Weights (tunable):
            # - Skills: 40% (most important for technical roles)
            # - Experience: 25% (seniority match with proximity preference)
            # - RAG: 20% (semantic understanding)
            # - Title: 15% (role alignment)
            
            final_score = (
                0.40 * (skills_result.weighted_score / 100) +
                0.25 * exp_score +
                0.20 * rag_similarity +
                0.15 * title_score
            )
            
            logger.info(f"│ ⚡ FINAL SCORE: {final_score * 100:>6.1f}% │ (40%×Skills + 25%×Exp + 20%×RAG + 15%×Title) │")
            logger.info("")
            
            # Convert to 0-100 scale
            final_score_int = int(final_score * 100)
            
            # === Extract Contact Info ===
            person = extraction.get("person", {})
            
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
            
            name = person.get("name")
            
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
            
            # === Build Candidate Dict ===
            candidate_dict = {
                "resume_id": resume_id,
                "rag_score": final_score_int,  # Final ensemble score
                "similarity": final_score,  # 0-1 scale for compatibility
                "breakdown": {
                    "skills": int(skills_result.weighted_score),
                    "experience": int(exp_score * 100),
                    "rag_similarity": int(rag_similarity * 100),
                    "title": int(title_score * 100)
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
                "title_detail": {
                    "job_title": title_result.get("job_title"),
                    "resume_title": title_result.get("resume_title"),
                    "matched_words": title_result.get("matched_words", [])
                },
                "contact": {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "experience_years": experience_years,
                    "resume_url": f"/resumes/{resume_id}/file",
                    "skills": skills_set,
                }
            }
            
            scored_candidates.append(candidate_dict)
            
            # Log progress
            if (idx + 1) % 50 == 0:
                logger.info(f"Processed {idx + 1}/{len(rag_candidates)} candidates...")
        
        except Exception as e:
            logger.error(f"Error scoring resume {resume_id}: {e}", exc_info=True)
            continue
    
    # ===== STAGE 3: Sort and Return Top N =====
    scored_candidates.sort(key=lambda x: x["rag_score"], reverse=True)
    final_candidates = scored_candidates[:limit]
    
    logger.info("=" * 80)
    logger.info("ENSEMBLE SCORING COMPLETE")
    logger.info(f"Returning {len(final_candidates)} top candidates")
    
    if final_candidates:
        logger.info("Top 5 candidates:")
        for i, c in enumerate(final_candidates[:5], 1):
            b = c["breakdown"]
            logger.info(
                f"  {i}. Score={c['rag_score']} "
                f"(Skills:{b['skills']}% Exp:{b['experience']}% "
                f"RAG:{b['rag_similarity']}% Title:{b['title']}%)"
            )
    
    logger.info("=" * 80)
    
    return final_candidates
