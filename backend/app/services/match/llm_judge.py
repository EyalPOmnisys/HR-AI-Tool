"""
LLM-based deep analysis of top candidates.
Loads full resumes and performs comprehensive evaluation.
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
        logger.info("JOB REQUIREMENTS:")
        logger.info("  Title: %s", job_requirements["title"])
        logger.info("  Must-Have Skills: %s", ", ".join(job_requirements.get("must_have_skills", [])))
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
        """Extract structured requirements from job."""
        analysis = job.analysis_json or {}
        
        # Extract must-have skills
        skills_dict = analysis.get("skills", {})
        must_have = []
        if isinstance(skills_dict, dict):
            must_have = skills_dict.get("must_have", [])
        
        # Extract tech stack
        tech_stack = analysis.get("tech_stack", {})
        tech_list = []
        if isinstance(tech_stack, dict):
            tech_list = tech_stack.get("frameworks", []) + tech_stack.get("languages", [])
        
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
        
        return {
            "title": job.title,
            "description": job.job_description[:500] if job.job_description else "",  # First 500 chars
            "must_have_skills": must_have,
            "tech_stack": tech_list,
            "min_years": min_years,
        }
    
    @staticmethod
    async def _call_llm(
        job_requirements: Dict,
        candidates: List[Dict]
    ) -> List[Dict]:
        """Call LLM to evaluate candidates."""
        logger.info("Calling OpenAI API for deep evaluation...")
        
        # Load prompt from file
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "match" / "candidate_evaluation.prompt.txt"
        system_prompt = prompt_path.read_text(encoding="utf-8")

        # Build user prompt
        user_prompt = {
            "job": job_requirements,
            "candidates": [
                {
                    "resume_id": str(c["resume_id"]),
                    "rag_score": c["rag_score"],
                    "candidate_name": c["contact"].get("name", "Unknown"),
                    "contact_email": c["contact"].get("email"),
                    "experience_years": c["contact"].get("experience_years"),
                    "skills": sorted(list(c["contact"].get("skills", []))),
                    "full_resume": c["full_resume"],
                }
                for c in candidates
            ]
        }
        
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                temperature=0.2,  # Slight creativity for nuanced evaluation
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
        """Combine RAG and LLM scores into final ranking."""
        logger.info("Combining RAG and LLM scores...")
        
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
                
                # Weighted combination: 50% RAG + 50% LLM
                final_score = round((rag_score * 0.5) + (llm_score * 0.5))
                
                # Apply verdict penalty if poor fit
                if verdict == "poor":
                    final_score = max(0, final_score - 15)
                elif verdict == "weak":
                    final_score = max(0, final_score - 8)
                
                results.append({
                    **candidate,
                    "llm_score": llm_score,
                    "llm_verdict": verdict,
                    "llm_strengths": llm_ev.get("strengths", ""),
                    "llm_concerns": llm_ev.get("concerns", ""),
                    "llm_recommendation": llm_ev.get("recommendation", ""),
                    "final_score": final_score,
                })
                
                logger.info("  %s: RAG=%d, LLM=%d → Final=%d (%s)",
                           candidate["contact"].get("name", "Unknown")[:20],
                           rag_score, llm_score, final_score, verdict)
            else:
                # No LLM evaluation - use RAG score only
                logger.warning("  %s: No LLM evaluation, using RAG score only",
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
