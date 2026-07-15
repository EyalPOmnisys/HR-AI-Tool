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
        # Experience beyond the requirement is an asset, not a defect - this mirrors
        # the LLM judge rubric ("treat extra experience as a BONUS"). The previous
        # aggressive decay gave a 8.5y candidate a 0.01 score on a "2+ years" job,
        # inverting the ranking against the judge for every senior candidate.
        # Penalize only extreme gaps on junior roles (flight-risk concern).
        if job_min_years < 5 and resume_years > job_min_years * 3:
            return 0.75
        return 1.0


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
    
    # Determine if role is tech or non-tech
    is_tech_role = job_analysis.get("is_tech_role", True)

    # Extract candidate years based on role type
    exp_meta = candidate_extraction.get("experience_meta", {})
    rec_primary = exp_meta.get("recommended_primary_years", {})
    totals = exp_meta.get("totals_by_category", {})

    primary_bucket = "tech" if is_tech_role else "other"
    secondary_buckets = ["other", "military"] if is_tech_role else ["tech"]

    candidate_years = rec_primary.get(primary_bucket)
    if candidate_years is None:
        candidate_years = totals.get(primary_bucket)

    # Cross-bucket fallback: extraction sometimes mis-buckets years, and the job's
    # is_tech_role flag itself can be wrong. If the primary bucket is empty but
    # another bucket holds real experience, credit it at a discount instead of
    # zeroing the candidate (military often IS the relevant tech experience here).
    fallback_bucket = None
    if not candidate_years:
        best_other = 0.0
        for bucket in secondary_buckets:
            bucket_years = rec_primary.get(bucket) or totals.get(bucket) or 0.0
            if bucket_years and float(bucket_years) > best_other:
                best_other = float(bucket_years)
                fallback_bucket = bucket
        if best_other > 0:
            candidate_years = best_other * 0.7

    if candidate_years is None:
        # Last resort fallback
        candidate_years = candidate_extraction.get("years_of_experience", 0)

    candidate_years = float(candidate_years) if candidate_years else 0.0

    # Unknown is not zero: if years could not be computed (bad dates are common)
    # but the resume HAS work history, score neutral instead of destroying the
    # candidate - the LLM judge sees the full history and resolves the ambiguity.
    experience_entries = candidate_extraction.get("experience") or []
    years_unknown = candidate_years == 0.0 and len(experience_entries) > 0

    if years_unknown:
        score = 0.5
        verdict = "years_unknown"
    else:
        score = calculate_experience_match(candidate_years, job_min_years)

        # Determine verdict using dynamic thresholds
        perfect_zone_buffer = job_min_years * 0.5

        if job_min_years == 0:
            verdict = "no_requirement"
        elif candidate_years < job_min_years * 0.5:
            verdict = "significantly_under_qualified"
        elif candidate_years < job_min_years:
            verdict = "slightly_under_qualified"
        elif candidate_years <= job_min_years + perfect_zone_buffer:
            verdict = "perfect_match"
        elif candidate_years <= job_min_years + perfect_zone_buffer + 2.0:
            verdict = "moderately_over_qualified"
        else:
            verdict = "significantly_over_qualified"

    result = {
        "score": round(score, 3),
        "candidate_years": round(candidate_years, 1),
        "required_years": round(job_min_years, 1),
        "verdict": verdict
    }
    if fallback_bucket:
        result["years_source"] = f"{fallback_bucket} (discounted 0.7)"
    return result
