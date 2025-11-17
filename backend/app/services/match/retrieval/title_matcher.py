# Title similarity matching using Jaccard coefficient.
# Fast keyword-based comparison for role alignment scoring.

from __future__ import annotations
from typing import Optional, Dict, Any, Set


def calculate_title_similarity(
    job_title: str,
    resume_title: str
) -> float:
    """
    Calculate title similarity using Jaccard coefficient (0-1 scale).
    
    Jaccard similarity = |A ∩ B| / |A ∪ B|
    
    This is a fast, keyword-based similarity measure that works well for:
    - Role alignment: "Senior Backend Developer" vs "Backend Engineer"
    - Avoiding false matches: "Marketing Manager" vs "Software Engineer" → 0.0
    - Partial matches: "Full Stack Developer" vs "Frontend Developer" → 0.33
    
    Examples:
    - "Senior Python Developer" vs "Python Developer" → 0.67
    - "Backend Engineer" vs "Software Engineer" → 0.5
    - "Data Scientist" vs "Data Analyst" → 0.5
    - "DevOps Engineer" vs "Frontend Developer" → 0.0
    
    Args:
        job_title: Job title string
        resume_title: Resume/candidate title string
        
    Returns:
        Jaccard similarity score (0.0-1.0)
    """
    if not job_title or not resume_title:
        return 0.0
    
    # Normalize and tokenize
    job_words = _normalize_title(job_title)
    resume_words = _normalize_title(resume_title)
    
    if not job_words or not resume_words:
        return 0.0
    
    # Calculate Jaccard similarity
    common_words = job_words & resume_words
    all_words = job_words | resume_words
    
    if not all_words:
        return 0.0
    
    return len(common_words) / len(all_words)


def _normalize_title(title: str) -> Set[str]:
    """
    Normalize title string into set of lowercase tokens.
    
    - Converts to lowercase
    - Splits on whitespace
    - Removes common filler words (junior, senior, etc. kept for now)
    """
    words = set(title.lower().split())
    
    # Optional: Remove very common words that don't add meaning
    # stopwords = {"the", "a", "an", "and", "or"}
    # words = words - stopwords
    
    return words


def calculate_title_match_from_extraction(
    job_analysis: Dict[str, Any],
    resume_extraction: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate title match with full context from job and resume data.
    
    Args:
        job_analysis: Job analysis JSON with role_title
        resume_extraction: Resume extraction JSON with experience array
        
    Returns:
        Dict with score, job_title, resume_title, and matched_words
    """
    # Extract job title
    job_title = job_analysis.get("role_title") or ""
    if not job_title:
        # Fallback to raw job title if analysis doesn't have it
        job_title = job_analysis.get("title") or ""
    
    # Extract most recent resume title
    experiences = resume_extraction.get("experience", [])
    resume_title = ""
    
    if experiences and isinstance(experiences, list) and len(experiences) > 0:
        # Take first (most recent) experience
        first_exp = experiences[0]
        if isinstance(first_exp, dict):
            resume_title = first_exp.get("title") or ""
    
    # Calculate similarity
    score = calculate_title_similarity(job_title, resume_title)
    
    # Find matched words for debugging/explanation
    job_words = _normalize_title(job_title) if job_title else set()
    resume_words = _normalize_title(resume_title) if resume_title else set()
    matched_words = sorted(list(job_words & resume_words))
    
    return {
        "score": round(score, 3),
        "job_title": job_title,
        "resume_title": resume_title,
        "matched_words": matched_words
    }


def calculate_title_match_with_history(
    job_title: str,
    experience_list: list[Dict[str, Any]],
    top_n: int = 3
) -> Dict[str, Any]:
    """
    Calculate title match considering candidate's work history (top N roles).
    
    Takes the best match from recent roles, giving candidates credit for
    relevant past experience even if their current role differs.
    
    Args:
        job_title: Target job title
        experience_list: List of experience dicts with 'title' field
        top_n: Number of recent roles to consider
        
    Returns:
        Dict with best_score, best_matching_title, and all_scores
    """
    if not job_title or not experience_list:
        return {
            "best_score": 0.0,
            "best_matching_title": None,
            "all_scores": []
        }
    
    scores = []
    
    for exp in experience_list[:top_n]:
        if not isinstance(exp, dict):
            continue
        
        resume_title = exp.get("title")
        if not resume_title:
            continue
        
        score = calculate_title_similarity(job_title, resume_title)
        scores.append({
            "title": resume_title,
            "score": round(score, 3)
        })
    
    if not scores:
        return {
            "best_score": 0.0,
            "best_matching_title": None,
            "all_scores": []
        }
    
    # Find best match
    best = max(scores, key=lambda x: x["score"])
    
    return {
        "best_score": best["score"],
        "best_matching_title": best["title"],
        "all_scores": scores
    }
