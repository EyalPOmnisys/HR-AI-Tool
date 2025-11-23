"""Resume validation service providing quality checks for extraction completeness, data consistency, and embedding quality."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.quality_score: float = 1.0
    
    def add_error(self, message: str):
        self.errors.append(message)
        self.quality_score = max(0.0, self.quality_score - 0.2)
    
    def add_warning(self, message: str):
        self.warnings.append(message)
        self.quality_score = max(0.0, self.quality_score - 0.1)
    
    def add_info(self, message: str):
        self.info.append(message)
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    @property
    def summary(self) -> Dict[str, Any]:
        return {
            "valid": self.is_valid,
            "quality_score": round(self.quality_score, 2),
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


def validate_extraction(extraction: Dict[str, Any]) -> ValidationResult:
    """
    Validate the quality of extracted resume data.
    
    Checks:
    - Required fields present
    - Data consistency (dates, formats)
    - Completeness
    - Data quality indicators
    """
    result = ValidationResult()
    
    if not extraction:
        result.add_error("Extraction is empty")
        return result
    
    # 1. Person validation
    _validate_person(extraction.get("person", {}), result)
    
    # 2. Experience validation
    _validate_experience(extraction.get("experience", []), result)
    
    # 3. Education validation
    _validate_education(extraction.get("education", []), result)
    
    # 4. Skills validation
    _validate_skills(extraction.get("skills", []), result)
    
    # 5. Overall completeness check
    _check_completeness(extraction, result)
    
    return result


def _validate_person(person: Dict[str, Any], result: ValidationResult):
    """Validate person/contact information."""
    if not person:
        result.add_warning("No person information extracted")
        return
    
    # Name check
    name = person.get("name")
    if not name or not isinstance(name, str) or len(name.strip()) < 2:
        result.add_warning("Missing or invalid candidate name")
    
    # Contact information
    emails = person.get("emails", [])
    phones = person.get("phones", [])
    
    if not emails and not phones:
        result.add_warning("No contact information (email/phone) extracted")
    
    # Email format validation
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    for email_obj in emails:
        email = email_obj.get("value") if isinstance(email_obj, dict) else email_obj
        if email and not email_pattern.match(str(email)):
            result.add_warning(f"Suspicious email format: {email}")
    
    # Languages
    languages = person.get("languages", [])
    if not languages:
        result.add_info("No languages specified")
    elif len(languages) < 1:
        result.add_info("Consider adding language proficiency")


def _validate_experience(experience: List[Dict[str, Any]], result: ValidationResult):
    """Validate work experience entries."""
    if not experience or len(experience) == 0:
        result.add_error("No work experience extracted - this is critical for matching")
        return
    
    if len(experience) < 2:
        result.add_warning("Only one experience entry found - resume might be under-parsed")
    
    for idx, role in enumerate(experience):
        if not isinstance(role, dict):
            result.add_error(f"Experience entry {idx} is not a valid object")
            continue
        
        # Title and company
        title = role.get("title")
        company = role.get("company")
        
        if not title and not company:
            result.add_error(f"Experience entry {idx}: missing both title and company")
        elif not title:
            result.add_warning(f"Experience entry {idx}: missing job title")
        elif not company:
            result.add_warning(f"Experience entry {idx}: missing company name")
        
        # Date validation
        start_date = role.get("start_date")
        end_date = role.get("end_date")
        
        if not start_date:
            result.add_warning(f"Experience '{title or 'Unknown'}': missing start date")
        
        # Date ordering
        if start_date and end_date:
            start_parsed = _parse_loose_date(start_date)
            end_parsed = _parse_loose_date(end_date)
            
            if start_parsed and end_parsed and start_parsed > end_parsed:
                result.add_error(f"Experience '{title}': start date after end date")
        
        # Tech stack
        tech = role.get("tech", [])
        if isinstance(tech, list) and len(tech) == 0:
            result.add_info(f"Experience '{title}': no technologies specified")
        
        # Bullets/description
        bullets = role.get("bullets", [])
        if not bullets or len(bullets) == 0:
            result.add_info(f"Experience '{title}': no detailed description")


def _validate_education(education: List[Dict[str, Any]], result: ValidationResult):
    """Validate education entries."""
    if not education or len(education) == 0:
        result.add_info("No education information extracted")
        return
    
    for idx, edu in enumerate(education):
        if not isinstance(edu, dict):
            continue
        
        degree = edu.get("degree")
        institution = edu.get("institution")
        
        if not degree and not institution:
            result.add_warning(f"Education entry {idx}: missing degree and institution")


def _validate_skills(skills: List[Any], result: ValidationResult):
    """Validate skills section."""
    if not skills or len(skills) == 0:
        result.add_warning("No skills extracted - this may impact matching quality")
        return
    
    if len(skills) < 3:
        result.add_warning("Very few skills extracted - resume might be under-parsed")
    
    # Check for duplicate skills (case-insensitive)
    skill_names = []
    for skill in skills:
        if isinstance(skill, dict):
            name = skill.get("name")
        else:
            name = skill
        
        if name and isinstance(name, str):
            skill_names.append(name.lower())
    
    if len(skill_names) != len(set(skill_names)):
        result.add_info("Duplicate skills found - consider deduplication")


def _check_completeness(extraction: Dict[str, Any], result: ValidationResult):
    """Overall completeness check."""
    has_person = bool(extraction.get("person", {}).get("name"))
    has_experience = bool(extraction.get("experience"))
    has_education = bool(extraction.get("education"))
    has_skills = bool(extraction.get("skills"))
    
    completeness_score = sum([has_person, has_experience, has_education, has_skills]) / 4.0
    
    if completeness_score < 0.5:
        result.add_error("Resume extraction is severely incomplete")
    elif completeness_score < 0.75:
        result.add_warning("Resume extraction is partially incomplete")
    else:
        result.add_info(f"Extraction completeness: {int(completeness_score * 100)}%")
    
    # Check experience metadata
    exp_meta = extraction.get("experience_meta", {})
    totals = exp_meta.get("totals_by_category", {})
    
    if not totals or all(v == 0 for v in totals.values()):
        result.add_warning("No experience duration calculated - clustering may have failed")


def _parse_loose_date(date_str: Any) -> Optional[datetime]:
    """Parse various date formats loosely."""
    if not date_str:
        return None
    
    try:
        s = str(date_str).strip().lower()
        if s in ("present", "current", "now"):
            return datetime.now()
        
        # Try year only
        if len(s) == 4 and s.isdigit():
            return datetime(int(s), 1, 1)
        
        # Try various formats
        for fmt in ["%Y-%m-%d", "%Y-%m", "%b %Y", "%B %Y"]:
            try:
                return datetime.strptime(s.title() if "%" in fmt else s, fmt)
            except:
                pass
    except:
        pass
    
    return None


def validate_embedding_quality(embedding: Any) -> ValidationResult:
    """
    Validate the quality of an embedding vector.
    
    Checks:
    - Vector is not null
    - Vector has correct dimensions
    - Vector is not all zeros (degenerate)
    - Vector has reasonable distribution
    """
    result = ValidationResult()
    
    if embedding is None:
        result.add_error("Embedding is None")
        return result
    
    try:
        # Check if it's a list or array-like
        if not hasattr(embedding, '__len__'):
            result.add_error("Embedding is not a vector")
            return result
        
        length = len(embedding)
        
        # Check expected dimensions (1536 for OpenAI text-embedding-3-small)
        if length not in [1536, 3072, 768]:
            result.add_warning(f"Unexpected embedding dimension: {length}")
        
        # Check for all zeros (degenerate)
        if all(v == 0 for v in embedding):
            result.add_error("Embedding is all zeros (degenerate)")
        
        # Check for reasonable distribution (not all values the same)
        unique_values = len(set(float(v) for v in embedding[:100]))  # Sample first 100
        if unique_values < 5:
            result.add_warning("Embedding has very low variance")
        
        result.add_info(f"Embedding dimension: {length}, unique values (sample): {unique_values}")
        
    except Exception as e:
        result.add_error(f"Error validating embedding: {e}")
    
    return result


def create_quality_report(extraction: Dict[str, Any], embedding: Any = None) -> Dict[str, Any]:
    """
    Create a comprehensive quality report for resume processing.
    
    Returns a report with validation results and recommendations.
    """
    extraction_validation = validate_extraction(extraction)
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "extraction": extraction_validation.summary,
    }
    
    if embedding is not None:
        embedding_validation = validate_embedding_quality(embedding)
        report["embedding"] = embedding_validation.summary
    
    # Overall assessment
    overall_valid = extraction_validation.is_valid
    overall_quality = extraction_validation.quality_score
    
    if embedding is not None:
        overall_quality = (overall_quality + validate_embedding_quality(embedding).quality_score) / 2
    
    report["overall"] = {
        "valid": overall_valid,
        "quality_score": round(overall_quality, 2),
        "status": _get_status_label(overall_quality),
    }
    
    # Recommendations
    recommendations = []
    if not overall_valid:
        recommendations.append("Resume processing has critical errors - review extraction results")
    if overall_quality < 0.7:
        recommendations.append("Quality is below threshold - consider re-processing or manual review")
    if not extraction.get("experience"):
        recommendations.append("Missing work experience - this resume may not be suitable for matching")
    
    report["recommendations"] = recommendations
    
    return report


def _get_status_label(quality_score: float) -> str:
    """Get human-readable status label for quality score."""
    if quality_score >= 0.9:
        return "excellent"
    elif quality_score >= 0.75:
        return "good"
    elif quality_score >= 0.6:
        return "acceptable"
    elif quality_score >= 0.4:
        return "poor"
    else:
        return "critical"
