# Experience matching with proximity-based scoring.
# Prefers candidates close to requirements rather than just "more is better".

from __future__ import annotations
from typing import Optional, Dict, Any


def calculate_experience_match(
    candidate_years: Optional[float],
    required_years: float
) -> float:
    """
    Calculate experience match score with proximity preference (0-1 scale).
    
    Strategy: Prefer candidates CLOSE to the requirement, not just "more is better".
    
    Scoring logic:
    - Significantly under-qualified (< 80% of required): Proportional score (0.0-0.8)
    - Slightly under-qualified (80%-100% of required): 0.75-1.0
    - Perfect range (100%-200% of required): 1.0
    - Moderately over-qualified (200%-300%): 1.0 → 0.7 (linear decay)
    - Significantly over-qualified (300%+): 0.7 → 0.5 (gentle decay)
    
    Examples:
    - Required: 2 years
      - 1.0 years → 0.5 (significantly under)
      - 1.7 years → 0.88 (slightly under)
      - 2.0 years → 1.0 (perfect)
      - 3.0 years → 1.0 (perfect range)
      - 5.0 years → 0.85 (moderately over)
      - 10 years → 0.6 (significantly over)
    
    Args:
        candidate_years: Candidate's years of experience (primary/tech years)
        required_years: Minimum years required by job
        
    Returns:
        Experience match score (0.0-1.0)
    """
    # Handle None/zero candidate years
    if candidate_years is None or candidate_years <= 0:
        return 0.5 if required_years == 0 else 0.0
    
    # Handle no requirement
    if required_years == 0:
        return 1.0 if candidate_years > 0 else 0.5
    
    resume_years = float(candidate_years)
    job_min_years = float(required_years)
    
    # Significantly under-qualified (< 80%)
    if resume_years < job_min_years * 0.8:
        return resume_years / job_min_years  # Proportional: 0.0 → 0.8
    
    # Slightly under-qualified (80% - 100%)
    elif resume_years < job_min_years:
        # Linear interpolation: 0.75 → 1.0
        return 0.75 + (0.25 * (resume_years / job_min_years))
    
    # Perfect range (100% - 200%)
    elif resume_years <= job_min_years * 2:
        return 1.0
    
    # Moderately over-qualified (200% - 300%)
    elif resume_years <= job_min_years * 3:
        # Linear decay: 1.0 → 0.7
        excess_ratio = (resume_years - job_min_years * 2) / job_min_years
        return 1.0 - (excess_ratio * 0.3)
    
    # Significantly over-qualified (300%+)
    else:
        # Gentle decay: 0.7 → 0.5 (capped at 0.5)
        excess_ratio = (resume_years - job_min_years * 3) / job_min_years
        return max(0.5, 0.7 - (excess_ratio * 0.1))


def calculate_experience_match_detailed(
    candidate_extraction: Dict[str, Any],
    job_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate detailed experience match with breakdown.
    
    Args:
        candidate_extraction: Resume extraction JSON with experience_meta
        job_analysis: Job analysis JSON with experience requirements
        
    Returns:
        Dict with score, candidate_years, required_years, and verdict
    """
    # Extract job requirements
    job_exp = job_analysis.get("experience", {})
    job_min_years = job_exp.get("years_min", 0) or 0
    
    # Handle string format (e.g., "2 years")
    if isinstance(job_min_years, str):
        import re
        match = re.search(r'(\d+)', job_min_years)
        if match:
            job_min_years = int(match.group(1))
        else:
            job_min_years = 0
    
    job_min_years = float(job_min_years)
    
    # Extract candidate years (prefer primary tech years)
    exp_meta = candidate_extraction.get("experience_meta", {})
    rec_primary = exp_meta.get("recommended_primary_years", {})
    candidate_years = rec_primary.get("tech")
    
    if candidate_years is None:
        # Fallback to total tech years
        totals = exp_meta.get("totals_by_category", {})
        candidate_years = totals.get("tech")
    
    if candidate_years is None:
        # Last resort: legacy years_of_experience
        candidate_years = candidate_extraction.get("years_of_experience", 0)
    
    candidate_years = float(candidate_years) if candidate_years else 0.0
    
    # Calculate score
    score = calculate_experience_match(candidate_years, job_min_years)
    
    # Determine verdict
    if job_min_years == 0:
        verdict = "no_requirement"
    elif candidate_years < job_min_years * 0.8:
        verdict = "significantly_under_qualified"
    elif candidate_years < job_min_years:
        verdict = "slightly_under_qualified"
    elif candidate_years <= job_min_years * 2:
        verdict = "perfect_match"
    elif candidate_years <= job_min_years * 3:
        verdict = "moderately_over_qualified"
    else:
        verdict = "significantly_over_qualified"
    
    return {
        "score": round(score, 3),
        "candidate_years": round(candidate_years, 1),
        "required_years": round(job_min_years, 1),
        "verdict": verdict
    }
