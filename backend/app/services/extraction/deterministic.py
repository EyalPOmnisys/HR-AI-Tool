from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?0?\d{1,3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4,5}")
URL_RE = re.compile(r"https?://[^\s)\]]+", re.I)
LINKEDIN_RE = re.compile(r"https?://(www\.)?linkedin\.com/[^\s)\]]+", re.I)
GITHUB_RE = re.compile(r"https?://(www\.)?github\.com/[^\s)\]]+", re.I)

# כותרות נפוצות (he/en) לזיהוי מדורים
SECTION_RE = re.compile(
    r"^\s*(experience|ניסיון|education|השכלה|skills|מיומנויות|projects|פרויקטים|summary|סיכום|languages|שפות|certifications|הסמכות)\s*[:\-]?\s*$",
    re.I
)

# מילונים/מונחים בסיסיים לנירמול מיומנויות (ל־MVP; אפשר להרחיב)
TECH_DICT = {
    "python": "python", "py": "python",
    "java": "java",
    "c#": "csharp", "csharp": "csharp", ".net": "dotnet", "dotnet": "dotnet",
    "javascript": "javascript", "typescript": "typescript", "ts": "typescript",
    "react": "react", "vue": "vue", "angular": "angular",
    "node": "nodejs", "node.js": "nodejs",
    "postgres": "postgresql", "postgresql": "postgresql", "mysql": "mysql", "mongodb": "mongodb",
    "docker": "docker", "kubernetes": "kubernetes", "k8s": "kubernetes",
    "aws": "aws", "gcp": "gcp", "azure": "azure",
    "spark": "spark", "airflow": "airflow", "hadoop": "hadoop",
}

def _find_all(pattern: re.Pattern, text: str) -> List[Tuple[str, int, int]]:
    results = []
    for m in pattern.finditer(text):
        span = m.span()
        results.append((m.group(0), span[0], span[1]))
    return results

def _collect_sections(text: str) -> List[Dict[str, Any]]:
    sections = []
    current = {"title": "general", "start": 0}
    lines = text.splitlines()
    offset = 0
    for ln in lines:
        if SECTION_RE.match(ln.strip()):
            # סגור קטע קודם
            current["end"] = offset + len(ln)
            sections.append(current)
            # התחל חדש
            current = {"title": SECTION_RE.match(ln.strip()).group(0).strip().lower(), "start": offset + len(ln)}
        offset += len(ln) + 1
    current["end"] = len(text)
    sections.append(current)
    return sections

def _extract_basic_contacts(text: str) -> Dict[str, Any]:
    emails = _find_all(EMAIL_RE, text)
    phones = _find_all(PHONE_RE, text)
    links = _find_all(URL_RE, text)
    lin = _find_all(LINKEDIN_RE, text)
    gh = _find_all(GITHUB_RE, text)

    def pack(items, type_):
        return [
            {
                "type": type_,
                "value": v,
                "provenance": {"char_start": s, "char_end": e},
                "confidence": 0.98
            } for (v, s, e) in items
        ]

    return {
        "emails": pack(emails, "email"),
        "phones": pack(phones, "phone"),
        "links": pack(links, "url"),
        "profiles": pack(lin, "linkedin") + pack(gh, "github")
    }

def _extract_skills(text: str) -> Dict[str, Any]:
    found = {}
    for raw, norm in TECH_DICT.items():
        for m in re.finditer(rf"\b{re.escape(raw)}\b", text, flags=re.I):
            found.setdefault(norm, []).append({"char_start": m.start(), "char_end": m.end()})
    skills = []
    for norm, spans in found.items():
        skills.append({
            "name": norm,
            "provenance": spans,
            "confidence": 0.8 if len(spans) == 1 else 0.9
        })
    return {"skills": skills}

def extract_deterministic(parsed_text: str) -> Dict[str, Any]:
    sections = _collect_sections(parsed_text)
    contacts = _extract_basic_contacts(parsed_text)
    skills = _extract_skills(parsed_text)
    return {
        "person": {
            "emails": contacts["emails"],
            "phones": contacts["phones"],
            "links": contacts["links"],
            "profiles": contacts["profiles"],
        },
        "skills": skills["skills"],
        "sections": sections, 
        "confidence": {"person": 0.9, "skills": 0.85},
        "provenance": {"root": {"char_start": 0, "char_end": len(parsed_text)}}
    }
