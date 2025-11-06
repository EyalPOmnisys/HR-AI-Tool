"""Deterministic resume field extraction to complement the optional LLM boost.

This module performs conservative, regex/heuristics-based extraction of:
- Contacts (emails, phones, urls, profiles)
- Sections (with provenance)
- Technical skills (normalized)
- Education (supports two-line pattern: "Institution | Years" + next line degree)
- Experience (supports "Title | Company | Dates" and "Title | Dates" + next line company)
- Languages (light heuristic)

It is intentionally cautious to avoid false positives; the LLM booster can refine/complete.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


# ---------------------------
# Regex Patterns (precise)
# ---------------------------

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)

# Phone candidate: allow +country-code and separators; must start/end on non-digit boundaries.
# Later we normalize to + and digits only, and apply length sanity checks.
PHONE_CANDIDATE_RE = re.compile(r"(?:(?<!\d)\+?\d[\d\s().\-]{7,}\d(?!\d))")

# Year ranges like "2021-2022" that should NOT be considered phone numbers.
YEAR_RANGE_RE = re.compile(r"^\s*\d{4}\s*[-–—]\s*\d{4}\s*$")

URL_RE = re.compile(r"https?://[^\s)\]]+", re.I)
LINKEDIN_RE = re.compile(r"https?://(www\.)?linkedin\.com/[^\s)\]]+", re.I)
GITHUB_RE = re.compile(r"https?://(www\.)?github\.com/[^\s)\]]+", re.I)

# Common section headers (English + Hebrew)
SECTION_RE = re.compile(
    r"^\s*(experience|education|skills|projects|summary|languages|certifications|achievements|"
    r"ניסיון|השכלה|מיומנויות|פרויקטים|סיכום|שפות|הסמכות)\s*[:\-]?\s*$",
    re.I,
)

# Expanded technology normalization dictionary (languages, frameworks, data/ML, BI/DB/ETL, cloud/infra)
TECH_DICT = {
    # Languages
    "python": "python", "py": "python", "r": "r", "java": "java",
    "c#": "csharp", "csharp": "csharp", "c++": "cpp", "go": "go",
    "javascript": "javascript", "typescript": "typescript", "ts": "typescript",
    "php": "php", "ruby": "ruby", "scala": "scala", "rust": "rust",
    # Web/Frameworks
    "react": "react", "vue": "vue", "angular": "angular",
    "node": "nodejs", "node.js": "nodejs", "express": "express",
    "django": "django", "flask": "flask", "fastapi": "fastapi",
    "spring": "spring", ".net": "dotnet", "dotnet": "dotnet",
    "nextjs": "nextjs", "nuxt": "nuxt", "tailwind": "tailwind", "bootstrap": "bootstrap",
    # Data/ML
    "pandas": "pandas", "numpy": "numpy", "scikit-learn": "scikit-learn",
    "xgboost": "xgboost", "lightgbm": "lightgbm", "random forest": "random-forest",
    "spark": "spark", "airflow": "airflow", "hadoop": "hadoop",
    "bayesian": "bayesian", "bayesian methods": "bayesian",
    # BI/DB/ETL
    "sql": "sql", "postgres": "postgresql", "postgresql": "postgresql",
    "mysql": "mysql", "mariadb": "mariadb", "mongodb": "mongodb",
    "power bi": "power-bi", "excel": "excel", "advanced excel": "excel",
    "etl": "etl", "data engineering": "data-engineering",
    # Infra
    "docker": "docker", "kubernetes": "kubernetes", "k8s": "kubernetes",
    # Cloud
    "aws": "aws", "gcp": "gcp", "azure": "azure",
}

# Light list of languages for heuristic detection
LANGUAGE_WORDS = {"hebrew", "english", "arabic", "russian", "french", "spanish", "german"}


# ---------------------------
# Core Utilities
# ---------------------------

def _find_all(pattern: re.Pattern, text: str) -> List[Tuple[str, int, int]]:
    """Find all matches of a regex pattern, returning (value, start, end)."""
    return [(m.group(0), m.start(), m.end()) for m in pattern.finditer(text)]


def _collect_sections(text: str) -> List[Dict[str, Any]]:
    """
    Identify high-level sections (Experience, Education, etc.).
    We store character start/end to allow UI provenance highlighting.
    """
    sections: List[Dict[str, Any]] = []
    current = {"title": "general", "start": 0}

    lines = text.splitlines()
    offset = 0
    for line in lines:
        if SECTION_RE.match(line.strip()):
            # Close previous section
            current["end"] = offset + len(line)
            sections.append(current)
            # Start new section
            title = SECTION_RE.match(line.strip()).group(1).strip().lower()
            current = {"title": title, "start": offset + len(line)}
        offset += len(line) + 1

    current["end"] = len(text)
    sections.append(current)
    return sections


# ---------------------------
# Contacts
# ---------------------------

def _extract_basic_contacts(text: str) -> Dict[str, Any]:
    """
    Extract emails, phones, URLs, and social profiles.
    Extra validation for phones to avoid false positives like '2021-2022'.
    """
    emails = _find_all(EMAIL_RE, text)

    phones: List[Tuple[str, int, int]] = []
    for raw, s, e in _find_all(PHONE_CANDIDATE_RE, text):
        raw_span = text[s:e].strip()

        # Reject year ranges (e.g., "2021-2022")
        if YEAR_RANGE_RE.match(raw_span):
            continue

        # Normalize: keep a single leading '+' (if present) and digits only
        norm = re.sub(r"[^\d+]", "", raw_span)
        if norm.startswith("+"):
            norm = "+" + re.sub(r"\D", "", norm)
        else:
            norm = "+" + re.sub(r"\D", "", norm)  # ensure a canonical leading '+'

        # Sanity: E.164 length (8–16 digits excluding '+')
        digit_count = len(re.sub(r"\D", "", norm))
        if digit_count < 8 or digit_count > 16:
            continue

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


# ---------------------------
# Skills / Languages
# ---------------------------

def _extract_skills(text: str) -> Dict[str, Any]:
    """
    Extract technical skills based on a normalized dictionary of terms.
    We use a safer boundary check than \b to support tokens like 'C++'.
    """
    found: Dict[str, List[Dict[str, int]]] = {}
    for raw, norm in TECH_DICT.items():
        pattern = r"(?<![A-Za-z0-9+])" + re.escape(raw) + r"(?![A-Za-z0-9+])"
        for match in re.finditer(pattern, text, flags=re.I):
            found.setdefault(norm, []).append(
                {"char_start": match.start(), "char_end": match.end()}
            )

    skills: List[Dict[str, Any]] = []
    for norm, spans in found.items():
        confidence = 0.9 if len(spans) > 1 else 0.8
        skills.append({"name": norm, "provenance": spans, "confidence": confidence})
    return {"skills": skills}


def _extract_languages(text: str) -> List[str]:
    """Heuristic language list from a dedicated Languages section or free text."""
    found = set()
    for lang in LANGUAGE_WORDS:
        if re.search(rf"\b{re.escape(lang)}\b", text, flags=re.I):
            found.add(lang.capitalize())
    return sorted(found)


# ---------------------------
# Education
# ---------------------------

def _parse_year_or_range(token: str) -> Tuple[str | None, str | None]:
    """
    Parse simple year or year range 'YYYY' or 'YYYY–YYYY' / 'YYYY-YYYY'.
    Return (start, end). 'Present' is handled by the caller.
    """
    t = token.strip().lower().replace("–", "-").replace("—", "-")
    if re.match(r"^\d{4}$", t):
        return t, None
    m = re.match(r"^(\d{4})\s*-\s*(\d{4}|present|current|now)$", t)
    if m:
        start, end = m.group(1), m.group(2)
        end = None if end in {"present", "current", "now"} else end
        return start, end
    return None, None


def _extract_education_simple(text: str) -> List[Dict[str, Any]]:
    """
    Parse two-line blocks like:
      'Institution | 2022-2025'
      'B.Sc. in Statistics, Data Science & Economics'
    Fallbacks still apply if only one line is present.
    """
    results: List[Dict[str, Any]] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    degree_hint = re.compile(r"(b\.?sc|m\.?sc|b\.?a|m\.?a|mba|ph\.?d)", re.I)

    i = 0
    while i < len(lines):
        line = lines[i]
        inst, start, end, degree, field = None, None, None, None, None

        # Case A: "Institution | YYYY-YYYY"
        m = re.search(r"^(?P<inst>[^|]+?)\s*\|\s*(?P<years>.+)$", line)
        if m:
            inst = m.group("inst").strip()
            ys = m.group("years").strip()
            start, end = _parse_year_or_range(ys)

            # If next line looks like a degree, capture degree/field
            if i + 1 < len(lines) and degree_hint.search(lines[i + 1]):
                deg_line = lines[i + 1]
                degree = degree_hint.search(deg_line).group(0).replace(".", "").upper()
                post = degree_hint.split(deg_line, maxsplit=1)[-1].strip(" :-–—")
                field = post if post else None
                i += 1  # consume degree line as well

        # Case B: single line with degree (no institution) – fallback
        elif degree_hint.search(line):
            degree = degree_hint.search(line).group(0).replace(".", "").upper()
            post = degree_hint.split(line, maxsplit=1)[-1].strip(" :-–—")
            field = post if post else None

        if inst or degree or field:
            results.append(
                {
                    "institution": inst,
                    "degree": degree,
                    "field": field,
                    "start_date": start,
                    "end_date": end,
                }
            )
        i += 1

    return results


# ---------------------------
# Experience
# ---------------------------

def _extract_experience_simple(text: str) -> List[Dict[str, Any]]:
    """
    Heuristics for lines like:
      'Data Projects | 2024 – present'
      'Ben Gurion University'
      '• bullet...'
    Also supports 'Title | Company | Dates'.
    Bullets end when a blank line OR a new title pattern appears.
    """
    results: List[Dict[str, Any]] = []
    lines = [ln for ln in (l.strip() for l in text.splitlines()) if ln]

    triple = re.compile(
        r"^(?P<title>[^|]{2,}?)\s*\|\s*(?P<company>[^|]{2,}?)\s*\|\s*(?P<dates>.+?)$"
    )
    title_dates = re.compile(
        r"^(?P<title>[^|]{2,}?)\s*\|\s*(?P<dates>\d{4}\s*[-–—]\s*(?:\d{4}|present|current|now)|\d{4})$",
        re.I,
    )
    bullet = re.compile(r"^[•\-–]\s+(.*)$")

    def flush(cur: Dict[str, Any] | None):
        if cur:
            cur["bullets"] = [b for b in cur.get("bullets", []) if b]
            results.append(cur)

    cur: Dict[str, Any] | None = None
    i = 0
    while i < len(lines):
        ln = lines[i]

        # Case 1: "Title | Company | Dates"
        m = triple.match(ln)
        if m:
            flush(cur)
            start, end = _parse_year_or_range(m.group("dates"))
            cur = {
                "title": m.group("title").strip(),
                "company": m.group("company").strip(),
                "start_date": start,
                "end_date": end,
                "location": None,
                "bullets": [],
                "tech": [],
            }
            i += 1
            continue

        # Case 2: "Title | Dates" then NEXT line is company (non-bullet, not a header)
        m2 = title_dates.match(ln)
        if m2:
            flush(cur)
            start, end = _parse_year_or_range(m2.group("dates"))
            title_val = m2.group("title").strip()
            company_val = None
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                if not bullet.match(nxt) and not triple.match(nxt) and not title_dates.match(nxt):
                    company_val = nxt.strip()
                    i += 1  # consume company line
            cur = {
                "title": title_val,
                "company": company_val,
                "start_date": start,
                "end_date": end,
                "location": None,
                "bullets": [],
                "tech": [],
            }
            i += 1
            continue

        # Bullets
        mb = bullet.match(ln)
        if mb and cur is not None:
            cur.setdefault("bullets", []).append(mb.group(1).strip())
            i += 1
            continue

        # New logical block without pipes could be a new title; if we already have
        # a current block and see a capitalized short line without punctuation, flush.
        if cur and re.match(r"^[A-Z][A-Za-z0-9/&()., ':-]{1,60}$", ln) and not bullet.match(ln):
            flush(cur)
            cur = {
                "title": ln.strip(),
                "company": None,
                "start_date": None,
                "end_date": None,
                "location": None,
                "bullets": [],
                "tech": [],
            }
            i += 1
            continue

        i += 1

    flush(cur)
    return results


# ---------------------------
# Public Entry Point
# ---------------------------

def extract_deterministic(parsed_text: str) -> Dict[str, Any]:
    """
    Deterministically extract key fields from resume text.
    Provides structured extraction before LLM enhancement.
    Includes better contacts, skills, sections, languages, and
    light heuristics for education/experience.
    """
    sections = _collect_sections(parsed_text)
    contacts = _extract_basic_contacts(parsed_text)
    skills = _extract_skills(parsed_text)
    langs = _extract_languages(parsed_text)

    # Attempt to extract education/experience from their sections if present,
    # otherwise fall back to scanning the whole text.
    edu_text = parsed_text
    exp_text = parsed_text
    for sec in sections:
        title = (sec.get("title") or "").lower()
        seg = parsed_text[sec["start"]:sec["end"]]
        if "education" in title or "השכלה" in title:
            edu_text = seg
        if "experience" in title or "ניסיון" in title:
            exp_text = seg

    education = _extract_education_simple(edu_text)
    experience = _extract_experience_simple(exp_text)

    result: Dict[str, Any] = {
        "person": {
            "name": None,  # LLM can fill reliably from header if needed
            "emails": contacts["emails"],
            "phones": contacts["phones"],
            "links": contacts["links"],
            "profiles": contacts["profiles"],
            "languages": langs or None,
            "confidence_details": {"languages": 0.7 if langs else 0.0},
        },
        "skills": skills["skills"],
        "sections": sections,
        "education": education or None,
        "experience": experience or None,
        "confidence": {
            "person": 0.9,
            "skills": 0.85,
            "education": 0.6 if education else 0.0,
            "experience": 0.6 if experience else 0.0,
        },
        "provenance": {"root": {"char_start": 0, "char_end": len(parsed_text)}},
    }
    return result
