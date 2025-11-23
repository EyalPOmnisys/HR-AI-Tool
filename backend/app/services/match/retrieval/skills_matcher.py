"""Skills matching using binary weighting model that scores experience-based skills (1.0) higher than general skills (0.6)."""

from __future__ import annotations
from typing import Any, Optional

from app.services.common.skills_normalizer import normalize_skill


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


def _classify_skill_source(source: str) -> tuple[str, float]:
    """
    Classify skill source and return (category, weight).
    
    Binary weighting model:
    - "work_experience": Skills from work experience context (weight=1.0)
    - "general": Skills from any other source (weight=0.6)
    """
    if source in ("work_experience", "experience"):
        return ("work_experience", 1.0)
    return ("general", 0.6)


def calculate_skills_match(
    candidate_skills: list[dict[str, Any]],
    required_skills: list[str],
    nice_to_have_skills: Optional[list[str]] = None
) -> SkillsMatchResult:
    """
    Calculate skills match score using binary weighting model.
    
    Binary Scoring (simplified from schema):
    - Experience skills (from work bullets): weight=1.0 (100% credit)
    - General skills (projects/education/list/etc.): weight=0.6 (60% credit)
    - Nice-to-have skills add bonus (up to 10% extra)
    
    Args:
        candidate_skills: List of skill dicts with {name, source, weight?, category?}
        required_skills: List of required skill names
        nice_to_have_skills: Optional list of nice-to-have skill names
    
    Returns:
        SkillsMatchResult with detailed scoring breakdown
    """
    nice_to_have_skills = nice_to_have_skills or []
    
    # Build candidate skills map: normalized_name -> skill info
    candidate_skills_map = {}
    for skill in candidate_skills:
        if not isinstance(skill, dict):
            continue
        
        name = skill.get("name")
        if not name:
            continue
        
        # Normalize using central normalizer
        norm_name = normalize_skill(name).lower()
        source = skill.get("source", "other")
        
        # Classify source and get weight
        source_category, weight = _classify_skill_source(source)
        
        # Keep the skill with highest weight (prefer work_experience over other)
        if norm_name not in candidate_skills_map:
            candidate_skills_map[norm_name] = {
                "name": name,
                "source": source,
                "source_category": source_category,
                "weight": weight,
                "category": skill.get("category")
            }
        elif weight > candidate_skills_map[norm_name]["weight"]:
            candidate_skills_map[norm_name] = {
                "name": name,
                "source": source,
                "source_category": source_category,
                "weight": weight,
                "category": skill.get("category")
            }
    
    # Match required skills
    matched_required = []
    missing_required = []
    total_required_weight = 0.0
    max_possible_weight = len(required_skills)
    
    for req_skill in required_skills:
        norm_req = normalize_skill(req_skill).lower()
        
        if norm_req in candidate_skills_map:
            matched_skill = candidate_skills_map[norm_req]
            
            matched_required.append({
                "name": matched_skill["name"],
                "source": matched_skill["source"],
                "source_category": matched_skill["source_category"],
                "weight": matched_skill["weight"],
                "category": matched_skill.get("category")
            })
            
            total_required_weight += matched_skill["weight"]
        else:
            missing_required.append(req_skill)
    
    # Calculate base score (0-100)
    if max_possible_weight > 0:
        base_score = (total_required_weight / max_possible_weight) * 100
        required_match_rate = len(matched_required) / max_possible_weight
    else:
        base_score = 100.0
        required_match_rate = 1.0
    
    # Match nice-to-have skills (bonus up to 10 points)
    matched_nice_to_have = []
    bonus_weight = 0.0
    
    for nice_skill in nice_to_have_skills:
        norm_nice = normalize_skill(nice_skill).lower()
        
        if norm_nice in candidate_skills_map:
            matched_skill = candidate_skills_map[norm_nice]
            
            matched_nice_to_have.append({
                "name": matched_skill["name"],
                "source": matched_skill["source"],
                "source_category": matched_skill["source_category"],
                "weight": matched_skill["weight"],
                "category": matched_skill.get("category")
            })
            
            bonus_weight += matched_skill["weight"] * 0.5
    
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
