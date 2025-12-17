"""Employment stability scoring that measures job stability based on tenure patterns, penalizing job hopping and rewarding consistent employment."""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger("match.stability")


def _calculate_duration_from_dates(start_date: Optional[str], end_date: Optional[str]) -> Optional[float]:
    """
    Calculate duration in years from start/end dates.
    
    Handles various date formats:
    - "2023" (year only)
    - "2023-01" (year-month)
    - "2023-01-15" (full date)
    - "January 2023" (month name + year)
    - "Jan 2023" (short month + year)
    
    If end_date is None or "present", uses current date.
    
    Args:
        start_date: Start date string
        end_date: End date string or None for current
        
    Returns:
        Duration in years, or None if dates are invalid
    """
    if not start_date:
        return None
    
    try:
        # Clean up the date strings
        start_date = start_date.strip()
        if end_date:
            end_date = end_date.strip()
        
        # Parse start date - try different formats
        start = None
        start_is_year_only = False
        
        # Try: Just year "2023"
        if len(start_date) == 4 and start_date.isdigit():
            # CHANGE: Assume mid-year (July 1st) for start year to be conservative, 
            # unless it's the only info we have, but let's stick to Jan 1 for start to not punish too hard,
            # BUT we will fix the end date logic.
            start = datetime(int(start_date), 1, 1)
            start_is_year_only = True
        # Try: "2023-01" (year-month with dash)
        elif len(start_date) == 7 and "-" in start_date:
            start = datetime.strptime(start_date, "%Y-%m")
        # Try: "2023-01-15" (full date with dash)
        elif len(start_date) == 10 and "-" in start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        # Try: "January 2023" or "Jan 2023" (month name + year)
        else:
            try:
                start = datetime.strptime(start_date, "%B %Y")  # Full month name
            except ValueError:
                try:
                    start = datetime.strptime(start_date, "%b %Y")  # Short month name
                except ValueError:
                    pass
        
        if start is None:
            logger.warning(f"Could not parse start_date: '{start_date}'")
            return None
        
        # Parse end date (or use today)
        end = None
        
        if end_date is None or end_date.lower() == "present":
            end = datetime.now()
        # Try: Just year "2024"
        elif len(end_date) == 4 and end_date.isdigit():
            # CHANGE: If start was year-only and end is year-only, calculate simple difference.
            # Old logic used Dec 31, which made 2023-2024 = 2 years.
            # New logic: Use Jan 1 for end year too, so 2023-2024 = 1 year.
            if start_is_year_only:
                 end = datetime(int(end_date), 1, 1)
                 # Ensure at least 1 year if same year provided (2023-2023)
                 if end.year == start.year:
                     return 0.5
            else:
                # If start had month but end is just year, assume mid-year end
                end = datetime(int(end_date), 6, 30)
        # Try: "2024-11" (year-month with dash)
        elif len(end_date) == 7 and "-" in end_date:
            end = datetime.strptime(end_date, "%Y-%m")
        # Try: "2024-11-19" (full date with dash)
        elif len(end_date) == 10 and "-" in end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        # Try: "January 2024" or "Jan 2024" (month name + year)
        else:
            try:
                end = datetime.strptime(end_date, "%B %Y")  # Full month name
            except ValueError:
                try:
                    end = datetime.strptime(end_date, "%b %Y")  # Short month name
                except ValueError:
                    pass
        
        if end is None:
            logger.warning(f"Could not parse end_date: '{end_date}'")
            return None
        
        # Calculate years
        delta = end - start
        years = delta.days / 365.25
        return max(0.0, years)  # Don't return negative
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse dates: start='{start_date}', end='{end_date}' - Error: {e}")
        return None


def calculate_employment_stability(
    candidate_extraction: Dict[str, Any],
    job_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate employment stability score based on tenure patterns.
    
    Philosophy:
    - Rewards consistent employment (2-4 years per role)
    - Penalizes job hopping (multiple short stints)
    - Adjusts expectations based on candidate seniority
    - Only lowers score, never disqualifies
    
    Scoring (0.0-1.0 scale):
    - 1.0 = Excellent stability (long tenures, consistent)
    - 0.8-0.9 = Good stability (meets expectations)
    - 0.6-0.7 = Moderate concerns (some short stints)
    - 0.4-0.5 = Significant concerns (job hopper pattern)
    - 0.0-0.3 = Severe stability issues
    
    Args:
        candidate_extraction: Resume extraction JSON with experience data
        job_analysis: Job analysis JSON (for context, not heavily used)
        
    Returns:
        Dict with score, metrics, and verdict
    """
    experience_list = candidate_extraction.get("experience", [])
    
    if not experience_list or len(experience_list) == 0:
        return {
            "score": 0.5,  # Neutral score for no data
            "average_tenure_years": 0.0,
            "total_jobs": 0,
            "tech_jobs": 0,
            "short_stints": 0,
            "long_tenures": 0,
            "verdict": "no_experience_data",
            "concerns": ["No employment history available"],
            "strengths": []
        }
    
    # Extract total experience to determine seniority level
    exp_meta = candidate_extraction.get("experience_meta", {})
    rec_primary = exp_meta.get("recommended_primary_years", {})
    total_experience = rec_primary.get("tech")
    
    if total_experience is None:
        totals = exp_meta.get("totals_by_category", {})
        total_experience = totals.get("tech")
    
    if total_experience is None:
        total_experience = candidate_extraction.get("years_of_experience", 0)
    
    total_experience = float(total_experience) if total_experience else 0.0
    
    # Determine expected tenure based on seniority
    # Junior (0-3 years): Expected tenure = 2.0 years
    # Mid (3-6 years): Expected tenure = 3.0 years
    # Senior (6+ years): Expected tenure = 4.0 years
    if total_experience < 3:
        expected_tenure = 2.0
        seniority_level = "junior"
    elif total_experience < 6:
        expected_tenure = 3.0
        seniority_level = "mid"
    else:
        expected_tenure = 4.0
        seniority_level = "senior"
    
    # Filter tech jobs (have tech stack)
    tech_jobs = []
    
    # Build a set of identifiers for jobs classified as 'tech' in clusters
    tech_cluster_ids = set()
    clusters = exp_meta.get("experience_clusters", [])
    for cluster in clusters:
        if cluster.get("category") == "tech":
            for member in cluster.get("members", []):
                # Create a unique key based on title and start date
                t = str(member.get("title", "")).lower().strip()
                s = str(member.get("start_date", "")).strip()
                if t:
                    tech_cluster_ids.add(f"{t}|{s}")

    for exp in experience_list:
        if isinstance(exp, dict):
            tech = exp.get("tech", [])
            duration = exp.get("duration_years")
            
            # Calculate duration if missing
            if duration is None:
                duration = _calculate_duration_from_dates(
                    exp.get("start_date"),
                    exp.get("end_date")
                )
            
            # Determine if this is a tech job
            is_tech_job = False
            
            # Criteria 1: Has tech stack tags
            if tech and len(tech) > 0:
                is_tech_job = True
            
            # Criteria 2: Is in a tech cluster (matches by title/start_date)
            if not is_tech_job and tech_cluster_ids:
                t = str(exp.get("title", "")).lower().strip()
                s = str(exp.get("start_date", "")).strip()
                if f"{t}|{s}" in tech_cluster_ids:
                    is_tech_job = True
            
            # Consider it a tech job if it meets criteria and has duration
            if is_tech_job and duration is not None:
                tech_jobs.append({
                    "company": exp.get("company", "Unknown"),
                    "title": exp.get("title", "Unknown"),
                    "duration": float(duration)
                })
    
    # If no tech jobs found, use all jobs with duration
    if not tech_jobs:
        for exp in experience_list:
            if isinstance(exp, dict):
                duration = exp.get("duration_years")
                
                # Calculate duration if missing
                if duration is None:
                    duration = _calculate_duration_from_dates(
                        exp.get("start_date"),
                        exp.get("end_date")
                    )
                
                if duration is not None:
                    tech_jobs.append({
                        "company": exp.get("company", "Unknown"),
                        "title": exp.get("title", "Unknown"),
                        "duration": float(duration)
                    })
    
    if not tech_jobs:
        return {
            "score": 0.5,
            "average_tenure_years": 0.0,
            "total_jobs": len(experience_list),
            "tech_jobs": 0,
            "short_stints": 0,
            "long_tenures": 0,
            "verdict": "no_duration_data",
            "concerns": ["No duration data available for jobs"],
            "strengths": []
        }
    
    # Calculate metrics
    total_jobs = len(tech_jobs)
    durations = [job["duration"] for job in tech_jobs]
    average_tenure = sum(durations) / len(durations) if durations else 0.0
    
    # Count short stints (< 1.5 years) and long tenures (4+ years)
    short_stints = sum(1 for d in durations if d < 1.5)
    long_tenures = sum(1 for d in durations if d >= 4.0)
    
    # Count medium stints (1.5 - 2.5 years) - frequent movers
    medium_stints = sum(1 for d in durations if 1.5 <= d < 2.5)
    
    # Count very short stints (< 6 months) - more severe
    very_short_stints = sum(1 for d in durations if d < 0.5)
    
    # Start with base score
    base_score = 1.0
    
    concerns = []
    strengths = []
    
    # === PENALTIES ===
    
    # 1. Job Hopping Pattern (3+ jobs in 2 years)
    if total_experience <= 2.0 and total_jobs >= 3:
        base_score -= 0.25
        concerns.append(f"Job hopping: {total_jobs} jobs in ~{total_experience:.1f} years")
    
    # CHANGE: Added penalty for "Early Career Instability" (2 jobs in < 2.5 years where both are short)
    # This catches the case of the user (2 jobs, ~1 year each)
    elif total_experience <= 2.5 and total_jobs == 2 and average_tenure < 1.3:
        base_score -= 0.20
        concerns.append(f"Early career instability: {total_jobs} short roles in ~{total_experience:.1f} years")

    # New: Serial Short Stints for Mid/Senior levels
    # If not junior, and average tenure is low (< 1.8y), penalize significantly
    if seniority_level != "junior" and average_tenure < 1.8:
        base_score -= 0.15
        concerns.append(f"Average tenure ({average_tenure:.1f}y) indicates frequent job changes for {seniority_level} level")

    # 2. Short Stints Penalty (< 1.5 years)
    if short_stints > 0:
        # More severe for multiple short stints
        if short_stints >= 3:
            base_score -= 0.25
            concerns.append(f"Multiple short stints: {short_stints} jobs < 1.5 years")
        elif short_stints == 2:
            # CHANGE: Increased penalty for 2 short stints from 0.15 to 0.20
            base_score -= 0.20
            concerns.append(f"{short_stints} jobs lasted less than 1.5 years")
        else:
            base_score -= 0.10
            concerns.append("1 job lasted less than 1.5 years")
            
    # New: Medium Stints Penalty (Frequent changes every ~2 years)
    if medium_stints >= 2:
        base_score -= 0.10
        concerns.append(f"Pattern of changing jobs every ~2 years ({medium_stints} jobs)")
    
    # 3. Very Short Stints (< 6 months) - Additional Penalty
    if very_short_stints > 0:
        base_score -= 0.10 * very_short_stints
        concerns.append(f"{very_short_stints} job(s) lasted less than 6 months")
    
    # 4. Average Tenure Below Expected
    if average_tenure < expected_tenure:
        ratio = average_tenure / expected_tenure
        if ratio <= 0.5:
            # Significantly below expectations
            base_score -= 0.25
            concerns.append(
                f"Average tenure ({average_tenure:.1f}y) much lower than expected "
                f"for {seniority_level} level ({expected_tenure:.1f}y)"
            )
        elif ratio <= 0.7:
            base_score -= 0.15
            concerns.append(
                f"Average tenure ({average_tenure:.1f}y) below expected "
                f"for {seniority_level} level ({expected_tenure:.1f}y)"
            )
    
    # 5. Frequency of Job Changes (if many jobs in short time)
    if total_jobs >= 3 and total_experience > 0:
        avg_time_per_job = total_experience / total_jobs
        if avg_time_per_job < 2.0:
            base_score -= 0.15
            concerns.append(
                f"High job change frequency: {total_jobs} jobs in {total_experience:.1f} years "
                f"(avg {avg_time_per_job:.1f}y per job)"
            )
    
    # === BONUSES ===
    
    # 1. Long Tenure Bonus (4+ years in one place)
    if long_tenures > 0:
        longest = max(durations)
        base_score += 0.10
        strengths.append(f"Has {long_tenures} long tenure(s) (longest: {longest:.1f} years)")
    
    # 2. Progressive Tenure (each job longer than previous)
    if len(durations) >= 2:
        is_progressive = all(
            durations[i] <= durations[i + 1] 
            for i in range(len(durations) - 1)
        )
        if is_progressive:
            base_score += 0.10
            strengths.append("Progressive career: each role longer than previous")
    
    # 3. Consistent Tenure (2-4 years per role)
    consistent_count = sum(1 for d in durations if 2.0 <= d <= 4.0)
    if consistent_count >= 2:
        base_score += 0.05
        strengths.append(f"{consistent_count} roles with ideal tenure (2-4 years)")
    
    # 4. Above Expected Average
    if average_tenure >= expected_tenure * 1.2:
        base_score += 0.05
        strengths.append(
            f"Average tenure ({average_tenure:.1f}y) exceeds "
            f"{seniority_level} expectations ({expected_tenure:.1f}y)"
        )
    
    # === CLAMP SCORE ===
    final_score = max(0.0, min(1.0, base_score))
    
    # === DETERMINE VERDICT ===
    if final_score >= 0.9:
        verdict = "excellent_stability"
    elif final_score >= 0.8:
        verdict = "good_stability"
    elif final_score >= 0.7:
        verdict = "acceptable_stability"
    elif final_score >= 0.6:
        verdict = "moderate_concerns"
    elif final_score >= 0.5:
        verdict = "significant_concerns"
    else:
        verdict = "severe_stability_issues"
    
    # === LOG DETAILS ===
    logger.info("┌─────────────────────────────────────────────────────────────────┐")
    logger.info("│               EMPLOYMENT STABILITY ANALYSIS                     │")
    logger.info("├─────────────────────────────────────────────────────────────────┤")
    logger.info(f"│ Seniority Level: {seniority_level.upper():<10} (Total Exp: {total_experience:.1f} years)    │")
    logger.info(f"│ Expected Tenure: {expected_tenure:.1f} years                                │")
    logger.info("├─────────────────────────────────────────────────────────────────┤")
    logger.info(f"│ Total Jobs Analyzed: {total_jobs}                                      │")
    logger.info(f"│ Average Tenure: {average_tenure:.1f} years                              │")
    logger.info(f"│ Short Stints (<1yr): {short_stints}                                    │")
    logger.info(f"│ Long Tenures (4+yr): {long_tenures}                                    │")
    logger.info("├─────────────────────────────────────────────────────────────────┤")
    
    if strengths:
        logger.info("│ ✅ STRENGTHS:                                                   │")
        for strength in strengths:
            # Wrap long lines
            if len(strength) <= 58:
                logger.info(f"│   • {strength:<58} │")
            else:
                logger.info(f"│   • {strength[:58]:<58} │")
                logger.info(f"│     {strength[58:116]:<58} │")
    else:
        logger.info("│ ✅ STRENGTHS: None identified                                   │")
    
    logger.info("├─────────────────────────────────────────────────────────────────┤")
    
    if concerns:
        logger.info("│ ⚠️  CONCERNS:                                                   │")
        for concern in concerns:
            # Wrap long lines
            if len(concern) <= 58:
                logger.info(f"│   • {concern:<58} │")
            else:
                logger.info(f"│   • {concern[:58]:<58} │")
                remaining = concern[58:]
                while remaining:
                    logger.info(f"│     {remaining[:58]:<58} │")
                    remaining = remaining[58:]
    else:
        logger.info("│ ⚠️  CONCERNS: None identified                                   │")
    
    logger.info("├─────────────────────────────────────────────────────────────────┤")
    logger.info(f"│ 🎯 STABILITY SCORE: {final_score * 100:>5.1f}% ({verdict.replace('_', ' ').title()})     │")
    logger.info("└─────────────────────────────────────────────────────────────────┘")
    logger.info("")
    
    return {
        "score": round(final_score, 3),
        "average_tenure_years": round(average_tenure, 1),
        "expected_tenure_years": round(expected_tenure, 1),
        "total_jobs": total_jobs,
        "tech_jobs": len([j for j in tech_jobs if j["duration"] > 0]),
        "short_stints": short_stints,
        "long_tenures": long_tenures,
        "seniority_level": seniority_level,
        "verdict": verdict,
        "concerns": concerns,
        "strengths": strengths,
        "job_details": [
            {
                "company": job["company"],
                "title": job["title"],
                "duration_years": round(job["duration"], 1)
            }
            for job in tech_jobs
        ]
    }
