"""Hybrid title matching combining semantic embeddings with keyword analysis and role knowledge base to match job titles across work history."""

from __future__ import annotations
import numpy as np
from typing import List, Optional, Dict, Any, Set
import requests
import logging

from app.core.config import settings
from app.services.match.retrieval.tech_roles_knowledge import get_role_similarity_boost

logger = logging.getLogger("match.title")


class TitleMatcher:
    """
    Hybrid title matching combining semantic embeddings with keyword analysis.
    Works for ANY job titles without manual configuration.
    
    Uses two-stage matching:
    1. Semantic similarity via Ollama embeddings (base score 0-100)
    2. Keyword overlap boost for technical terms (+0-30 bonus)
    
    Automatically handles:
    - Synonyms: "Developer" ↔ "Engineer"
    - Role variations: "Full Stack" ↔ "Software Engineer"
    - Seniority levels: "Senior", "Junior", "Lead"
    - Word order and typos
    """

    @staticmethod
    def get_embedding_from_ollama(text: str) -> np.ndarray:
        """Get embedding from Ollama server"""
        try:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": settings.SENTENCE_TRANSFORMER_MODEL,
                    "prompt": text
                },
                timeout=30
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            return np.array(embedding)
        except Exception as e:
            logger.error(f"Failed to get embedding from Ollama: {e}")
            raise

    @staticmethod
    def normalize_title(title: str) -> str:
        """Basic normalization of title text"""
        if not title:
            return ""
        # Just clean up extra spaces and basic formatting
        return ' '.join(title.strip().split())

    @staticmethod
    def extract_key_terms(title: str) -> Set[str]:
        """
        Extract key technical terms and roles from title.
        These are weighted heavily in matching.
        """
        title_lower = title.lower()
        
        # Key role indicators
        roles = {
            'engineer', 'developer', 'programmer', 'architect',
            'lead', 'manager', 'director', 'analyst', 'specialist',
            'consultant', 'scientist', 'researcher', 'designer'
        }
        
        # Technical domains
        domains = {
            'software', 'full stack', 'fullstack', 'backend', 'frontend',
            'web', 'mobile', 'cloud', 'data', 'machine learning', 'ml',
            'devops', 'qa', 'test', 'security', 'network', 'database',
            'embedded', 'systems', 'platform', 'infrastructure'
        }
        
        # Seniority levels
        levels = {
            'senior', 'sr', 'junior', 'jr', 'lead', 'principal',
            'staff', 'chief', 'head', 'entry', 'associate'
        }
        
        found_terms = set()
        
        # Check for exact matches (order matters for multi-word)
        for term in domains | roles | levels:
            if term in title_lower:
                found_terms.add(term)
        
        return found_terms

    @staticmethod
    def compute_keyword_boost(job_title: str, resume_title: str) -> float:
        """
        Calculate keyword-based boost for similar technical terms.
        Now uses comprehensive knowledge base for ALL high-tech roles.
        Returns 0-30 (bonus points to add to semantic score).
        """
        # Step 1: Check knowledge base for role category matching
        # This handles: DevOps ↔ SRE, Data Scientist ↔ ML Engineer, etc.
        kb_boost = get_role_similarity_boost(job_title, resume_title)
        
        # Step 2: Keyword overlap analysis (legacy logic as fallback)
        job_terms = TitleMatcher.extract_key_terms(job_title)
        resume_terms = TitleMatcher.extract_key_terms(resume_title)
        
        keyword_boost = 0.0
        if job_terms and resume_terms:
            # Check for key overlaps
            overlap = job_terms & resume_terms
            
            # Strong signals (core technical roles)
            strong_matches = {
                'engineer', 'developer', 'programmer', 'architect',
                'software', 'full stack', 'fullstack', 'backend', 'frontend'
            }
            
            # Both have strong role indicators (engineer/developer/etc)
            job_has_strong = bool(job_terms & strong_matches)
            resume_has_strong = bool(resume_terms & strong_matches)
            
            if job_has_strong and resume_has_strong:
                # Both are technical roles - strong boost!
                base_boost = 20.0
                overlap_bonus = len(overlap) * 2.0
                keyword_boost = min(30.0, base_boost + overlap_bonus)
            elif overlap:
                # Partial match
                base_boost = 10.0
                overlap_bonus = len(overlap) * 2.0
                keyword_boost = min(20.0, base_boost + overlap_bonus)
        
        # Step 3: Use the MAXIMUM of knowledge base and keyword boost
        # This ensures we get best signal from either approach
        final_boost = max(kb_boost, keyword_boost)
        
        if final_boost > 0:
            logger.debug(
                f"Keyword boost: KB={kb_boost:.1f}, Keywords={keyword_boost:.1f}, Final={final_boost:.1f}"
            )
        
        return final_boost

    @staticmethod
    def compute_semantic_similarity(text1: str, text2: str, embedder=None) -> float:
        """
        Compute semantic similarity between two texts using Ollama embeddings.
        
        Args:
            text1: First text (job title)
            text2: Second text (resume title)
            embedder: Ignored (kept for compatibility)
        
        Returns:
            Similarity score 0-100 (cosine similarity normalized)
        """
        if not text1 or not text2:
            return 0.0

        try:
            # Normalize texts
            t1 = TitleMatcher.normalize_title(text1)
            t2 = TitleMatcher.normalize_title(text2)

            # Get embeddings from Ollama
            emb1 = TitleMatcher.get_embedding_from_ollama(t1)
            emb2 = TitleMatcher.get_embedding_from_ollama(t2)

            # Cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            # Cosine similarity (-1 to 1)
            cosine_sim = dot_product / (norm1 * norm2)
            
            # Convert to 0-100 scale
            # Cosine similarity of 1.0 (identical) = 100
            # Cosine similarity of 0.0 (unrelated) = 0
            # Negative values (opposite meaning) = 0
            score = max(0.0, cosine_sim) * 100

            return round(score, 1)

        except Exception as e:
            logger.error(f"Error computing semantic similarity: {e}")
            return 0.0

    @staticmethod
    def compute_detailed_match(
        job_title: str,
        resume_titles: List[str],
        embedder=None
    ) -> Dict[str, Any]:
        """
        Compute best title match and return detailed results.
        
        Returns:
            Dict with 'score', 'best_title', and 'all_matches'
        """
        if not job_title or not resume_titles:
            return {
                "score": 0.0,
                "best_title": "",
                "all_matches": []
            }

        # embedder parameter ignored - kept for compatibility

        # Find best matching title from resume
        best_score = 0.0
        best_title = ""
        all_matches = []

        for resume_title in resume_titles:
            if not resume_title or not resume_title.strip():
                continue

            # 1. Semantic similarity (base score 0-100)
            semantic_score = TitleMatcher.compute_semantic_similarity(
                job_title,
                resume_title,
                None
            )
            
            # 2. Keyword boost (0-30 bonus points)
            keyword_boost = TitleMatcher.compute_keyword_boost(
                job_title,
                resume_title
            )
            
            # 3. Combined score (capped at 100)
            combined_score = min(100.0, semantic_score + keyword_boost)
            
            all_matches.append({
                "title": resume_title,
                "semantic_score": semantic_score,
                "keyword_boost": keyword_boost,
                "final_score": combined_score
            })
            
            if combined_score > best_score:
                best_score = combined_score
                best_title = resume_title
                
        # Log best match for debugging
        if best_title:
            logger.debug(
                f"Title match: '{job_title}' ↔ '{best_title}' = {best_score:.1f}%"
            )

        return {
            "score": best_score,
            "best_title": best_title,
            "all_matches": all_matches
        }

    @staticmethod
    def compute_title_match(
        job_title: str,
        resume_titles: List[str],
        embedder=None
    ) -> float:
        """
        Compute best title match using HYBRID approach:
        1. Semantic similarity (base score 0-100)
        2. Keyword matching boost (+0-30)
        
        Args:
            job_title: The job title to match against
            resume_titles: List of job titles from the resume
            embedder: Ignored (kept for compatibility)
            
        Returns:
            Best match score 0-100
        """
        result = TitleMatcher.compute_detailed_match(job_title, resume_titles, None)
        return result["score"]


# Legacy function signatures for backward compatibility
def calculate_title_similarity(job_title: str, resume_title: str) -> float:
    """
    Legacy function - uses semantic similarity now instead of Jaccard.
    Returns score on 0-1 scale for compatibility.
    """
    score_100 = TitleMatcher.compute_title_match(job_title, [resume_title])
    return score_100 / 100.0


def calculate_title_match_from_extraction(
    job_analysis: Dict[str, Any],
    resume_extraction: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate title match with full context from job and resume data.
    Now uses semantic similarity instead of Jaccard.
    
    Args:
        job_analysis: Job analysis JSON with role_title
        resume_extraction: Resume extraction JSON with experience array
        
    Returns:
        Dict with score, job_title, resume_title, and semantic similarity
    """
    # Extract job title
    job_title = job_analysis.get("role_title") or ""
    if not job_title:
        # Fallback to raw job title if analysis doesn't have it
        job_title = job_analysis.get("title") or ""
    
    # Extract all resume titles from work history
    experiences = resume_extraction.get("experience", [])
    resume_titles = []
    
    if experiences and isinstance(experiences, list):
        for exp in experiences[:3]:  # Check top 3 recent roles
            if isinstance(exp, dict):
                title = exp.get("title")
                if title:
                    resume_titles.append(title)
    
    # Calculate best match using semantic similarity
    score_100 = TitleMatcher.compute_title_match(job_title, resume_titles)
    score = score_100 / 100.0  # Convert to 0-1 scale
    
    # Get best matching title for display
    best_resume_title = resume_titles[0] if resume_titles else ""
    
    return {
        "score": round(score, 3),
        "job_title": job_title,
        "resume_title": best_resume_title,
        "matched_words": []  # Not applicable for semantic matching
    }

def calculate_title_match_with_history(
    job_title: str,
    experience_list: list[Dict[str, Any]],
    candidate_profession: Optional[str] = None,
    top_n: int = 3
) -> Dict[str, Any]:
    """
    Calculate title match considering candidate's work history AND their primary profession.
    
    Args:
        job_title: Target job title
        experience_list: List of experience dicts with 'title' field
        candidate_profession: The primary profession displayed in the frontend
        top_n: Number of recent roles to consider
        
    Returns:
        Dict with best_score, best_matching_title, best_source, and all_scores
    """
    if not job_title:
        return {
            "best_score": 0.0,
            "best_matching_title": None,
            "best_source": None,
            "all_scores": []
        }
    
    # 1. Collect all titles to check
    titles_to_check = []
    
    # A. Primary Profession (High Priority - matches Frontend)
    if candidate_profession and candidate_profession.strip():
        titles_to_check.append({
            "title": candidate_profession.strip(),
            "source": "primary_profession"
        })

    # B. Recent History
    if experience_list:
        for exp in experience_list[:top_n]:
            if not isinstance(exp, dict):
                continue
            
            t = exp.get("title")
            if t and t.strip():
                # Avoid duplicates if profession matches recent role
                if not any(x["title"].lower() == t.strip().lower() for x in titles_to_check):
                    titles_to_check.append({
                        "title": t.strip(),
                        "source": "history"
                    })
    
    if not titles_to_check:
        return {
            "best_score": 0.0,
            "best_matching_title": None,
            "best_source": None,
            "all_scores": []
        }
    
    # 2. Calculate scores
    scores = []
    
    for item in titles_to_check:
        title_text = item["title"]
        source = item["source"]
        
        # Use detailed match logic
        res = TitleMatcher.compute_detailed_match(job_title, [title_text], None)
        score_val = round(res["score"], 1)
        
        scores.append({
            "title": title_text,
            "score": score_val,
            "source": source
        })
        
        # Debug log
        source_label = "⭐ (Primary)" if source == "primary_profession" else "(History)"
        logger.debug(f"Checking title {source_label}: '{title_text}' = {score_val}%")
    
    # 3. Find best match
    best = max(scores, key=lambda x: x["score"])
    
    return {
        "best_score": best["score"],
        "best_matching_title": best["title"],
        "best_source": best.get("source"),
        "all_scores": scores
    }
