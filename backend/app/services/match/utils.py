# app/services/match/utils.py
"""
Match Utilities - Generic helper functions for matching calculations.
Provides embedding generation, similarity scoring, and skills matching using AI/semantic methods.
All logic is generic and relies on embeddings rather than hard-coded rules.
"""
import numpy as np
from typing import List, Set
import logging

from app.services.common.embedding_client import OpenAIEmbeddingClient

logger = logging.getLogger("match.utils")


def format_experience_years(years: float | None) -> str | None:
    """Format experience years for display."""
    if years is None:
        return None
    if years < 1:
        return "<1 yr"
    if years % 1 == 0:
        return f"{int(years)} yrs"
    return f"{years:.1f} yrs"


def get_embedding(text: str) -> np.ndarray:
    """
    Get embedding vector for text using the embedding client.
    
    Args:
        text: Text to embed
        
    Returns:
        Numpy array of embedding vector
    """
    client = OpenAIEmbeddingClient()
    embedding = client.embed(text)
    return np.array(embedding)


def cosine_similarity(vec1: np.ndarray | list, vec2: np.ndarray | list) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector (numpy array or list)
        vec2: Second vector (numpy array or list)
        
    Returns:
        Similarity score between 0 and 1
    """
    # Convert to numpy arrays if needed
    v1 = np.array(vec1) if not isinstance(vec1, np.ndarray) else vec1
    v2 = np.array(vec2) if not isinstance(vec2, np.ndarray) else vec2
    
    # Calculate cosine similarity
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    
    similarity = dot_product / (norm_v1 * norm_v2)
    
    # Clamp to [0, 1] range (handle floating point errors)
    return float(max(0.0, min(1.0, similarity)))


def calculate_skills_similarity(
    job_skills_must: Set[str],
    job_skills_nice: Set[str],
    resume_skills: Set[str]
) -> float:
    """
    Calculate skills match using exact matching only.
    Fast and efficient - no API calls, pure string matching.
    Let the LLM Judge handle nuanced transferable skills evaluation.
    
    Strategy:
    - Exact match = 1.0 (perfect match)
    - No match = 0.0 (not present)
    
    Args:
        job_skills_must: Set of must-have skills from job (lowercase)
        job_skills_nice: Set of nice-to-have skills from job (lowercase)
        resume_skills: Set of skills from resume (lowercase)
        
    Returns:
        Skills match score between 0 and 1
    """
    if not job_skills_must and not job_skills_nice:
        return 1.0
    
    if not job_skills_must:
        # Only nice-to-haves, give high base score
        if not job_skills_nice:
            return 1.0
        nice_match = len(job_skills_nice & resume_skills) / len(job_skills_nice)
        return 0.8 + (0.2 * nice_match)
    
    # Normalize all skills for comparison
    job_must_normalized = {s.lower().strip() for s in job_skills_must}
    resume_normalized = {s.lower().strip() for s in resume_skills}
    
    # Count exact matches only - fast and simple
    exact_matches = len(job_must_normalized & resume_normalized)
    must_have_score = exact_matches / len(job_must_normalized) if job_must_normalized else 1.0
    
    # Bonus for nice-to-have skills
    if job_skills_nice:
        nice_normalized = {s.lower().strip() for s in job_skills_nice}
        nice_exact = len(nice_normalized & resume_normalized)
        nice_bonus = (nice_exact / len(nice_normalized)) * 0.10
        final_score = min(1.0, must_have_score + nice_bonus)
    else:
        final_score = must_have_score
    
    # Log for debugging
    logger.debug(
        f"Skills: {exact_matches}/{len(job_must_normalized)} exact matches → {final_score:.2f}"
    )
    
    return float(final_score)

