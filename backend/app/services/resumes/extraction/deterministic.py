"""Safe rule-based resume extraction for contacts, sections, languages, and skills without inference or guessing to avoid false positives."""
# -----------------------------------------------------------------------------
# PURPOSE (English-only comments)
# - "Safe-only" deterministic signals to avoid introducing wrong facts:
#   * Contacts (emails, phones with IL normalization, urls, profiles)
#   * Section boundaries (provenance), Languages (light), Skills (dictionary-based)
# - NO inference for education/experience titles/dates to avoid mistakes (e.g., "MA" from "May").
# - Leaves education/experience to the LLM. This ensures fewer false positives and better consistency.
# - UPDATE: Expanded TECH_DICT to cover common items seen in resumes (e.g., NestJS, Cesium, OpenLayers, Git, Jenkins, Linux, OpenShift, Splunk, HTML, CSS).
# -----------------------------------------------------------------------------
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.services.common.skills_normalizer import normalize_skill

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_CANDIDATE_RE = re.compile(r"(?:(?<!\d)\+?\d[\d\s().\-]{7,}\d(?!\d))")
YEAR_RANGE_RE = re.compile(r"^\s*\d{4}\s*[-–—]\s*\d{4}\s*$")
URL_RE = re.compile(r"https?://[^\s)\]]+", re.I)
LINKEDIN_RE = re.compile(r"https?://(www\.)?linkedin\.com/[^\s)\]]+", re.I)
GITHUB_RE = re.compile(r"https?://(www\.)?github\.com/[^\s)\]]+", re.I)

SECTION_RE = re.compile(
    r"^\s*(experience|education|skills(?:\s*&\s*abilities)?|projects|summary|languages|certifications|achievements|"
    r"ניסיון|השכלה|מיומנויות|פרויקטים|סיכום|שפות|הסמכות)\s*[:\-]?\s*$",
    re.I,
)

# NOTE: keys are raw mentions (lowercase); values are properly capitalized display names
TECH_DICT = {
    # languages & frameworks
    "python": "Python", "py": "Python", "r": "R", "java": "Java",
    "c#": "C#", "csharp": "C#", "c++": "C++", "go": "Go",
    "javascript": "JavaScript", "typescript": "TypeScript", "ts": "TypeScript",
    "php": "PHP", "ruby": "Ruby", "scala": "Scala", "rust": "Rust",

    # front-end
    "react": "React", "vue": "Vue", "angular": "Angular",
    "nextjs": "Next.js", "tailwind": "Tailwind",
    "html": "HTML", "html5": "HTML", "css": "CSS", "css3": "CSS",

    # node ecosystem & back-end
    "node": "Node.js", "node js": "Node.js", "node.js": "Node.js", "express": "Express",
    "nest": "NestJS", "nestjs": "NestJS", "spring": "Spring",
    ".net": ".NET", "dotnet": ".NET", "django": "Django", "flask": "Flask", "fastapi": "FastAPI",

    # data & ml
    "pandas": "Pandas", "numpy": "NumPy", "scikit-learn": "Scikit-learn",
    "xgboost": "XGBoost", "lightgbm": "LightGBM", "spark": "Spark", "airflow": "Airflow",

    # mapping/3D
    "cesium": "Cesium", "openlayers": "OpenLayers",

    # databases
    "sql": "SQL", "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "mysql": "MySQL", "mongodb": "MongoDB",

    # devops & infra
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "git": "Git", "jenkins": "Jenkins", "linux": "Linux",
    "openshift": "OpenShift", "splunk": "Splunk",

    # clouds
    "aws": "AWS", "gcp": "GCP", "azure": "Azure",
}

LANGUAGE_WORDS = {"hebrew", "english", "arabic", "russian", "french", "spanish", "german"}


def _find_all(pattern: re.Pattern, text: str) -> List[Tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in pattern.finditer(text)]


def _collect_sections(text: str) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    current = {"title": "general", "start": 0}
    lines = text.splitlines()
    offset = 0
    for line in lines:
        if SECTION_RE.match(line.strip()):
            current["end"] = offset + len(line)
            sections.append(current)
            title = SECTION_RE.match(line.strip()).group(1).strip().lower()
            current = {"title": title, "start": offset + len(line)}
        offset += len(line) + 1
    current["end"] = len(text)
    sections.append(current)
    return sections


def _extract_basic_contacts(text: str) -> Dict[str, Any]:
    emails = _find_all(EMAIL_RE, text)

    phones: List[Tuple[str, int, int]] = []
    for raw, s, e in _find_all(PHONE_CANDIDATE_RE, text):
        raw_span = text[s:e].strip()
        if YEAR_RANGE_RE.match(raw_span):
            continue
        # Normalize: keep leading '+' if present, then digits only
        norm = re.sub(r"[^\d+]", "", raw_span)
        if norm.startswith("+"):
            digits = re.sub(r"\D", "", norm)
            norm = "+" + digits
        else:
            digits = re.sub(r"\D", "", norm)
            # IL normalization: if starts with 0 and length 9–10 → +972 without the leading 0
            if digits.startswith("0") and 8 <= len(digits) - 1 <= 9:
                norm = "+972" + digits[1:]
            else:
                norm = "+" + digits
        digit_count = len(re.sub(r"\D", "", norm))
        if 8 <= digit_count <= 16:
            phones.append((norm, s, e))

    links = _find_all(URL_RE, text)
    linkedin = _find_all(LINKEDIN_RE, text)
    github = _find_all(GITHUB_RE, text)

    def pack(items: List[Tuple[str, int, int]], kind: str) -> List[Dict[str, Any]]:
        return [
            {
                "type": kind,
                "value": value,
                "provenance": {"char_start": start, "char_end": end},
                "confidence": 0.98,
            }
            for (value, start, end) in items
        ]

    return {
        "emails": pack(emails, "email"),
        "phones": pack(phones, "phone"),
        "links": pack(links, "url"),
        "profiles": pack(linkedin, "linkedin") + pack(github, "github"),
    }


def _extract_languages(text: str) -> List[str]:
    found = set()
    for lang in LANGUAGE_WORDS:
        if re.search(rf"\b{re.escape(lang)}\b", text, flags=re.I):
            found.add(lang.capitalize())
    return sorted(found)


# Removed: _normalize_skill_name - now using centralized normalize_skill() from skills_normalizer


def _extract_skills(text: str) -> List[Dict[str, Any]]:
    """Extract skills with unified format: name, source, weight, category.
    
    Uses centralized TECH_DICT and normalize_skill() for perfect consistency.
    """
    found: Dict[str, int] = {}  # Track occurrence count per normalized skill
    for raw, canonical in TECH_DICT.items():
        pattern = r"(?<![A-Za-z0-9+])" + re.escape(raw) + r"(?![A-Za-z0-9+])"
        for match in re.finditer(pattern, text, flags=re.I):
            # Normalize through central normalizer for consistency
            normalized = normalize_skill(canonical)
            found[normalized] = found.get(normalized, 0) + 1
    
    skills: List[Dict[str, Any]] = []
    for norm, _count in found.items():
        # Deterministic skills are always general (binary model: general=0.6)
        skills.append({
            "name": norm,
            "source": "deterministic",
            "weight": 0.6,
            "category": None
        })
    return skills


def _extract_candidate_name_heuristic(text: str) -> str | None:
    """
    Simple heuristic to guess the candidate name from the first few lines.
    Rules:
    - Look at first 3 non-empty lines.
    - Candidate must be 2-4 words.
    - Must not contain digits, emails, or common header words (Resume, CV, etc).
    - Must be mostly letters (Hebrew or English).
    - UPDATE: If name contains Hebrew, return None to force LLM translation.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    
    # Common words to avoid
    blocklist = {"resume", "cv", "curriculum", "vitae", "profile", "summary", "contact", "phone", "email", "address", "קורות", "חיים"}
    
    for line in lines[:3]:
        # Clean up common separators like " - " or " | "
        clean_line = re.sub(r"[\-\|•]", " ", line).strip()
        
        words = clean_line.split()
        if 2 <= len(words) <= 4:
            # Check if words are valid (no numbers, no symbols)
            if all(w.replace("-", "").isalpha() for w in words):
                # Check against blocklist
                if not any(w.lower() in blocklist for w in words):
                    # Check for Hebrew characters
                    if re.search(r"[\u0590-\u05FF]", clean_line):
                        return None  # Force LLM to handle translation
                    return clean_line
                    
    return None


def extract_deterministic_safe(parsed_text: str) -> Dict[str, Any]:
    """
    Safe-only extraction (no risky inference):
    - person: emails/phones/links/profiles/languages (no name/date/location guesses)
    - skills: normalized dictionary hits
    - sections: provenance bounds
    - education/experience: omitted (LLM will fill)
    """
    sections = _collect_sections(parsed_text)
    contacts = _extract_basic_contacts(parsed_text)
    langs = _extract_languages(parsed_text)
    skills = _extract_skills(parsed_text)
    
    # Try to find a name candidate to help the LLM
    name_candidate = _extract_candidate_name_heuristic(parsed_text)

    return {
        "person": {
            "name": name_candidate,
            "emails": contacts["emails"],
            "phones": contacts["phones"],
            "links": contacts["links"],
            "profiles": contacts["profiles"],
            "languages": langs or None,
            "confidence_details": {"languages": 0.7 if langs else 0.0},
        },
        "skills": skills,
        "sections": sections,
        "education": None,   # leave to LLM
        "experience": None,  # leave to LLM
        "confidence": {"person": 0.9, "skills": 0.85, "education": 0.0, "experience": 0.0},
        "provenance": {"root": {"char_start": 0, "char_end": len(parsed_text)}},
    }
