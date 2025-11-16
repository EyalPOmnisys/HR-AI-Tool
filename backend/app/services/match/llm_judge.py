# app/services/match/llm_judge.py
"""
LLM Judge - Performs deep AI-powered evaluation of top candidates.
Loads full resumes, analyzes fit against job requirements, and provides detailed scoring and recommendations.
"""
from __future__ import annotations
import logging
from typing import List, Dict, Any
from uuid import UUID
from openai import AsyncOpenAI
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Job, Resume, ResumeChunk
from app.core.config import settings
from app.services.common.llm_client import load_prompt

# Load evaluation prompt from centralized location
CANDIDATE_EVALUATION_PROMPT = load_prompt("match/candidate_evaluation.prompt.txt")

client = AsyncOpenAI()
logger = logging.getLogger("match.llm_judge")


class LLMJudge:
    """Performs deep LLM-based evaluation of candidates."""
    
    @staticmethod
    async def evaluate_candidates(
        session: AsyncSession,
        job: Job,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform deep LLM evaluation on top candidates.
        
        Args:
            session: Database session
            job: Job to evaluate against
            candidates: List of candidate dicts from RAG matching
            
        Returns:
            List of candidates with LLM scores and analysis
        """
        logger.info("=" * 80)
        logger.info("LLM DEEP EVALUATION")
        logger.info("=" * 80)
        logger.info("Evaluating %d candidates for job '%s'", len(candidates), job.title)
        
        # Step 1: Load full resume data for each candidate
        candidates_with_resumes = await LLMJudge._load_full_resumes(session, candidates)
        
        # Step 2: Extract job requirements
        job_requirements = LLMJudge._extract_job_requirements(job)
        
        logger.info("")
        logger.info("JOB REQUIREMENTS (FULL CONTEXT):")
        logger.info("  Title: %s", job_requirements["title"])
        logger.info("  Description length: %d chars", len(job_requirements["description"]))
        logger.info("  Must-Have Skills: %s", ", ".join(job_requirements.get("must_have_skills", [])))
        if job_requirements.get("nice_to_have_skills"):
            logger.info("  Nice-to-Have Skills: %s", ", ".join(job_requirements["nice_to_have_skills"]))
        logger.info("  Min Experience: %s years", job_requirements.get("min_years", "N/A"))
        logger.info("")
        
        # Step 3: Call LLM for evaluation
        llm_results = await LLMJudge._call_llm(job_requirements, candidates_with_resumes)
        
        # Step 4: Combine RAG + LLM scores
        final_results = LLMJudge._combine_scores(candidates, llm_results)
        
        logger.info("=" * 80)
        logger.info("LLM EVALUATION COMPLETE")
        logger.info("Top 5 final scores: %s", [r["final_score"] for r in final_results[:5]])
        logger.info("=" * 80)
        
        return final_results
    
    @staticmethod
    async def _load_full_resumes(
        session: AsyncSession,
        candidates: List[Dict]
    ) -> List[Dict]:
        """Load complete resume data for candidates."""
        logger.info("Loading full resume data for %d candidates...", len(candidates))
        
        enriched = []
        for candidate in candidates:
            resume_id = candidate["resume_id"]
            resume: Resume = await session.get(Resume, resume_id)
            
            if not resume:
                logger.warning("Resume %s not found", resume_id)
                continue
            
            # Get full resume text
            full_text = ""
            extraction = resume.extraction_json or {}
            
            if extraction:
                # Build structured text from extraction
                parts = []
                
                # Personal info
                person = extraction.get("person", {})
                if person:
                    parts.append(f"Name: {person.get('name', 'N/A')}")
                
                # Summary
                summary = extraction.get("summary")
                if summary:
                    parts.append(f"\nSUMMARY:\n{summary}")
                
                # Experience
                experiences = extraction.get("experience", [])
                if experiences:
                    parts.append("\n\nWORK EXPERIENCE:")
                    for exp in experiences:
                        if isinstance(exp, dict):
                            company = exp.get("company", "Unknown")
                            title = exp.get("title", "Unknown")
                            duration = exp.get("duration", "")
                            description = exp.get("description", "")
                            parts.append(f"\n- {title} at {company} ({duration})")
                            if description:
                                parts.append(f"  {description}")
                
                # Skills
                skills = extraction.get("skills", [])
                if skills:
                    skill_names = []
                    for skill in skills:
                        if isinstance(skill, dict):
                            skill_names.append(skill.get("name", ""))
                        elif isinstance(skill, str):
                            skill_names.append(skill)
                    parts.append(f"\n\nSKILLS:\n{', '.join(skill_names)}")
                
                # Education
                education = extraction.get("education", [])
                if education:
                    parts.append("\n\nEDUCATION:")
                    for edu in education:
                        if isinstance(edu, dict):
                            degree = edu.get("degree", "")
                            institution = edu.get("institution", "")
                            parts.append(f"\n- {degree} from {institution}")
                
                # Projects
                projects = extraction.get("projects", [])
                if projects:
                    parts.append("\n\nPROJECTS:")
                    for proj in projects:
                        if isinstance(proj, dict):
                            name = proj.get("name", "")
                            description = proj.get("description", "")
                            parts.append(f"\n- {name}: {description}")
                
                full_text = "\n".join(parts)
            
            # If no extraction, fall back to chunks
            if not full_text:
                logger.info("No extraction for resume %s, loading chunks...", str(resume_id)[:8])
                chunks = await session.execute(
                    select(ResumeChunk)
                    .where(ResumeChunk.resume_id == resume_id)
                    .order_by(ResumeChunk.section, ResumeChunk.chunk_index)
                )
                
                chunk_texts = []
                for chunk in chunks.scalars().all():
                    chunk_texts.append(f"[{chunk.section.upper()}]\n{chunk.text}")
                
                full_text = "\n\n".join(chunk_texts)
            
            # Limit text size (max ~8000 chars for token limits)
            if len(full_text) > 8000:
                full_text = full_text[:8000] + "\n\n[... truncated for length ...]"
            
            enriched.append({
                **candidate,
                "full_resume": full_text,
            })
            
            logger.info("  Loaded resume for %s (%d chars)", 
                       candidate["contact"].get("name", "Unknown"),
                       len(full_text))
        
        return enriched
    
    @staticmethod
    def _extract_job_requirements(job: Job) -> Dict:
        """Extract structured requirements from job with FULL description."""
        analysis = job.analysis_json or {}
        
        # Extract must-have skills
        skills_dict = analysis.get("skills", {})
        must_have = []
        nice_to_have = []
        if isinstance(skills_dict, dict):
            must_have = skills_dict.get("must_have", [])
            nice_to_have = skills_dict.get("nice_to_have", [])
        
        # Extract tech stack
        tech_stack = analysis.get("tech_stack", {})
        tech_list = []
        if isinstance(tech_stack, dict):
            languages = tech_stack.get("languages", [])
            frameworks = tech_stack.get("frameworks", [])
            databases = tech_stack.get("databases", [])
            tools = tech_stack.get("tools", [])
            tech_list = {
                "languages": languages,
                "frameworks": frameworks,
                "databases": databases,
                "tools": tools,
            }
        
        # Extract experience requirements
        experience = analysis.get("experience", {})
        min_years = 0
        if isinstance(experience, dict):
            min_years = experience.get("years_min") or experience.get("min_years") or 0
            if isinstance(min_years, str):
                import re
                match = re.search(r'(\d+)', min_years)
                if match:
                    min_years = int(match.group(1))
        
        # Extract responsibilities
        responsibilities = analysis.get("responsibilities", [])
        
        # Extract qualifications
        qualifications = analysis.get("qualifications", {})
        
        return {
            "title": job.title,
            "description": job.job_description or "",  # FULL description
            "free_text": job.free_text or "",  # Additional context
            "must_have_skills": must_have,
            "nice_to_have_skills": nice_to_have,
            "tech_stack": tech_list,
            "min_years": min_years,
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "full_analysis": analysis,  # Complete AI analysis for context
        }
    
    @staticmethod
    async def _call_llm(
        job_requirements: Dict,
        candidates: List[Dict]
    ) -> List[Dict]:
        """Call LLM to evaluate candidates."""
        logger.info("Calling OpenAI API for deep evaluation...")
        
        # Use centralized prompt
        system_prompt = CANDIDATE_EVALUATION_PROMPT

        # Build user prompt
        user_prompt = {
            "job": job_requirements,
            "candidates": [
                {
                    "resume_id": str(c["resume_id"]),
                    "rag_score": c["rag_score"],
                    "candidate_name": c["contact"].get("name", "Unknown"),
                    "contact_email": c["contact"].get("email"),
                    # CRITICAL: Preserve 0 as real value - it means junior/entry-level
                    "experience_years": c["contact"].get("experience_years") if c["contact"].get("experience_years") is not None else "unknown",
                    "skills": sorted(list(c["contact"].get("skills", []))),
                    "full_resume": c["full_resume"],
                }
                for c in candidates
            ]
        }
        
        # Log candidate experience years for debugging
        logger.info("Candidates being evaluated:")
        for i, cand in enumerate(user_prompt["candidates"], 1):
            exp_years = cand.get("experience_years")
            exp_str = f"{exp_years} years" if isinstance(exp_years, (int, float)) else str(exp_years)
            logger.info("  %d. %s - Experience: %s", i, cand.get("candidate_name", "Unknown"), exp_str)
        
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False, indent=2)},
                ]
            )
            
            content = response.choices[0].message.content
            logger.info("LLM response received (%d tokens)", 
                       getattr(response.usage, "total_tokens", 0))
            
            parsed = json.loads(content)
            evaluations = parsed.get("evaluations", [])
            
            logger.info("LLM evaluated %d candidates", len(evaluations))
            
            # Log summary
            for ev in evaluations:
                logger.info("  %s: Score=%d, Verdict=%s",
                           ev.get("resume_id", "unknown")[:8],
                           ev.get("llm_score", 0),
                           ev.get("verdict", "unknown"))
            
            return evaluations
            
        except Exception as e:
            logger.error("LLM call failed: %s", str(e), exc_info=True)
            return []
    
    @staticmethod
    def _combine_scores(
        rag_candidates: List[Dict],
        llm_evaluations: List[Dict]
    ) -> List[Dict]:
        """Use LLM score as the final score (RAG only used for initial filtering)."""
        logger.info("Applying LLM scores as final scores...")
        
        # Create lookup map
        llm_map = {ev["resume_id"]: ev for ev in llm_evaluations}
        
        results = []
        for candidate in rag_candidates:
            resume_id = str(candidate["resume_id"])
            rag_score = candidate["rag_score"]
            
            # Get LLM evaluation
            llm_ev = llm_map.get(resume_id)
            
            if llm_ev:
                llm_score = llm_ev.get("llm_score", 0)
                verdict = llm_ev.get("verdict", "unknown")
                
                # FINAL SCORE = LLM SCORE (no averaging with RAG)
                # RAG is only used for initial candidate filtering
                final_score = llm_score
                
                results.append({
                    **candidate,
                    "llm_score": llm_score,
                    "llm_verdict": verdict,
                    "llm_strengths": llm_ev.get("strengths", ""),
                    "llm_concerns": llm_ev.get("concerns", ""),
                    "llm_recommendation": llm_ev.get("recommendation", ""),
                    "final_score": final_score,
                })
                
                logger.info("  %s: RAG=%d (filter), LLM=%d → Final=%d (%s)",
                           candidate["contact"].get("name", "Unknown")[:20],
                           rag_score, llm_score, final_score, verdict)
            else:
                # No LLM evaluation - use RAG score as fallback
                logger.warning("  %s: No LLM evaluation, using RAG score as fallback",
                             candidate["contact"].get("name", "Unknown"))
                results.append({
                    **candidate,
                    "llm_score": 0,
                    "llm_verdict": "not_evaluated",
                    "final_score": rag_score,
                })
        
        # Sort by final score
        results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return results
