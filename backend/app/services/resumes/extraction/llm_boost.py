# app/services/resumes/extraction/llm_boost.py
"""
LLM Resume Enhancer - AI-powered structured extraction with validation and experience clustering.
Processes resumes using LLM for education, experience, and clustering while maintaining data quality and preventing hallucinations.
"""
# -----------------------------------------------------------------------------
# PURPOSE (English-only header)
# End-to-end LLM pipeline with strict validation, reliable merging and duration
# recomputation. This version fixes:
# 1) Education must never contribute to experience years (especially "tech").
# 2) Roles with end_date like "present/current/now" are computed up to now.
# 3) primary_years is only set for "tech" if there are actual tech roles.
# 4) Contacts/skills from the deterministic SAFE base are always merged back
#    when missing from the LLM result.
# 5) Section headers (e.g., "Projects") never leak into roles.
# 6) Dates are normalized and years are recalculated from extraction.experience.
# 7) NEW: Parse month-name dates (e.g., "Jan 2020", "January 2020", "March 3, 2024").
# 8) NEW: If clustering returns nothing, fall back to a deterministic total by category
#    based on role titles/tech stack, preferring TECH over MILITARY for military orgs
#    when the role is clearly technical.
# 9) NEW: Post-merge deduplication for contacts (emails/phones/links/profiles).
# -----------------------------------------------------------------------------
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.common.llm_client import default_llm_client, load_prompt

RESUME_EXTRACTION_PROMPT = load_prompt("resumes/resume_extraction.prompt.txt")
EXPERIENCE_CLUSTERING_PROMPT = load_prompt("resumes/experience_clustering.prompt.txt")

BANNED_ROLE_TITLES = {
    "projects", "experience", "education", "skills", "summary",
    "פרויקטים", "ניסיון", "השכלה", "מיומנויות", "סיכום"
}
ALLOWED_CATEGORIES = {"tech", "military", "hospitality", "other"}

LLM_TIMEOUT_S = 90
RETRIES = 2


def _is_number(x: Any) -> bool:
    try:
        return isinstance(x, (int, float)) and not math.isnan(float(x)) and math.isfinite(float(x))
    except Exception:
        return False


def _normalize_il_phone(value: str) -> str:
    """Normalize Israeli phone numbers into +972XXXXXXXXX where possible."""
    v = "".join(ch for ch in value if ch.isdigit() or ch == "+")
    if v.startswith("+"):
        digits = "".join(ch for ch in v if ch.isdigit())
        return "+" + digits
    digits = "".join(ch for ch in v if ch.isdigit())
    if digits.startswith("0") and 8 <= len(digits) - 1 <= 9:
        return "+972" + digits[1:]
    return "+" + digits if digits else value


def _lc(s: Optional[str]) -> Optional[str]:
    return s.lower() if isinstance(s, str) else s


def _parse_date(raw: Any) -> Optional[datetime]:
    """
    Parse multiple loose formats including English and Hebrew month names.
    Accepts: YYYY, YYYY-MM, YYYY-MM-DD, MM/YYYY, YYYY/MM, 'Jan 2020', 'ינואר 2020'.
    Maps 'present/current/now/כיום/נוכחי/הווה' to current UTC.
    """
    if raw is None:
        return None
    try:
        val = str(raw).strip().lower().replace("–", "-").replace("—", "-")
        if val in {"present", "current", "now", "כיום", "נוכחי", "הווה"}:
            return datetime.utcnow()
        # Handle compact year range mistakenly sent as a single value
        if "-" in val and val.count("-") == 1 and len(val) == 9 and val[:4].isdigit() and val[-4:].isdigit():
            val = val.split("-")[0]

        # Hebrew month parsing
        heb_months = {
            "ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4, "מאי": 5, "יוני": 6,
            "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12,
        }
        m = re.match(rf"^\s*({'|'.join(heb_months.keys())})\s+(20\d{{2}}|19\d{{2}})\s*$", val)
        if m:
            month = heb_months.get(m.group(1), 1)
            year = int(m.group(2))
            return datetime(year, month, 1)
        m = re.match(rf"^\s*(\d{{1,2}})\s+({'|'.join(heb_months.keys())})\s+(20\d{{2}}|19\d{{2}})\s*$", val)
        if m:
            day = int(m.group(1))
            month = heb_months.get(m.group(2), 1)
            year = int(m.group(3))
            return datetime(year, month, min(day, 28))

        # Try an ordered list of formats (most specific first)
        fmts = (
            "%B %d, %Y", "%b %d, %Y",
            "%d %B %Y", "%d %b %Y",
            "%B %Y", "%b %Y",
            "%Y-%m-%d", "%Y-%m",
            "%m/%Y", "%Y/%m", "%Y",
            "%b-%Y", "%B-%Y",
        )
        for fmt in fmts:
            try:
                dt = datetime.strptime(val.title() if "%b" in fmt or "%B" in fmt else val, fmt)
                if fmt == "%Y":
                    dt = dt.replace(month=1, day=1)
                elif fmt in {"%Y-%m", "%m/%Y", "%Y/%m", "%b %Y", "%B %Y", "%b-%Y", "%B-%Y"}:
                    dt = dt.replace(day=1)
                return dt
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _duration_years(start_raw: Any, end_raw: Any) -> float:
    """
    Compute duration in years (1 decimal). End defaults to now if missing or 'present'.
    Uses month-based calculation for accuracy:
    - 2019-2022 = 3 years (2019-01-01 to 2022-12-31)
    - Handles overlaps correctly in clustering logic
    """
    s = _parse_date(start_raw)
    e = _parse_date(end_raw) or datetime.utcnow()
    if not (s and e and e >= s):
        return 0.0
    
    # Calculate years and months difference
    years_diff = e.year - s.year
    months_diff = e.month - s.month
    days_diff = e.day - s.day
    
    # Convert to total months
    total_months = years_diff * 12 + months_diff
    
    # Add fraction for remaining days (approximate: days/30)
    if days_diff > 0:
        total_months += days_diff / 30.0
    
    # Convert months to years with 1 decimal precision
    years = total_months / 12.0
    return round(max(years, 0.0), 1)


def _sanitize_roles(experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Drop rows where the 'title' is a section header in any language.
    Additionally, attempt to infer missing titles from bullets/tech stack.
    """
    out = []
    for e in experience or []:
        title = (e or {}).get("title")
        if isinstance(title, str) and title.strip().lower() in BANNED_ROLE_TITLES:
            continue
        
        # If title is missing or null, try to infer from bullets/tech
        if not title or not str(title).strip():
            inferred = _infer_title_from_role(e)
            if inferred:
                e["title"] = inferred
        
        out.append(e)
    return out


def _infer_title_from_role(role: Dict[str, Any]) -> Optional[str]:
    """
    Infer job title from role description when title is missing.
    Analyzes bullets and tech stack to determine most appropriate title.
    Returns None if title cannot be reliably inferred.
    """
    bullets = role.get("bullets") or []
    tech = role.get("tech") or []
    
    if not bullets:
        return None
    
    # Combine bullets into single text for analysis
    text = " ".join(str(b).lower() for b in bullets if isinstance(b, str))
    
    # Define keyword patterns for common roles
    patterns = {
        "AI Developer": ["ai-powered", "ai based", "machine learning", "ml", "gemini", "openai", "llm"],
        "Full Stack Developer": ["full stack", "fullstack", "frontend and backend", "react and node"],
        "Frontend Developer": ["frontend", "front-end", "react", "angular", "vue", "ui/ux"],
        "Backend Developer": ["backend", "back-end", "api", "server", "database"],
        "Software Developer": ["developed", "built", "implemented", "programmed"],
        "DevOps Engineer": ["devops", "ci/cd", "docker", "kubernetes", "jenkins", "deployment"],
        "Data Scientist": ["data analysis", "data science", "analytics", "machine learning"],
    }
    
    # Check for AI/ML indicators first (highest priority)
    if any(kw in text for kw in patterns["AI Developer"]):
        return "AI Developer"
    
    # Check for full stack indicators
    has_frontend = any(tech_item.lower() in ["react", "angular", "vue", "html", "css"] 
                       for tech_item in tech if isinstance(tech_item, str))
    has_backend = any(tech_item.lower() in ["node.js", "express", "django", "flask", "spring"] 
                      for tech_item in tech if isinstance(tech_item, str))
    
    if has_frontend and has_backend:
        return "Full Stack Developer"
    
    # Check other patterns
    for title, keywords in patterns.items():
        if title in ["AI Developer", "Full Stack Developer"]:
            continue  # Already checked above
        match_count = sum(1 for kw in keywords if kw in text)
        if match_count >= 2:  # Require at least 2 keyword matches
            return title
    
    # Generic fallback for technical roles
    if any(kw in text for kw in ["develop", "built", "implement", "code", "software"]):
        return "Software Developer"
    
    return None


def _validate_structured_payload(obj: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "not a dict"
    if "person" not in obj or "experience" not in obj or "education" not in obj:
        return False, "missing top-level keys"
    person = obj.get("person") or {}
    langs = person.get("languages")
    if langs is not None and not isinstance(langs, list):
        return False, "person.languages must be list or null"
    exp = obj.get("experience")
    if exp is not None and not isinstance(exp, list):
        return False, "experience must be list or null"
    edu = obj.get("education")
    if edu is not None and not isinstance(edu, list):
        return False, "education must be list or null"
    return True, ""


def _validate_clustering_payload(obj: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "clustering: not a dict"
    clusters = obj.get("experience_clusters")
    if not isinstance(clusters, list):
        return False, "clustering: experience_clusters must be list"
    totals = obj.get("totals_by_category")
    if not isinstance(totals, dict):
        return False, "clustering: totals_by_category must be dict"
    for k, v in totals.items():
        if k not in ALLOWED_CATEGORIES:
            return False, f"clustering: illegal category {k}"
        if not _is_number(v) or v < 0:
            return False, f"clustering: totals_by_category {k} invalid"
    for c in clusters:
        cat = c.get("category")
        if cat not in ALLOWED_CATEGORIES:
            return False, f"clustering: cluster illegal category {cat}"
    primary = obj.get("recommended_primary_years")
    if primary is not None and not isinstance(primary, dict):
        return False, "clustering: recommended_primary_years must be dict or null"
    return True, ""


# ----------------------- Contacts post-processing -----------------------------

def _normalize_url_for_dedup(u: str) -> str:
    if not isinstance(u, str):
        return ""
    return u.strip().rstrip("/").lower()


def _dedup_person_contacts(person: Dict[str, Any]) -> Dict[str, Any]:
    """Deduplicate person contacts by normalized values after merge/normalization."""
    def dedup(items: Optional[List[Dict[str, Any]]], key_fn):
        out, seen = [], set()
        for it in items or []:
            try:
                key = key_fn(it)
            except Exception:
                key = None
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out

    # Emails
    person["emails"] = dedup(
        person.get("emails"),
        lambda i: (i.get("value") or "").strip().lower()
    )
    # Phones (normalize to E.164-like key)
    person["phones"] = dedup(
        person.get("phones"),
        lambda i: _normalize_il_phone(i.get("value") or "")
    )
    # Links (URLs)
    person["links"] = dedup(
        person.get("links"),
        lambda i: _normalize_url_for_dedup(i.get("value") or "")
    )
    # Profiles (type + URL)
    person["profiles"] = dedup(
        person.get("profiles"),
        lambda i: (str(i.get("type") or "").lower(), _normalize_url_for_dedup(i.get("value") or ""))
    )
    return person


def _postfix_normalize_person(merged: Dict[str, Any]) -> None:
    """Post-merge contact normalization and dedup (phones to E.164 where possible)."""
    person = merged.get("person") or {}
    fixed = []
    for p in person.get("phones") or []:
        val = (p or {}).get("value")
        if isinstance(val, str) and val.strip():
            p["value"] = _normalize_il_phone(val)
            fixed.append(p)
    if fixed:
        person["phones"] = fixed
    # Deduplicate all contact lists
    person = _dedup_person_contacts(person)
    merged["person"] = person


def _final_merge_base_signals(extraction: Dict[str, Any], base_json: Dict[str, Any]) -> None:
    """Always bring back deterministic base signals if LLM missed them."""
    person = extraction.setdefault("person", {})
    base_person = base_json.get("person") or {}
    for key in ("emails", "phones", "links", "profiles"):
        if not person.get(key):
            person[key] = base_person.get(key) or []
    if not person.get("languages"):
        person["languages"] = base_person.get("languages")
    base_skills = base_json.get("skills") or []
    if not extraction.get("skills"):
        extraction["skills"] = base_skills


# ----------------------- Soft-matching helpers (utils-ready) -------------------

def _norm_text(s: Optional[str]) -> str:
    """Lowercase, unify symbols, strip non-alphanumerics, collapse spaces."""
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _jaccard(a: str, b: str) -> float:
    """Token Jaccard similarity on normalized strings."""
    ta = set(_norm_text(a).split()) if a else set()
    tb = set(_norm_text(b).split()) if b else set()
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _soft_match_role(
    member: Dict[str, Any],
    experience: List[Dict[str, Any]],
    edu_insts_norm: set,
) -> Optional[Dict[str, Any]]:
    """
    Find a "soft" match between a clustering member and an actual extraction role.
    Preference is given to company similarity; title contributes as secondary signal.
    Returns the best matching role or None when no acceptable match is found.
    """
    title_m = member.get("title") or ""
    company_m = member.get("company") or ""

    title_m_n = _norm_text(title_m)
    company_m_n = _norm_text(company_m)

    best = None
    best_score = 0.0

    for r in experience:
        comp_r = r.get("company") or ""
        title_r = r.get("title") or ""
        comp_r_n = _norm_text(comp_r)
        title_r_n = _norm_text(title_r)

        # Exclude education institutions
        if comp_r_n in edu_insts_norm:
            continue

        score_comp = _jaccard(company_m_n, comp_r_n) if company_m_n else 0.0
        score_title = _jaccard(title_m_n, title_r_n) if title_m_n else 0.0

        # Boost if one string contains the other (handles short/long variants)
        if company_m_n and (company_m_n in comp_r_n or comp_r_n in company_m_n):
            score_comp = max(score_comp, 0.9)
        if title_m_n and (title_m_n in title_r_n or title_r_n in title_m_n):
            score_title = max(score_title, 0.85)

        score = 0.6 * score_comp + 0.4 * score_title  # company weighs slightly more

        # Acceptance threshold tuned to catch real-world variants ("meta" vs "meta platforms")
        if score >= 0.55 and score > best_score:
            best_score = score
            best = r

    return best


# ----------------------------- Fallback heuristics ----------------------------

_TECH_TITLE_KEYWORDS = (
    "developer", "engineer", "software", "frontend", "front end", "backend", "back end",
    "full stack", "devops", "sre", "site reliability", "data", "ml", "machine learning",
    "ai", "android", "ios", "mobile", "architect", "security", "platform", "automation", "qa"
)


def _is_tech_role(role: Dict[str, Any]) -> bool:
    """Return True if role clearly looks technical by title keywords or a non-empty tech stack."""
    tech_list = role.get("tech")
    if isinstance(tech_list, list) and any(isinstance(t, str) and t.strip() for t in tech_list):
        return True
    title_n = _norm_text(role.get("title"))
    return any(k in title_n for k in _TECH_TITLE_KEYWORDS)


def _looks_military_company(company_raw: Optional[str]) -> bool:
    """Detect common military/defense org hints (e.g., IAF/IDF/Unit numbers/Ofek)."""
    name = _norm_text(company_raw)
    if not name:
        return False
    if any(tag in name for tag in ("iaf", "idf", "air force", "ofek", "tzahal", "8200")):
        return True
    # 'unit' combined with a unit number is a strong signal (e.g., 'unit 324')
    if "unit" in name and re.search(r"\b\d{2,4}\b", name):
        return True
    return False


def _fallback_totals_by_category(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback when clustering returns nothing: sum durations from extraction.experience and
    assign categories by simple heuristics. Prefer TECH when role looks technical even if
    the company name is military/defense.
    """
    experience = _sanitize_roles(extraction.get("experience") or [])
    totals_by_category: Dict[str, float] = {k: 0.0 for k in ALLOWED_CATEGORIES}

    for role in experience:
        dy = _duration_years(role.get("start_date"), role.get("end_date"))
        if dy <= 0:
            continue
        company = role.get("company") or ""
        if _is_tech_role(role):
            cat = "tech"
        elif _looks_military_company(company):
            cat = "military"
        else:
            cat = "other"
        totals_by_category[cat] = round(totals_by_category[cat] + dy, 1)

    # recommended_primary_years only for tech when present
    primary_years = {}
    if totals_by_category.get("tech", 0.0) > 0:
        primary_years["tech"] = totals_by_category["tech"]

    return {
        "experience_clusters": [],  # fallback does not fabricate clusters
        "totals_by_category": totals_by_category,
        "recommended_primary_years": primary_years,
    }


# ----------------------------- Clusters rebuilding ----------------------------

def _rebuild_clean_clusters(
    extraction: Dict[str, Any],
    raw_clustering: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Rebuild clusters strictly from extraction.experience, recomputing durations.
    Education roles never count. If exact (title, company) matching fails, we try
    soft matching to tolerate harmless variations in company/title strings.
    If, after rebuilding, nothing valid remains, fall back to a deterministic
    totals computation by title/stack heuristics (preferring TECH when appropriate).
    """
    experience = _sanitize_roles(extraction.get("experience") or [])
    edu = extraction.get("education") or []

    # Exact index (legacy behavior)
    exp_index = {((_lc(e.get("title")) or ""), (_lc(e.get("company")) or "")): e for e in experience}
    # Normalized set of education institutions (excluded from experience sums)
    edu_insts_norm = {_norm_text(x.get("institution")) for x in edu if isinstance(x, dict) and x.get("institution")}

    cleaned_clusters: List[Dict[str, Any]] = []
    totals_by_category: Dict[str, float] = {k: 0.0 for k in ALLOWED_CATEGORIES}
    category_has_roles: Dict[str, bool] = {k: False for k in ALLOWED_CATEGORIES}

    for c in (raw_clustering.get("experience_clusters") or []):
        cat = c.get("category")
        if cat not in ALLOWED_CATEGORIES:
            continue
        members = []
        total_years = 0.0

        for m in (c.get("members") or []):
            # Step 1: exact match by (title, company) lowercase
            title_k = _lc(m.get("title"))
            company_k = _lc(m.get("company"))
            exp_key = (title_k or "", company_k or "")
            exp_role = exp_index.get(exp_key)

            # Step 2: soft match if exact match failed
            if not exp_role:
                exp_role = _soft_match_role(m, experience, edu_insts_norm)

            if not exp_role:
                continue

            # Do not count items that correspond to education institutions
            comp_norm = _norm_text(exp_role.get("company") or "")
            if comp_norm in edu_insts_norm:
                continue

            sd = exp_role.get("start_date")
            ed = exp_role.get("end_date")
            dy = _duration_years(sd, ed)
            if dy <= 0:
                continue

            members.append({
                "title": exp_role.get("title"),
                "company": exp_role.get("company"),
                "start_date": sd,
                "end_date": ed
            })
            total_years += dy

        if not members:
            continue

        total_years = round(total_years, 1)
        totals_by_category[cat] = round(totals_by_category.get(cat, 0.0) + total_years, 1)
        category_has_roles[cat] = True
        cleaned_clusters.append({
            "category": cat,
            "members": members,
            "total_years": total_years,
            "confidence": c.get("confidence", 0.7),
            "normalized_roles": c.get("normalized_roles") or [],
            "original_roles": c.get("original_roles") or [],
            "reasoning": c.get("reasoning") or "recomputed from extraction.experience (with soft matching)"
        })

    # Normalize totals
    for k in list(totals_by_category.keys()):
        totals_by_category[k] = round(totals_by_category[k], 1)

    # If no valid tech roles after cleaning, enforce 0.0
    if not category_has_roles.get("tech", False):
        totals_by_category["tech"] = 0.0

    # If nothing meaningful came out, fall back to deterministic totals by role/title/stack
    if (not cleaned_clusters) or (all(v == 0.0 for v in totals_by_category.values())):
        fallback = _fallback_totals_by_category(extraction)
        # Preserve cleaned_clusters if they exist; otherwise use empty (fallback does not fabricate)
        cleaned_clusters = cleaned_clusters or fallback.get("experience_clusters", [])
        totals_by_category = fallback.get("totals_by_category", totals_by_category)
        primary_years = fallback.get("recommended_primary_years", {})
    else:
        primary_years = {}
        if totals_by_category.get("tech", 0.0) > 0 and category_has_roles.get("tech", False):
            primary_years["tech"] = totals_by_category["tech"]

    return {
        "experience_clusters": cleaned_clusters,
        "totals_by_category": totals_by_category,
        "recommended_primary_years": primary_years
    }


# ------------------------------ Final normalization ---------------------------

def _final_normalize(extraction: Dict[str, Any], cleaned_cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Apply final sanitization, merge base signals, and assemble output format."""
    extraction["experience"] = _sanitize_roles(extraction.get("experience") or [])
    _final_merge_base_signals(extraction, extraction.get("_base_json_", {}))
    _postfix_normalize_person(extraction)

    out = dict(extraction)
    out.pop("_base_json_", None)

    out["experience_meta"] = {
        "experience_clusters": cleaned_cluster.get("experience_clusters", []),
        "totals_by_category": cleaned_cluster.get("totals_by_category", {}),
        "recommended_primary_years": cleaned_cluster.get("recommended_primary_years", {}),
    }

    totals = cleaned_cluster.get("totals_by_category") or {}
    out["years_by_category"] = {k: float(v) for k, v in totals.items() if _is_number(v) and v >= 0}

    rec = cleaned_cluster.get("recommended_primary_years") or {}
    out["primary_years"] = float(rec["tech"]) if ("tech" in rec and _is_number(rec["tech"])) else None

    return out


# --------------------------------- LLM wrapper --------------------------------

def _call_llm_json(messages: List[Dict[str, str]], timeout: int = LLM_TIMEOUT_S) -> Optional[Dict[str, Any]]:
    """Thin wrapper for JSON chat calls. Returns dict or None."""
    try:
        resp = default_llm_client.chat_json(messages, timeout=timeout)
        data = resp.data
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def llm_end_to_end_enhance(parsed_text: str, base_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run extraction -> clustering -> rebuild & normalize.
    Strictly trust extraction.experience as the single source of truth for roles.
    """
    # Step 1: Extraction
    extraction: Optional[Dict[str, Any]] = None
    for _ in range(RETRIES + 1):
        user = (
            "TEXT:\n"
            f"{parsed_text}\n\n"
            "CURRENT_SAFE_JSON:\n"
            f"{base_json}\n"
            "Return JSON only."
        )
        messages = [
            {"role": "system", "content": RESUME_EXTRACTION_PROMPT},
            {"role": "user", "content": user},
        ]
        cand = _call_llm_json(messages, timeout=max(60, LLM_TIMEOUT_S))
        ok, _why = _validate_structured_payload(cand) if cand is not None else (False, "no data")
        if ok:
            extraction = cand
            break

    if extraction is None:
        # Hard fallback: preserve base_json and return minimal safe shape
        safe_out = dict(base_json)
        safe_out.setdefault("person", {}).setdefault("name", None)
        safe_out["education"] = None
        safe_out["experience"] = None
        safe_out["experience_meta"] = {
            "experience_clusters": [],
            "totals_by_category": {},
            "recommended_primary_years": {}
        }
        safe_out["years_by_category"] = {}
        safe_out["primary_years"] = None
        return safe_out

    extraction["_base_json_"] = base_json

    # Normalize "present/current/now" and whitespace around dates
    for role in extraction.get("experience") or []:
        if isinstance(role.get("end_date"), str):
            if role["end_date"].strip().lower() in {"present", "current", "now"}:
                role["end_date"] = "present"
        if isinstance(role.get("start_date"), str):
            role["start_date"] = role["start_date"].strip()

    extraction["experience"] = _sanitize_roles(extraction.get("experience") or [])

    # Step 2: Clustering request
    extraction_to_cluster = {
        "text": parsed_text,
        "experience": extraction.get("experience") or [],
    }

    raw_clustering: Optional[Dict[str, Any]] = None
    for _ in range(RETRIES + 1):
        user = (
            "INPUT:\n"
            f"{extraction_to_cluster}\n\n"
            "Return JSON only per the schema."
        )
        messages = [
            {"role": "system", "content": EXPERIENCE_CLUSTERING_PROMPT},
            {"role": "user", "content": user},
        ]
        cand = _call_llm_json(messages, timeout=LLM_TIMEOUT_S)
        ok, _why = _validate_clustering_payload(cand) if cand is not None else (False, "no data")
        if ok:
            raw_clustering = cand
            break

    if raw_clustering is None:
        raw_clustering = {"experience_clusters": [], "totals_by_category": {}, "recommended_primary_years": {}}

    # Step 3: Rebuild & normalize (with fallback when needed)
    cleaned_cluster = _rebuild_clean_clusters(extraction, raw_clustering)
    final = _final_normalize(extraction, cleaned_cluster)
    return final
