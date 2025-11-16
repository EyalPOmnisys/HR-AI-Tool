# app/services/resumes/embedding_utils.py
"""
Resume Embedding Utilities - Context enrichment for better semantic search.
Enhances resume chunks with metadata and creates optimized embeddings for candidate matching.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from app.models.resume import Resume, ResumeChunk


def enrich_chunk_for_embedding(
    chunk: ResumeChunk,
    resume: Resume,
    person_name: Optional[str] = None,
    extraction_json: Optional[Dict[str, Any]] = None
) -> str:
    """
    Enrich a chunk with contextual information for better embeddings.
    
    Strategy:
    1. Add section context prefix (what type of information this is)
    2. Add person name if available (for matching)
    3. Add relevant metadata from extraction_json
    4. Keep the original text at the core
    
    This creates more semantically rich embeddings that understand:
    - What kind of information is in the chunk (experience vs skills vs education)
    - Whose resume this is (for identity matching)
    - Context that helps match to job requirements
    """
    parts = []
    
    # 1. Section-specific prefix
    section = (chunk.section or "general").lower()
    section_prefixes = {
        "header": "Candidate Profile:",
        "experience": "Professional Experience:",
        "ניסיון": "ניסיון מקצועי:",
        "education": "Educational Background:",
        "השכלה": "רקע אקדמי:",
        "skills": "Technical Skills and Competencies:",
        "מיומנויות": "מיומנויות וכישורים טכניים:",
        "projects": "Notable Projects:",
        "פרויקטים": "פרויקטים בולטים:",
        "summary": "Professional Summary:",
        "סיכום": "סיכום מקצועי:",
    }
    
    prefix = section_prefixes.get(section, "Resume Content:")
    parts.append(prefix)
    
    # 2. Add person name if available (helps with identity matching)
    if person_name:
        parts.append(f"Candidate: {person_name}")
    
    # 3. Add section-specific context from extraction
    if extraction_json and section in ("experience", "ניסיון"):
        # Add total years of experience for experience sections
        exp_meta = extraction_json.get("experience_meta", {})
        totals = exp_meta.get("totals_by_category", {})
        tech_years = totals.get("tech")
        if tech_years and tech_years > 0:
            parts.append(f"Total Tech Experience: {tech_years} years")
    
    # 4. Add the actual chunk text
    parts.append(chunk.text)
    
    # Join with newlines for readability
    enriched = "\n".join(parts)
    return enriched


def create_search_optimized_embedding_text(resume: Resume) -> str:
    """
    Create a specially optimized text for the full-resume embedding.
    This embedding is used for initial candidate search/filtering.
    
    Focus on:
    - Key identifiable information (name, contact)
    - Technical skills and expertise
    - Years of experience by domain
    - Recent roles and companies
    - Education credentials
    """
    if not resume.extraction_json:
        return resume.parsed_text or ""
    
    extraction = resume.extraction_json
    parts = []
    
    # 1. Person information
    person = extraction.get("person", {})
    if person.get("name"):
        parts.append(f"Candidate: {person['name']}")
    
    # 2. Professional summary - years and domains
    exp_meta = extraction.get("experience_meta", {})
    totals = exp_meta.get("totals_by_category", {})
    
    experience_summary = []
    if totals.get("tech", 0) > 0:
        experience_summary.append(f"{totals['tech']} years technical experience")
    if totals.get("military", 0) > 0:
        experience_summary.append(f"{totals['military']} years military service")
    
    if experience_summary:
        parts.append("Experience: " + ", ".join(experience_summary))
    
    # 3. Key skills (top 20 most relevant)
    skills = extraction.get("skills", [])
    if skills:
        skill_names = [s.get("name") for s in skills[:20] if s.get("name")]
        if skill_names:
            parts.append("Technical Skills: " + ", ".join(skill_names))
    
    # 4. Recent experience (last 2-3 roles)
    experience = extraction.get("experience", [])
    if experience:
        recent_roles = []
        for role in experience[:3]:
            title = role.get("title")
            company = role.get("company")
            if title and company:
                recent_roles.append(f"{title} at {company}")
            elif title:
                recent_roles.append(title)
        
        if recent_roles:
            parts.append("Recent Roles: " + " | ".join(recent_roles))
    
    # 5. Education (top degree)
    education = extraction.get("education", [])
    if education and len(education) > 0:
        top_edu = education[0]
        degree = top_edu.get("degree")
        field = top_edu.get("field")
        institution = top_edu.get("institution")
        
        edu_parts = [x for x in [degree, field, institution] if x]
        if edu_parts:
            parts.append("Education: " + " in ".join(edu_parts))
    
    # 6. Languages
    languages = person.get("languages", [])
    if languages:
        parts.append("Languages: " + ", ".join(languages))
    
    # 7. Append a condensed version of the full text for additional context
    # (truncated to avoid overwhelming the embedding)
    if resume.parsed_text:
        condensed = resume.parsed_text[:2000]  # First 2000 chars
        parts.append("\n--- Full Resume Excerpt ---\n" + condensed)
    
    return "\n\n".join(parts)


def get_embedding_prefix_by_section(section: str) -> str:
    """
    Get a short prefix for embedding based on section type.
    This helps the embedding model understand what type of content to expect.
    """
    section_lower = (section or "").lower()
    
    prefixes = {
        "experience": "work experience: ",
        "ניסיון": "ניסיון תעסוקתי: ",
        "education": "education: ",
        "השכלה": "השכלה: ",
        "skills": "skills: ",
        "מיומנויות": "כישורים: ",
        "projects": "projects: ",
        "summary": "summary: ",
        "header": "profile: ",
    }
    
    return prefixes.get(section_lower, "resume: ")
