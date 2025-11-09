# app/services/resumes/extraction/deterministic.py
# -----------------------------------------------------------------------------
# PURPOSE (English-only comments)
# - "Safe-only" deterministic signals to avoid introducing wrong facts:
#   * Contacts (emails, phones with IL normalization, urls, profiles)
#   * Section boundaries (provenance), Languages (light), Skills (dictionary-based)
# - NO inference for education/experience titles/dates to avoid mistakes (e.g., "MA" from "May").
# - Leaves education/experience to the LLM. This ensures fewer false positives and better consistency.
# -----------------------------------------------------------------------------
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_CANDIDATE_RE = re.compile(r"(?:(?<!\d)\+?\d[\d\s().\-]{7,}\d(?!\d))")
YEAR_RANGE_RE = re.compile(r"^\s*\d{4}\s*[-–—]\s*\d{4}\s*$")
URL_RE = re.compile(r"https?://[^\s)\]]+", re.I)
LINKEDIN_RE = re.compile(r"https?://(www\.)?linkedin\.com/[^\s)\]]+", re.I)
GITHUB_RE = re.compile(r"https?://(www\.)?github\.com/[^\s)\]]+", re.I)

SECTION_RE = re.compile(
    r"^\s*(experience|education|skills|projects|summary|languages|certifications|achievements|"
    r"ניסיון|השכלה|מיומנויות|פרויקטים|סיכום|שפות|הסמכות)\s*[:\-]?\s*$",
    re.I,
)

TECH_DICT = {
    "python": "python", "py": "python", "r": "r", "java": "java",
    "c#": "csharp", "csharp": "csharp", "c++": "cpp", "go": "go",
    "javascript": "javascript", "typescript": "typescript", "ts": "typescript",
    "php": "php", "ruby": "ruby", "scala": "scala", "rust": "rust",
    "react": "react", "vue": "vue", "angular": "angular",
    "node": "nodejs", "node.js": "nodejs", "express": "express",
    "django": "django", "flask": "flask", "fastapi": "fastapi",
    "spring": "spring", ".net": "dotnet", "dotnet": "dotnet",
    "nextjs": "nextjs", "tailwind": "tailwind",
    "pandas": "pandas", "numpy": "numpy", "scikit-learn": "scikit-learn",
    "xgboost": "xgboost", "lightgbm": "lightgbm",
    "spark": "spark", "airflow": "airflow",
    "sql": "sql", "postgres": "postgresql", "postgresql": "postgresql",
    "mysql": "mysql", "mongodb": "mongodb",
    "docker": "docker", "kubernetes": "kubernetes", "k8s": "kubernetes",
    "aws": "aws", "gcp": "gcp", "azure": "azure",
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


def _extract_skills(text: str) -> List[Dict[str, Any]]:
    found: Dict[str, List[Dict[str, int]]] = {}
    for raw, norm in TECH_DICT.items():
        pattern = r"(?<![A-Za-z0-9+])" + re.escape(raw) + r"(?![A-Za-z0-9+])"
        for match in re.finditer(pattern, text, flags=re.I):
            found.setdefault(norm, []).append({"char_start": match.start(), "char_end": match.end()})
    skills: List[Dict[str, Any]] = []
    for norm, spans in found.items():
        confidence = 0.9 if len(spans) > 1 else 0.8
        skills.append({"name": norm, "provenance": spans, "confidence": confidence})
    return skills


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

    return {
        "person": {
            "name": None,
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
