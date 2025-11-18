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
from app.services.match.retrieval.title_matcher import TitleMatcher

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
    
    # ===== STAGE 2: Detailed Scoring for Each Candidate =====
    logger.info(f"Stage 2: Detailed scoring for ALL {len(rag_candidates)} candidates...")
    logger.info("")
    
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
            
            # === Calculate Title Match Score (Semantic Similarity) ===
            # Extract resume titles from work history
            experiences = extraction.get("experience", [])
            resume_titles = []
            for exp in experiences[:3]:  # Check top 3 recent roles
                if isinstance(exp, dict):
                    exp_title = exp.get("title")
                    if exp_title:
                        resume_titles.append(exp_title)
            
            # Use semantic embeddings for title matching
            embedder = get_title_embedder()
            title_score_100 = TitleMatcher.compute_title_match(
                job_title=job.title,
                resume_titles=resume_titles,
                embedder=embedder
            )
            title_score = title_score_100 / 100.0  # Convert to 0-1 scale
            
            # === Extract Contact Info First (for logging) ===
            person = extraction.get("person", {})
            name = person.get("name", "Unknown")
            
            # Best matching title for logging
            best_resume_title = resume_titles[0] if resume_titles else "No title"
            
            # === Log Individual Scores ===
            logger.info("┌─────────────────────────────────────────────────────────────────┐")
            logger.info(f"│ Candidate: {name[:45]:<45} │")
            logger.info("├─────────────────────────────────────────────────────────────────┤")
            logger.info(f"│ 🎯 Skills:      {skills_result.weighted_score:>6.1f}% │ Required: {skills_result.required_match_rate:>3.0f}% │")
            logger.info(f"│ 💼 Experience:  {exp_score * 100:>6.1f}% │ {exp_result.get('verdict', 'N/A')[:22]:<22} │")
            logger.info(f"│ 🔍 RAG:         {rag_similarity * 100:>6.1f}% │ Vector similarity        │")
            logger.info(f"│ 👔 Title:       {title_score * 100:>6.1f}% │ '{best_resume_title[:20]}'")
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
                    "job_title": job.title,
                    "resume_titles": resume_titles,
                    "best_match_score": title_score_100
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
                f"RAG:{b['rag_similarity']}% Title:{b['title']}%)"
            )
    
    logger.info("=" * 80)
    
    return final_candidates
