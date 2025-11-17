# Deterministic skills matching algorithm with weighted scoring.
# Compares candidate skills against job requirements using source-based weights.

from __future__ import annotations
from typing import Any, Optional


class SkillsMatchResult:
    """Result of skills matching calculation."""
    
    def __init__(
        self,
        score: float,
        required_match_rate: float,
        matched_required: list[dict[str, Any]],
        missing_required: list[str],
        matched_nice_to_have: list[dict[str, Any]],
        weighted_score: float,
        details: dict[str, Any]
    ):
        self.score = score
        self.required_match_rate = required_match_rate
        self.matched_required = matched_required
        self.missing_required = missing_required
        self.matched_nice_to_have = matched_nice_to_have
        self.weighted_score = weighted_score
        self.details = details
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "required_match_rate": round(self.required_match_rate, 2),
            "matched_required": self.matched_required,
            "missing_required": self.missing_required,
            "matched_nice_to_have": self.matched_nice_to_have,
            "weighted_score": round(self.weighted_score, 2),
            "details": self.details
        }


def calculate_skills_match(
    candidate_skills: list[dict[str, Any]],
    required_skills: list[str],
    nice_to_have_skills: Optional[list[str]] = None
) -> SkillsMatchResult:
    """
    Calculate deterministic skills match score with source-based weighting.
    
    Scoring logic:
    - Each required skill matched with weight 1.0 (work_experience) = 100% credit
    - Each required skill matched with weight 0.4 (skills_list) = 40% credit
    - Nice-to-have skills add bonus points (up to 10% extra)
    - Final score normalized to 0-100 range
    
    Args:
        candidate_skills: List of skill dicts with {name, source, weight, category}
        required_skills: List of required skill names
        nice_to_have_skills: Optional list of nice-to-have skill names
    
    Returns:
        SkillsMatchResult with detailed scoring breakdown
    """
    nice_to_have_skills = nice_to_have_skills or []
    
    # Normalize skill names for comparison (case-insensitive)
    def normalize(name: str) -> str:
        return name.strip().lower()
    
    # Build candidate skills map: normalized_name -> best skill item
    candidate_skills_map = {}
    for skill in candidate_skills:
        if not isinstance(skill, dict):
            continue
        
        name = skill.get("name")
        if not name:
            continue
        
        norm_name = normalize(name)
        weight = skill.get("weight", 0.4)
        
        # Keep the skill with highest weight
        if norm_name not in candidate_skills_map or weight > candidate_skills_map[norm_name]["weight"]:
            candidate_skills_map[norm_name] = skill
    
    # Match required skills
    matched_required = []
    missing_required = []
    total_required_weight = 0.0
    max_possible_weight = len(required_skills)
    
    for req_skill in required_skills:
        norm_req = normalize(req_skill)
        
        if norm_req in candidate_skills_map:
            matched_skill = candidate_skills_map[norm_req]
            weight = matched_skill.get("weight", 0.4)
            source = matched_skill.get("source", "skills_list")
            
            matched_required.append({
                "name": matched_skill.get("name"),
                "source": source,
                "weight": weight,
                "category": matched_skill.get("category")
            })
            
            total_required_weight += weight
        else:
            missing_required.append(req_skill)
    
    # Calculate base score (0-100)
    if max_possible_weight > 0:
        base_score = (total_required_weight / max_possible_weight) * 100
        required_match_rate = len(matched_required) / max_possible_weight
    else:
        base_score = 100.0  # No requirements = perfect match
        required_match_rate = 1.0
    
    # Match nice-to-have skills (bonus up to 10 points)
    matched_nice_to_have = []
    bonus_weight = 0.0
    
    for nice_skill in nice_to_have_skills:
        norm_nice = normalize(nice_skill)
        
        if norm_nice in candidate_skills_map:
            matched_skill = candidate_skills_map[norm_nice]
            weight = matched_skill.get("weight", 0.4)
            
            matched_nice_to_have.append({
                "name": matched_skill.get("name"),
                "source": matched_skill.get("source", "skills_list"),
                "weight": weight,
                "category": matched_skill.get("category")
            })
            
            bonus_weight += weight * 0.5  # Each nice-to-have worth 50% of required
    
    # Calculate bonus score (capped at 10 points)
    bonus_score = min(bonus_weight * 10, 10.0)
    
    # Final weighted score
    weighted_score = min(base_score + bonus_score, 100.0)
    
    # Simple score (percentage of required skills matched, ignoring weights)
    simple_score = (len(matched_required) / max_possible_weight * 100) if max_possible_weight > 0 else 100.0
    
    # Details for debugging/analysis
    details = {
        "total_required": len(required_skills),
        "total_matched": len(matched_required),
        "total_missing": len(missing_required),
        "total_nice_to_have": len(nice_to_have_skills),
        "matched_nice_to_have_count": len(matched_nice_to_have),
        "base_score": round(base_score, 2),
        "bonus_score": round(bonus_score, 2),
        "simple_match_percentage": round(simple_score, 2)
    }
    
    return SkillsMatchResult(
        score=simple_score,  # Use simple score as main score
        required_match_rate=required_match_rate,
        matched_required=matched_required,
        missing_required=missing_required,
        matched_nice_to_have=matched_nice_to_have,
        weighted_score=weighted_score,
        details=details
    )


def calculate_skills_match_by_category(
    candidate_skills: list[dict[str, Any]],
    required_skills_by_category: dict[str, list[str]],
    nice_to_have_by_category: Optional[dict[str, list[str]]] = None
) -> dict[str, Any]:
    """
    Calculate skills match broken down by category (e.g., backend, frontend, devops).
    
    Args:
        candidate_skills: List of skill dicts with {name, source, weight, category}
        required_skills_by_category: Dict of category -> list of required skills
        nice_to_have_by_category: Optional dict of category -> list of nice-to-have skills
    
    Returns:
        Dict with overall score and per-category breakdown
    """
    nice_to_have_by_category = nice_to_have_by_category or {}
    
    category_results = {}
    total_weight = 0.0
    total_possible = 0.0
    
    for category, required_skills in required_skills_by_category.items():
        nice_to_have = nice_to_have_by_category.get(category, [])
        
        result = calculate_skills_match(
            candidate_skills=candidate_skills,
            required_skills=required_skills,
            nice_to_have_skills=nice_to_have
        )
        
        category_results[category] = result.to_dict()
        
        # Weight categories equally for overall score
        total_weight += result.weighted_score
        total_possible += 100.0
    
    overall_score = (total_weight / total_possible * 100) if total_possible > 0 else 0.0
    
    return {
        "overall_score": round(overall_score, 2),
        "categories": category_results
    }
