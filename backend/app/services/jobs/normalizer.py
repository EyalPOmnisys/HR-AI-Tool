# app/services/jobs/normalizer.py
"""
Strict post-normalizer for job analysis JSON.

Goals:
- Enforce *explicit-only* extraction (no hidden inference).
- Canonicalize tech terms consistently (lowercase for tech/tool names).
- Prevent hallucinations (e.g., don't add a tech unless it appears in the text).
- Keep responsibilities/requirements as provided, only dedupe/trim.
- Do not invent languages, locations, or work modes.
- Provide predictable keyword generation focused on concrete tech terms.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, List
from collections import Counter

logger = logging.getLogger("jobs.normalizer")

# ===== Canonicalization =====
# Return lowercase canonical names for technologies/tools/frameworks etc.
# (We prefer lowercase for searchability and schema consistency.)
_ALIAS_TO_CANON = {
    "ts": "typescript",
    "typescript": "typescript",
    "javascript": "javascript",
    "node": "node.js",
    "node.js": "node.js",
    "express": "express.js",
    "express.js": "express.js",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "redis": "redis",
    "zod": "zod",
    "tanstack-query": "tanstack query",
    "tanstack query": "tanstack query",
    "mui": "mui",
    "material ui": "mui",
    "opentelemetry": "opentelemetry",
    "open telemetry": "opentelemetry",
    "websocket": "websockets",
    "websockets": "websockets",
    "rest": "rest apis",
    "rest apis": "rest apis",
    "rest api": "rest apis",
    "ci/cd": "ci/cd",
    "git": "git",
    "vite": "vite",
    "drizzle-orm": "drizzle orm",
    "drizzle orm": "drizzle orm",
    "react": "react",
    "react.js": "react",
    "react native": "react native",
}

# Buckets are lowercase identifiers we can match against the JD text
_BUCKETS = {
    "languages": {"javascript", "typescript", "python", "java", "go", "ruby", "rust", "scala", "php", "swift", "kotlin", "c#", "c++", "node.js"},
    "frameworks": {"react", "react native", "express", "express.js", "spring", "django", "flask", "fastapi", "angular", "vue", "nextjs", "nuxt", "dotnet", "tailwind", "bootstrap"},
    "databases": {"postgres", "postgresql", "mysql", "mariadb", "mongodb", "snowflake", "bigquery", "oracle", "redis", "dynamodb", "elasticsearch", "sql", "nosql"},
    "cloud": {"aws", "azure", "gcp", "digitalocean", "heroku"},
    "tools": {
        "git", "docker", "kubernetes", "jenkins", "terraform", "ansible", "jira", "confluence", "notion", "slack", "figma",
        "selenium", "cypress", "appium", "testrail", "testng", "junit", "pytest", "postman", "soapui", "jmeter", "vscode", "intellij",
        "powershell", "bash", "shell", "excel", "powerbi", "tableau", "opentelemetry", "websockets", "rest", "rest apis", "vite",
        "zod", "tanstack-query", "tanstack query", "mui", "drizzle-orm", "drizzle orm", "ci/cd"
    },
    "business": {"crm", "salesforce", "hubspot", "b2b", "b2c", "marketing", "negotiation", "lead generation", "account management", "pipeline", "forecast", "customer success"},
    "management": {"agile", "scrum", "kanban", "ci/cd", "devops", "waterfall", "qa strategy", "risk management", "stakeholder management", "mentoring", "coaching", "leadership", "budgeting", "planning"},
}

# Human languages recognized (explicit mentions only)
_HUMAN_LANGS = ["english", "hebrew", "french", "german", "spanish", "arabic", "russian"]


def _canon(term: str) -> str:
    """
    Canonicalize a raw term to our lowercase standard name.
    Only performs normalization; it does not attempt to reclassify.
    """
    t = (term or "").strip().lower()
    if not t:
        return ""
    return _ALIAS_TO_CANON.get(t, t)


def _push_unique(bucket: List[str], value: str) -> None:
    v = value.strip().lower()
    if v and v not in bucket:
        bucket.append(v)


def _ensure_tech_keys(tech: Dict[str, Any]) -> None:
    for k in ("languages", "frameworks", "databases", "cloud", "tools", "business", "management"):
        tech.setdefault(k, [])


def _present_in_text(term: str, text_blob: str) -> bool:
    """
    Check if a (canonicalized) term is explicitly present in text (substring match).
    This prevents adding hallucinated skills (e.g., 'scala' when not mentioned).
    """
    t = _canon(term)
    if not t:
        return False
    return t in text_blob


def _scan_and_fill_from_text(text_blob: str, tech: Dict[str, Any]) -> None:
    """
    Populate tech buckets strictly from the text. Only add terms if present verbatim.
    """
    for group, target in [
        (_BUCKETS["languages"], "languages"),
        (_BUCKETS["frameworks"], "frameworks"),
        (_BUCKETS["databases"], "databases"),
        (_BUCKETS["cloud"], "cloud"),
        (_BUCKETS["tools"], "tools"),
        (_BUCKETS["business"], "business"),
        (_BUCKETS["management"], "management"),
    ]:
        for term in group:
            if term in text_blob:
                _push_unique(tech[target], _canon(term))


def _sort_dedup(tech: Dict[str, Any]) -> None:
    for section in ["languages", "frameworks", "databases", "cloud", "tools", "business", "management"]:
        # Keep unique and sorted for deterministic output
        seen = set()
        ordered: List[str] = []
        for t in tech[section]:
            c = _canon(t)
            if c and c not in seen:
                seen.add(c)
                ordered.append(c)
        tech[section] = sorted(ordered)


def _dedupe_list(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for it in items or []:
        v = (it or "").strip()
        if not v:
            continue
        key = v.lower()
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def normalize_job_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strict post-processing for the model output.

    Key decisions:
    - No default assumptions (e.g., do NOT add English as a language unless present).
    - Skills/tech are kept only if they appear verbatim in the source text areas.
    - Responsibilities and requirements are deduplicated but not expanded.
    - Keywords are derived from concrete tech/stack words present in text to avoid noise.
    """
    logger.info("Normalizing job analysis JSON (strict mode)")

    # Ensure lists are lists and dedupe textual arrays we do keep as-is
    data["responsibilities"] = _dedupe_list(data.get("responsibilities") or [])
    data["requirements"] = _dedupe_list(data.get("requirements") or [])
    data["education"] = _dedupe_list(data.get("education") or [])

    # Strict skills separation (no soft skills, no additions)
    skills = data.get("skills") or {}
    must = _dedupe_list(skills.get("must_have") or [])
    nice = _dedupe_list(skills.get("nice_to_have") or [])
    data["skills"] = {"must_have": must, "nice_to_have": nice}

    # Build a lowercase text blob solely from fields that reflect the original text
    # (summary + responsibilities + requirements). We avoid adding any invented content here.
    text_blob_src = " ".join([
        data.get("summary") or "",
        " ".join(data.get("responsibilities") or []),
        " ".join(data.get("requirements") or []),
    ])
    text_blob = text_blob_src.lower()

    # ---- Tech stack (explicit only) ----
    tech = data.get("tech_stack") or {}
    _ensure_tech_keys(tech)

    # 1) Seed ONLY with skills that are present in the text verbatim
    for raw in must + nice:
        if _present_in_text(raw, text_blob):
            # Place into appropriate bucket if recognizable
            key = raw.strip().lower()
            placed = False
            for bucket_name, vocab in _BUCKETS.items():
                if key in vocab or _canon(key) in vocab:
                    _push_unique(tech[bucket_name], _canon(raw))
                    placed = True
                    break
            if not placed:
                # If not recognized to a specific bucket, keep it as a tool by default
                _push_unique(tech["tools"], _canon(raw))

    # 2) Also extract any tech terms that appear directly in the JD text
    _scan_and_fill_from_text(text_blob, tech)
    _sort_dedup(tech)
    data["tech_stack"] = tech

    # ---- Experience ----
    # Parse explicit numeric ranges when present (e.g., "3+ years", "2-4 years").
    # This is still "explicit-only" because we read it from the text blob.
    years_min = data.get("experience", {}).get("years_min")
    years_max = data.get("experience", {}).get("years_max")
    if years_min is None or years_max is None:
        # 2-4 years / 2 – 4 years
        m_range = re.search(r"(\d+)\s*[-–]\s*(\d+)\s+years?", text_blob)
        if m_range:
            yrs_min = int(m_range.group(1))
            yrs_max = int(m_range.group(2))
            data.setdefault("experience", {})["years_min"] = yrs_min
            data["experience"]["years_max"] = yrs_max
        else:
            # 3+ years / at least 3 years
            m_plus = re.search(r"(\d+)\s*\+?\s+years?", text_blob)
            if m_plus and years_min is None:
                data.setdefault("experience", {})["years_min"] = int(m_plus.group(1))
            # We do NOT set years_max unless an explicit upper bound is present.

    # ---- Human languages (no defaults) ----
    # If model provided languages, keep them (after cleaning).
    # If empty, detect explicit mentions in text (e.g., "English - fluent").
    langs = data.get("languages") or []
    cleaned_langs: List[Dict[str, Any]] = []
    if langs:
        for obj in langs:
            name = (obj or {}).get("name")
            level = (obj or {}).get("level")
            if name:
                cleaned_langs.append({"name": name.strip(), "level": level if level in {"basic", "conversational", "fluent", "native", None} else None})
    else:
        for hn in _HUMAN_LANGS:
            if hn in text_blob:
                cleaned_langs.append({"name": hn.capitalize(), "level": None})
    data["languages"] = cleaned_langs

    # ---- Locations / organization / security clearance ----
    # We do not infer or add anything here. Keep what the model extracted (if any).
    data["locations"] = data.get("locations") or []
    data["organization"] = (data.get("organization") or None) or None
    if "security_clearance" in data and isinstance(data["security_clearance"], dict):
        mentioned = bool(data["security_clearance"].get("mentioned"))
        note = (data["security_clearance"].get("note") or None)
        data["security_clearance"] = {"mentioned": mentioned, "note": note}
    else:
        data["security_clearance"] = {"mentioned": False, "note": None}

    # ---- Keywords (focused, explicit) ----
    # Compose keywords from (a) tech stack content and (b) must/nice skill strings that appear in text.
    # Avoid generic words like 'with', 'looking', 'world', etc.
    keyword_candidates: List[str] = []
    for section in ["languages", "frameworks", "databases", "cloud", "tools"]:
        for t in tech.get(section, []):
            if _present_in_text(t, text_blob):
                _push_unique(keyword_candidates, t)

    for s in must + nice:
        if _present_in_text(s, text_blob):
            _push_unique(keyword_candidates, _canon(s))

    # Keep top N by frequency within text to reduce noise
    # (We still count occurrences strictly from text)
    counts = Counter()
    for kw in keyword_candidates:
        counts[kw] = text_blob.count(kw)
    # Deterministic ordering: sort by (-count, alpha)
    data["keywords"] = [k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:50]

    # ---- Salary range sanity ----
    # If salary_range exists ensure correct structure; otherwise set nulls.
    sal = data.get("salary_range") or {}
    data["salary_range"] = {
        "min": sal.get("min", None),
        "max": sal.get("max", None),
        "currency": sal.get("currency", None) if sal.get("currency") in {"ILS", "USD", "EUR"} else None,
    }

    # ---- Evidence passthrough ----
    # We keep evidence as-is if provided by the model. Do not synthesize indices here.
    # (Upstream steps that consume evidence should handle strings/indices as needed.)
    ev = data.get("evidence")
    if isinstance(ev, list):
        # Deduplicate evidence strings if a list of strings was returned
        data["evidence"] = _dedupe_list([str(x) for x in ev])
    else:
        # Otherwise keep the original object (e.g., index mapping) without modification
        # to avoid breaking existing consumers.
        data["evidence"] = ev

    logger.info(
        "Normalization done: %d responsibilities, %d requirements, tech sections: %s",
        len(data["responsibilities"]), len(data["requirements"]),
        ", ".join([k for k in data["tech_stack"] if data["tech_stack"][k]])
    )
    return data
