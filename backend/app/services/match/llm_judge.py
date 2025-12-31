"""LLM-based candidate evaluation that provides final authoritative scoring using job requirements and candidate resumes in batches."""

from __future__ import annotations
import logging
from typing import List, Dict, Any
from uuid import UUID
import json
import asyncio
from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, Resume
from app.core.config import settings
from app.services.common.llm_client import load_prompt, default_llm_client

# Load evaluation prompt
CANDIDATE_EVALUATION_PROMPT = load_prompt("match/candidate_evaluation.prompt.txt")

logger = logging.getLogger("match.llm_judge")


class LLMJudge:
    """
    LLM-based candidate evaluation.
    
    Flow:
    1. Prepare job data (title + description + analysis_json)
    2. Prepare candidate data (extraction_json + algorithmic_score)
    3. Call LLM in batches of 3 candidates
    4. Return evaluations with final_score, strengths, concerns
    """
    
    BATCH_SIZE = 3  # Process 3 candidates per LLM call (Reduced from 5 to improve reliability)
    
    @staticmethod
    async def evaluate_candidates(
        session: AsyncSession,
        job: Job,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all candidates using LLM.
        
        Args:
            session: Database session
            job: Job to match against
            candidates: List of candidates with algorithmic scores from ensemble
            
        Returns:
            List of candidates with added llm_analysis and final_score
        """
        logger.info("=" * 80)
        logger.info("LLM JUDGE: Starting Deep Evaluation")
        logger.info("=" * 80)
        logger.info(f"Job: '{job.title}' (ID: {job.id})")
        logger.info(f"Candidates to evaluate: {len(candidates)}")
        logger.info(f"Batch size: {LLMJudge.BATCH_SIZE}")
        logger.info(f"Expected API calls: {(len(candidates) + LLMJudge.BATCH_SIZE - 1) // LLMJudge.BATCH_SIZE}")
        logger.info("")
        
        # Step 1: Prepare job data
        job_data = LLMJudge._prepare_job_data(job)
        logger.info("✓ Job data prepared")
        logger.info(f"  - Title: {job_data['title']}")
        logger.info(f"  - Description length: {len(job_data['description'])} characters")
        logger.info("")
        
        # Step 2: Load resume data for all candidates
        logger.info("Loading resume data from database...")
        candidates_with_data = await LLMJudge._load_resume_data(session, candidates)
        logger.info(f"✓ Loaded {len(candidates_with_data)} resumes")
        
        # Add rank to each candidate (1-indexed) - Important for LLM context
        total_candidates = len(candidates_with_data)
        for idx, candidate in enumerate(candidates_with_data, 1):
            candidate["rank"] = idx
            candidate["total_candidates"] = total_candidates
        logger.info("")
        
        # Step 3: Call LLM in batches
        logger.info("Calling LLM for evaluation...")
        logger.info("-" * 80)
        evaluations = await LLMJudge._evaluate_in_batches(job_data, candidates_with_data)
        logger.info("-" * 80)
        logger.info(f"✓ LLM evaluation complete: {len(evaluations)} candidates evaluated")
        logger.info("")
        
        # Step 4: Merge evaluations back into candidates
        logger.info("Merging LLM evaluations with candidate data...")
        final_results = LLMJudge._merge_evaluations(candidates, evaluations)
        
        # Sort by LLM final_score (descending)
        final_results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        logger.info("=" * 80)
        logger.info("LLM JUDGE: Evaluation Complete")
        logger.info("=" * 80)
        logger.info(f"Total candidates: {len(final_results)}")
        if final_results:
            logger.info(f"Top 5 LLM scores: {[c.get('final_score', 0) for c in final_results[:5]]}")
        logger.info("=" * 80)
        logger.info("")
        
        return final_results
    
    @staticmethod
    def _prepare_job_data(job: Job) -> Dict[str, Any]:
        """
        Prepare simple job data for LLM (raw text only).
        
        Returns:
            {
                "title": str,
                "description": str  # Combined description + free_text
            }
        """
        logger.debug(f"Preparing job data for job_id={job.id}")
        
        # Combine description and free_text
        full_description = job.job_description or ""
        if job.free_text:
            full_description += "\n\n" + job.free_text
        
        return {
            "title": job.title,
            "description": full_description.strip()
        }
    
    @staticmethod
    async def _load_resume_data(
        session: AsyncSession,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Load resume data and convert to human-readable format.
        
        Returns:
            List of candidates with added 'resume_text' field
        """
        enriched = []
        
        for idx, candidate in enumerate(candidates, 1):
            resume_id = candidate["resume_id"]
            
            # Load resume from DB
            resume: Resume = await session.get(Resume, resume_id)
            if not resume:
                logger.warning(f"  [{idx}/{len(candidates)}] Resume not found: {resume_id}")
                continue
            
            # Convert extraction_json to simple readable format
            resume_text = LLMJudge._format_resume_text(resume.extraction_json or {})
            
            enriched.append({
                **candidate,
                "resume_text": resume_text
            })
        
        return enriched
    
    @staticmethod
    def _format_resume_text(extraction: Dict[str, Any]) -> str:
        """
        Convert extraction_json to simple readable text format.
        """
        lines = []
        
        # Name and contact
        person = extraction.get("person", {})
        if person.get("name"):
            lines.append(f"NAME: {person['name']}")
        
        # Years of experience
        primary_years = extraction.get("primary_years")
        if primary_years:
            lines.append(f"EXPERIENCE: {primary_years} years")
        
        # Skills
        skills = extraction.get("skills", [])
        if skills:
            skill_names = [s["name"] for s in skills if s.get("name")]
            if skill_names:
                lines.append(f"SKILLS: {', '.join(skill_names)}")
        
        # Education
        education = extraction.get("education", [])
        if education:
            lines.append("\nEDUCATION:")
            for edu in education:
                degree = edu.get("degree", "")
                field = edu.get("field", "")
                institution = edu.get("institution", "")
                edu_line = f"  - {degree} in {field}" if degree and field else f"  - {field or degree or institution}"
                if institution and institution not in edu_line:
                    edu_line += f" from {institution}"
                lines.append(edu_line)
        
        # Work experience
        experience = extraction.get("experience", [])
        if experience:
            lines.append("\nWORK EXPERIENCE:")
            
            # Sort experience by start_date (descending) to ensure most recent is first
            # Handle "present", "current", nulls, and year strings
            def parse_date_sort_key(exp):
                start = exp.get("start_date")
                end = exp.get("end_date")
                
                # If currently working there (end date is present/null), it's the most recent
                is_current = False
                if end:
                    end_lower = str(end).lower()
                    if "present" in end_lower or "current" in end_lower or "now" in end_lower:
                        is_current = True
                elif start: # If start exists but end is null, assume current
                     is_current = True
                
                if is_current:
                    return 9999 # Future/Present
                
                # Try to parse year from end date
                try:
                    if end:
                        # Extract first 4 digits
                        import re
                        match = re.search(r'\d{4}', str(end))
                        if match:
                            return int(match.group(0))
                except:
                    pass
                
                # Fallback to start date
                try:
                    if start:
                        import re
                        match = re.search(r'\d{4}', str(start))
                        if match:
                            return int(match.group(0))
                except:
                    pass
                    
                return 0 # Unknown date
            
            # Sort in descending order (most recent first)
            sorted_experience = sorted(experience, key=parse_date_sort_key, reverse=True)
            
            for i, exp in enumerate(sorted_experience):
                title = exp.get("title", "")
                company = exp.get("company", "")
                start = exp.get("start_date", "")
                end = exp.get("end_date", "Present")
                
                exp_header = f"  • {title} at {company}"
                if start:
                    exp_header += f" ({start} - {end})"
                
                # Explicitly mark the first item as current if it looks current
                if i == 0:
                    is_current = False
                    if end:
                        end_lower = str(end).lower()
                        if "present" in end_lower or "current" in end_lower:
                            is_current = True
                    elif start:
                        is_current = True
                    
                    if is_current:
                        exp_header += " [CURRENT ROLE]"
                
                lines.append(exp_header)
                
                # Technologies
                tech = exp.get("tech", [])
                if tech:
                    lines.append(f"    Tech: {', '.join(tech)}")
                
                # Bullets
                bullets = exp.get("bullets", [])
                for bullet in bullets:
                    lines.append(f"    - {bullet}")
        
        return "\n".join(lines)
    
    @staticmethod
    async def _evaluate_in_batches(
        job_data: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Call LLM in batches of BATCH_SIZE candidates.
        
        Returns:
            List of evaluations: [{resume_id, final_score, strengths, concerns}, ...]
        """
        all_evaluations = []
        num_batches = (len(candidates) + LLMJudge.BATCH_SIZE - 1) // LLMJudge.BATCH_SIZE
        
        tasks = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * LLMJudge.BATCH_SIZE
            end_idx = min(start_idx + LLMJudge.BATCH_SIZE, len(candidates))
            batch = candidates[start_idx:end_idx]
            
            # Create task for this batch
            tasks.append(LLMJudge._call_llm_for_batch(
                job_data=job_data,
                candidates=batch,
                batch_num=batch_idx + 1
            ))
            
        # Run all batches in parallel
        results_lists = await asyncio.gather(*tasks)
        
        # Flatten results
        for res in results_lists:
            all_evaluations.extend(res)
        
        return all_evaluations
    
    @staticmethod
    async def _call_llm_for_batch(
        job_data: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        batch_num: int
    ) -> List[Dict[str, Any]]:
        """
        Call LLM for a single batch of candidates.
        
        Returns:
            List of evaluations for this batch
        """
        # Build system prompt
        system_prompt = CANDIDATE_EVALUATION_PROMPT
        
        # Build user prompt with job + candidates
        user_prompt = {
            "job": job_data,
            "candidates": []
        }
        
        for candidate in candidates:
            user_prompt["candidates"].append({
                "resume_id": str(candidate["resume_id"]),
                "algorithmic_score": candidate.get("rag_score", 0),
                "algorithmic_rank": candidate.get("rank", 0),  # Position in ranked list
                "current_title": candidate.get("contact", {}).get("title", "Unknown"),
                "resume": candidate.get("resume_text", "")
            })
        
        max_retries = 3
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry attempt {attempt}/{max_retries} for batch {batch_num}...")
                    await asyncio.sleep(1)

                # Prepare messages
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Here is the data for the job and candidates to evaluate. Please output the JSON evaluation list as requested:\n\n" + json.dumps(user_prompt, ensure_ascii=False, indent=2)}
                ]
                
                # DEBUG LOGGING
                logger.info(f"DEBUG: Sending prompt to LLM (Batch {batch_num}). User prompt keys: {list(user_prompt.keys())}")
                logger.info(f"DEBUG: Job Title: {user_prompt['job'].get('title')}")
                logger.info(f"DEBUG: Candidate count: {len(user_prompt['candidates'])}")

                # Call LLM (synchronous call wrapped in executor)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    partial(default_llm_client.chat_json, messages, timeout=180)
                )
                
                # DEBUG LOGGING
                logger.info(f"DEBUG: LLM Response received (Batch {batch_num})")
                if response.data:
                    logger.info(f"DEBUG: Raw response data keys: {list(response.data.keys())}")
                    logger.info(f"DEBUG: Raw response content: {json.dumps(response.data, ensure_ascii=False)[:1000]}...")
                else:
                    logger.info("DEBUG: Response data is empty or None")

                # Parse response
                content_dict = response.data
                
                # Handle 'evaluations', 'evaluation_list', and singular 'evaluation' keys
                evaluations = []
                
                # Try all known keys
                for key in ["evaluations", "evaluation_list", "candidates", "matches", "results", "evaluation"]:
                    if key in content_dict and isinstance(content_dict[key], list):
                        evaluations = content_dict[key]
                        break
                
                if not evaluations:
                    logger.warning(f"⚠️  LLM returned valid JSON but no recognized list key. Keys found: {list(content_dict.keys())}")
                    if attempt < max_retries:
                        continue

                # Validate: ensure we got evaluations for all candidates
                if len(evaluations) != len(candidates):
                    logger.warning(f"⚠️  Expected {len(candidates)} evaluations, got {len(evaluations)}")
                    if attempt < max_retries:
                        continue

                # Compact summary table
                logger.info(f"\n📊 Batch {batch_num} Results:")
                logger.info("┌─────────────────────────┬───────┐")
                logger.info("│ Candidate               │ Score │")
                logger.info("├─────────────────────────┼───────┤")
                
                for ev in evaluations:
                    # Get candidate info
                    resume_id = ev.get("resume_id", "unknown")
                    
                    # FIX: Handle different score keys (final_score vs match_score vs score)
                    final_score = None
                    for score_key in ["final_score", "match_score", "fit_score", "score", "overall_score", "rating", "overall_fit_score"]:
                        if score_key in ev:
                            final_score = ev[score_key]
                            break
                    
                    if final_score is None:
                        logger.warning(f"⚠️  No score found for candidate {resume_id}. Keys: {list(ev.keys())}")
                        final_score = 0
                    
                    # Find candidate name from input
                    candidate_name = "Unknown"
                    for cand in candidates:
                        if str(cand["resume_id"]) == resume_id:
                            resume_text = cand.get("resume_text", "")
                            if resume_text.startswith("NAME: "):
                                candidate_name = resume_text.split("\n")[0].replace("NAME: ", "")
                            break
                    
                    # Truncate name if too long
                    name_display = candidate_name[:23] if len(candidate_name) <= 23 else candidate_name[:20] + "..."
                    
                    logger.info(f"│ {name_display:<23} │ {final_score:>5} │")
                
                logger.info("└─────────────────────────┴───────┘\n")
                
                return evaluations
                
            except Exception as e:
                logger.error(f"  ❌ LLM call failed for batch {batch_num} (attempt {attempt+1}): {e}")
                last_exception = e
                if attempt < max_retries:
                    continue
        
        # If we get here, all retries failed
        logger.error(f"❌ All {max_retries + 1} attempts failed for batch {batch_num}. Last error: {last_exception}")
        
        # Return empty evaluations with zero scores as fallback
        fallback_evaluations = []
        for candidate in candidates:
            fallback_evaluations.append({
                "resume_id": str(candidate["resume_id"]),
                "final_score": 0,
                "strengths": "LLM evaluation failed - could not analyze",
                "concerns": "System error during evaluation"
            })
        
        return fallback_evaluations
    
    @staticmethod
    def _merge_evaluations(
        candidates: List[Dict[str, Any]],
        evaluations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge LLM evaluations back into candidate dictionaries.
        
        Scoring logic:
        - rag_score: Preserved from Stage 1 ensemble (RAG + Skills + Title + Experience + Stability)
        - llm_score: Stage 2 LLM evaluation score (from LLM's final_score output)
        - final_score: Blended score (30% Stage 1 + 70% Stage 2)
        
        Returns:
            List of candidates with llm_analysis, llm_score, and blended final_score
        """
        # Build lookup map: resume_id -> evaluation
        eval_map = {}
        for ev in evaluations:
            resume_id_str = ev.get("resume_id")
            if resume_id_str:
                # Handle both string and UUID
                try:
                    eval_map[str(resume_id_str)] = ev
                except:
                    pass
        
        results = []
        for candidate in candidates:
            resume_id = str(candidate["resume_id"])
            evaluation = eval_map.get(resume_id)
            
            # Stage 1 ensemble score (already in candidate from ensemble.py)
            stage1_score = candidate.get("rag_score", 0)
            
            if evaluation:
                # Stage 2 LLM score (Handle both keys)
                stage2_score = None
                for score_key in ["final_score", "match_score", "fit_score", "score", "overall_score", "rating", "overall_fit_score"]:
                    if score_key in evaluation:
                        stage2_score = evaluation[score_key]
                        break
                
                if stage2_score is None:
                    stage2_score = 0
                
                # Use LLM score directly as final score (100% Stage 2)
                blended_final_score = int(stage2_score)
                
                # Handle text fields (strengths/concerns vs match_reasoning)
                strengths = evaluation.get("strengths")
                concerns = evaluation.get("concerns")
                
                # Fallback if LLM returned alternative fields
                if not strengths or not concerns:
                    # Check for common variations seen in logs
                    reasoning = evaluation.get("match_reasoning") or evaluation.get("match_reason") or evaluation.get("fit_reasoning")
                    notes = evaluation.get("notes")
                    
                    # Handle case where reasoning is a dictionary (seen in logs)
                    if isinstance(reasoning, dict):
                        parts = []
                        for k, v in reasoning.items():
                            if isinstance(v, (str, int, float)):
                                parts.append(f"• {k.replace('_', ' ').title()}: {v}")
                        reasoning = "\n".join(parts)
                    
                    # Assign fallbacks
                    if not strengths:
                        strengths = str(reasoning) if reasoning else (str(notes) if notes else "Analysis not available.")
                        
                    if not concerns:
                        # If we used reasoning for strengths, concerns might be redundant or missing
                        # Try to extract negative points from reasoning if possible, otherwise provide a neutral message
                        concerns = "Please review the detailed analysis in the strengths section." if reasoning else "No specific concerns identified."

                # Ensure they are strings
                if not isinstance(strengths, str): strengths = str(strengths)
                if not isinstance(concerns, str): concerns = str(concerns)

                results.append({
                    **candidate,
                    "llm_score": stage2_score,  # Stage 2 LLM score
                    "final_score": blended_final_score,  # Blended final score
                    "llm_analysis": {
                        "strengths": strengths,
                        "concerns": concerns
                    }
                })
            else:
                # No LLM evaluation (error case) - use Stage 1 score only
                results.append({
                    **candidate,
                    "llm_score": 0,  # No LLM score available
                    "final_score": stage1_score,  # Fall back to Stage 1 ensemble score
                    "llm_analysis": {
                        "strengths": "LLM evaluation not available",
                        "concerns": "Could not complete LLM analysis"
                    }
                })
        
        return results