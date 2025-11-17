# Qualitative candidate evaluation that adds human-like insights to algorithmic scores.
# Receives pre-computed scores from ensemble and provides strengths, concerns, and recommendations.

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
        """Add qualitative analysis to algorithmically-scored candidates."""
        logger.info("=" * 80)
        logger.info("LLM QUALITATIVE ANALYSIS")
        logger.info("=" * 80)
        logger.info("Analyzing %d candidates for '%s'", len(candidates), job.title)
        
        candidates_with_resumes = await LLMJudge._load_full_resumes(session, candidates)
        job_requirements = LLMJudge._extract_job_requirements(job)
        
        logger.info("Job: %s (Min Experience: %s years)", 
                   job_requirements["title"], 
                   job_requirements.get("min_years", "N/A"))
        logger.info("Must-Have Skills: %s", ", ".join(job_requirements.get("must_have_skills", [])[:5]))
        logger.info("")
        
        llm_analyses = await LLMJudge._call_llm_batched(job_requirements, candidates_with_resumes)
        final_results = LLMJudge._add_qualitative_analysis(candidates, llm_analyses)
        
        logger.info("=" * 80)
        logger.info("ANALYSIS COMPLETE - Top 5 Scores: %s", [r["final_score"] for r in final_results[:5]])
        logger.info("=" * 80)
        
        return final_results
    
    @staticmethod
    async def _load_full_resumes(
        session: AsyncSession,
        candidates: List[Dict]
    ) -> List[Dict]:
        """Load full resume text for qualitative analysis."""
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
        """Extract job requirements for LLM context."""
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
    async def _call_llm_batched(
        job_requirements: Dict,
        candidates: List[Dict]
    ) -> List[Dict]:
        """Call LLM for qualitative analysis in batches of 5."""
        BATCH_SIZE = 5
        total_candidates = len(candidates)
        num_batches = (total_candidates + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
        
        logger.info("Calling OpenAI API for deep evaluation...")
        logger.info("Total candidates: %d, Batch size: %d, Number of API calls: %d", 
                   total_candidates, BATCH_SIZE, num_batches)
        
        all_evaluations = []
        
        for batch_num in range(num_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, total_candidates)
            batch_candidates = candidates[start_idx:end_idx]
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("BATCH %d/%d: Evaluating candidates %d-%d", 
                       batch_num + 1, num_batches, start_idx + 1, end_idx)
            logger.info("=" * 60)
            
            # Evaluate this batch
            batch_evaluations = await LLMJudge._call_llm_single_batch(
                job_requirements, 
                batch_candidates,
                batch_num + 1
            )
            
            all_evaluations.extend(batch_evaluations)
        
        logger.info("")
        logger.info("All batches completed. Total evaluations: %d", len(all_evaluations))
        
        return all_evaluations
    
    @staticmethod
    async def _call_llm_single_batch(
        job_requirements: Dict,
        candidates: List[Dict],
        batch_num: int
    ) -> List[Dict]:
        """Call LLM for qualitative analysis of a batch."""
        system_prompt = CANDIDATE_EVALUATION_PROMPT

        user_prompt = {
            "job": job_requirements,
            "candidates": [
                {
                    "resume_id": str(c["resume_id"]),
                    "candidate_name": c["contact"].get("name", "Unknown"),
                    "contact_email": c["contact"].get("email"),
                    "experience_years": c["contact"].get("experience_years") if c["contact"].get("experience_years") is not None else "unknown",
                    "skills": sorted(list(c["contact"].get("skills", []))),
                    "full_resume": c["full_resume"],
                    "algorithmic_scores": {
                        "overall": int(c.get("rag_score", 0)),
                        "skills": c.get("breakdown", {}).get("skills", 0),
                        "experience": c.get("breakdown", {}).get("experience", 0),
                        "title": c.get("breakdown", {}).get("title", 0),
                        "rag_similarity": c.get("breakdown", {}).get("rag_similarity", 0),
                    },
                    "skills_detail": c.get("skills_detail", {}),
                    "experience_detail": c.get("experience_detail", {}),
                    "title_detail": c.get("title_detail", {}),
                }
                for c in candidates
            ]
        }
        
        # Log candidate experience years for debugging
        logger.info("Candidates in this batch:")
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
            logger.info("Batch %d response received (%d tokens)", 
                       batch_num,
                       getattr(response.usage, "total_tokens", 0))
            
            parsed = json.loads(content)
            evaluations = parsed.get("evaluations", [])
            
            logger.info("Batch %d evaluated %d candidates", batch_num, len(evaluations))
            
            # Log summary
            for ev in evaluations:
                logger.info("  %s: Score=%d, Verdict=%s",
                           ev.get("resume_id", "unknown")[:8],
                           ev.get("llm_score", 0),
                           ev.get("verdict", "unknown"))
            
            return evaluations
            
        except Exception as e:
            logger.error("Batch %d LLM call failed: %s", batch_num, str(e), exc_info=True)
            return []
    
    @staticmethod
    def _add_qualitative_analysis(
        candidates: List[Dict],
        llm_analyses: List[Dict]
    ) -> List[Dict]:
        """Add LLM qualitative insights while keeping algorithmic scores."""
        logger.info("Adding qualitative analysis to candidates...")
        
        llm_map = {ev["resume_id"]: ev for ev in llm_analyses}
        
        results = []
        for candidate in candidates:
            resume_id = str(candidate["resume_id"])
            algo_score = candidate["rag_score"]
            
            llm_analysis = llm_map.get(resume_id)
            
            if llm_analysis:
                results.append({
                    **candidate,
                    "final_score": algo_score,
                    "llm_analysis": {
                        "strengths": llm_analysis.get("strengths", ""),
                        "concerns": llm_analysis.get("concerns", ""),
                        "recommendation": llm_analysis.get("recommendation", ""),
                    }
                })
                
                logger.info("  %s: Score=%d, Recommendation=%s",
                           candidate["contact"].get("name", "Unknown")[:20],
                           algo_score,
                           llm_analysis.get("recommendation", "unknown"))
            else:
                logger.warning("  %s: No LLM analysis",
                             candidate["contact"].get("name", "Unknown"))
                results.append({
                    **candidate,
                    "final_score": algo_score,
                    "llm_analysis": {
                        "strengths": "",
                        "concerns": "No qualitative analysis available.",
                        "recommendation": "unknown",
                    }
                })
        
        results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return results
