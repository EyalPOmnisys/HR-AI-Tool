"""Experience scoring using proximity-based approach that favors candidates close to requirements rather than just overqualification."""

from __future__ import annotations
from typing import Optional, Dict, Any


def calculate_experience_match(
    candidate_years: Optional[float],
    required_years: float
) -> float:
    """
    Calculate experience match score with proximity preference (0-1 scale).
    
    Strategy: Prefer candidates CLOSE to the requirement.
    
    Scoring logic (HR Perspective):
    - Under-qualified:
        - < 50% of required: Not relevant (Score ~0.0-0.2)
        - 50%-100% of required: Linear climb (e.g. 75% -> 0.6 "problematic but ok")
    - Over-qualified:
        - +0 to +1 years: Perfect match (1.0)
        - > +1 years: Decay based on seniority.
          - A senior (7 years) won't take a junior job (4 years).
          - Decay is gentler for higher required years.
    
    Args:
        candidate_years: Candidate's years of experience
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
    
    # Under-qualified
    if resume_years < job_min_years:
        ratio = resume_years / job_min_years
        if ratio < 0.5:
            # "2 years under (for 4) is not relevant" -> < 50% is very low
            return 0.05
        else:
            # Map 0.5 -> 0.2
            # Map 1.0 -> 1.0
            # "3 years (for 4) is problematic but not terrible" -> 0.75 -> 0.6
            return 0.2 + (ratio - 0.5) * 1.6

    # Over-qualified (or exact match)
    else:
        diff = resume_years - job_min_years
        
        # "If I am 5 (for 4) it's also great" -> +1 year is perfect
        if diff <= 1.0:
            return 1.0
            
        # "6 is great but less" -> Decay starts
        # NEW: Non-linear decay based on seniority level
        # For senior roles (7+), experience gaps are less critical
        else:
            # Dynamic decay with seniority adjustment:
            # Junior roles (<5 years): Strict decay - over-qualification is more problematic
            # Mid roles (5-6 years): Moderate decay
            # Senior roles (7+ years): Gentle decay - "7→9 or 10→12 is not critical"
            
            if job_min_years < 5:
                # Junior/Mid: More sensitive to over-qualification
                # Example: R=4, C=7 → diff=3 → score = 1.0 - 2*0.18 = 0.64
                decay_factor = 0.18
            elif job_min_years < 7:
                # Mid-Senior transition: Moderate decay
                # Example: R=5, C=8 → diff=3 → score = 1.0 - 2*0.12 = 0.76
                decay_factor = 0.12
            else:
                # Senior (7+): Very gentle decay
                # Example: R=7, C=10 → diff=3 → score = 1.0 - 2*0.06 = 0.88 ✓
                # Example: R=10, C=15 → diff=5 → score = 1.0 - 4*0.06 = 0.76 ✓
                decay_factor = 0.06
            
            score = 1.0 - (diff - 1.0) * decay_factor
            return max(0.0, score)


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
    elif candidate_years < job_min_years * 0.5:
        verdict = "significantly_under_qualified"
    elif candidate_years < job_min_years:
        verdict = "slightly_under_qualified"
    elif candidate_years <= job_min_years + 1.0:
        verdict = "perfect_match"
    elif candidate_years <= job_min_years + 3.0:
        verdict = "moderately_over_qualified"
    else:
        verdict = "significantly_over_qualified"
    
    return {
        "score": round(score, 3),
        "candidate_years": round(candidate_years, 1),
        "required_years": round(job_min_years, 1),
        "verdict": verdict
    }
