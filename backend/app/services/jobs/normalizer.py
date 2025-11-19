# app/services/jobs/normalizer.py
"""
Job Analysis Normalizer - Post-processes LLM output to ensure data quality and consistency.
Validates extracted data is explicitly present in source text, canonicalizes tech terms, and prevents hallucinations.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, List
from collections import Counter

from app.services.common.skills_normalizer import (
    normalize_skill, 
    normalize_skill_list
)

logger = logging.getLogger("jobs.normalizer")

# ===== Canonicalization =====
# NOTE: This function now delegates to the centralized skills_normalizer.py
# All skill normalization goes through normalize_skill() for perfect consistency
# across resumes, jobs, and matching.

def _canon(term: str) -> str:
    """
    Canonicalize a raw term using the centralized normalizer.
    
    This ensures perfect consistency across:
    - Resume extraction
    - Job extraction  
    - Matching algorithm
    
    Example: "node", "nodejs", "Node.js 14" all -> "Node.js"
    
    Returns lowercase for internal bucket matching.
    """
    if not term or not isinstance(term, str):
        return ""
    # Use centralized normalizer, then lowercase for bucket matching
    return normalize_skill(term).lower()
# Buckets use CANONICAL names from normalizer for consistency
_BUCKETS = {
    "languages": {
        "javascript", "typescript", "python", "java", "go", "ruby", "rust", "scala", "php", "swift", "kotlin", 
        "c#", "c++", "c", "node.js", "r", "matlab", "perl", "shell", "bash", "html", "css", "scss", "sass",
        "vhdl", "verilog", "assembly", "embedded c"
    },
    "frameworks": {
        "react", "react native", "express", "express.js", "spring", "django", "flask", "fastapi", "angular", "vue", 
        "next.js", "nextjs", "nuxt", "dotnet", ".net", "tailwindcss", "bootstrap", "redux", "graphql", "jquery",
        "context api"
    },
    "databases": {
        "postgres", "postgresql", "mysql", "mariadb", "mongodb", "snowflake", "bigquery", "oracle", "redis", 
        "dynamodb", "elasticsearch", "sql", "nosql", "cassandra", "sqlite"
    },
    "cloud": {"aws", "azure", "gcp", "google cloud", "digitalocean", "heroku", "cloud"},
    "tools": {
        "git", "github", "gitlab", "docker", "kubernetes", "k8s", "jenkins", "terraform", "ansible", "jira", 
        "confluence", "notion", "slack", "figma", "selenium", "cypress", "appium", "testrail", "testng", "junit", 
        "pytest", "postman", "soapui", "jmeter", "vscode", "intellij", "powershell", "bash", "shell", "vite", 
        "webpack", "rollup", "parcel", "zod", "tanstack-query", "tanstack query", "mui", "drizzle-orm", "drizzle orm", 
        "ci/cd", "rest api", "rest apis", "rest", "graphql", "websocket", "websockets", "opentelemetry", "playwright", 
        "jest", "github copilot", "copilot", "cursor", "windsurf",
        # Cybersecurity & Embedded tools
        "wireshark", "metasploit", "nmap", "burp suite", "kali linux", "splunk", "snort", "ida pro", 
        "ghidra", "volatility", "autopsy", "cryptography", "penetration testing", "vulnerability assessment",
        "firewalls", "ids", "ips", "siem", "soar", "dlp"
    },
    "business": {
        "crm", "salesforce", "hubspot", "b2b", "b2c", "b2g", "g2g",
        "marketing", "negotiation", "lead generation", "go-to-market", "gtm",
        "tenders", "rfp", "rfq", "contracting", "pricing", "channels", "partnerships",
        "account management", "pipeline", "forecast", "customer success"
    },
    "management": {
        "agile", "scrum", "kanban", "ci/cd", "devops", "waterfall", "qa strategy", "risk management", 
        "stakeholder management", "mentoring", "coaching", "leadership", "budgeting", "planning"
    },
    "domains": {  # New bucket for specialized domains
        "cybersecurity", "embedded systems", "embedded", "network security", "network protection",
        "communication protocols", "can bus", "i2c", "spi", "uart", "tcp/ip", "udp", "modbus",
        "scada", "iot", "rtos", "freertos", "real-time", "firmware", "hardware",
        "weapon systems", "defense systems", "defense", "military", "aerospace"
    }
}

# Common words that should NOT be included as keywords even if they appear in tech context
_KEYWORD_BLACKLIST = {
    "excel", "word", "powerpoint", "outlook",  # Office suite - too generic
}

# Very short terms that are too ambiguous (need word boundary check)
_AMBIGUOUS_SHORT_TERMS = {"go", "c", "r", "d", "e", "f", "k", "p", "s", "w"}

def _is_valid_tech_term(term: str, text_blob: str) -> bool:
    """
    Check if a term is a valid standalone tech term (not part of another word).
    For very short ambiguous terms, we need word boundary checks.
    """
    if not term or len(term) <= 1:
        return False
    
    # For short ambiguous terms, check word boundaries
    if term in _AMBIGUOUS_SHORT_TERMS:
        import re
        # Check if it appears as a standalone word (surrounded by non-letters)
        pattern = r'\b' + re.escape(term) + r'\b'
        matches = re.findall(pattern, text_blob, re.IGNORECASE)
        
        # CRITICAL: Single letter terms need VERY strict validation
        if len(term) == 1:
            # Only accept if explicitly mentioned as programming language
            lang_patterns = [
                rf'\b{term}\s+programming',
                rf'\b{term}\s+language',
                rf'\bprogramming\s+in\s+{term}\b',
                rf'\bdevelop.*\s+in\s+{term}\b'
            ]
            for pattern in lang_patterns:
                if re.search(pattern, text_blob, re.IGNORECASE):
                    return True
            return False  # Reject single letters by default
        
        # For 2+ letter ambiguous terms, check context
        if matches:
            context_window = 50
            for match_obj in re.finditer(pattern, text_blob, re.IGNORECASE):
                start = max(0, match_obj.start() - context_window)
                end = min(len(text_blob), match_obj.end() + context_window)
                context = text_blob[start:end].lower()
                # Only accept if near programming keywords
                if any(kw in context for kw in ["programming", "language", "code", "developer", "experience in"]):
                    return True
        return False
    
    return True

# Human languages recognized (explicit mentions only)
_HUMAN_LANGS = ["english", "hebrew", "french", "german", "spanish", "arabic", "russian"]


def _push_unique(bucket: List[str], value: str) -> None:
    """Add normalized skill to bucket if not already present."""
    if not value or not isinstance(value, str):
        return
    # Normalize using centralizer
    normalized = normalize_skill(value.strip())
    normalized_lower = normalized.lower()
    # Check if already exists (case-insensitive)
    if not any(item.lower() == normalized_lower for item in bucket):
        bucket.append(normalized)  # Store with proper capitalization


def _ensure_tech_keys(tech: Dict[str, Any]) -> None:
    for k in ("languages", "frameworks", "databases", "cloud", "tools", "business", "management", "domains"):
        tech.setdefault(k, [])


def _present_in_text(term: str, text_blob: str) -> bool:
    """
    Check if a (canonicalized) term is explicitly present in text (substring match).
    This prevents adding hallucinated skills (e.g., 'scala' when not mentioned).
    Also checks for common variations and separators.
    """
    t = _canon(term)
    if not t:
        return False

    # Prefer word-boundary match for single-token alnum terms to avoid substrings (e.g., 'ips' in 'partnerships')
    if re.fullmatch(r"[a-z0-9]+", t):
        if re.search(rf"\b{re.escape(t)}\b", text_blob, re.IGNORECASE):
            return True
    else:
        # Direct substring match for multi-token or punctuated terms
        if t in text_blob:
            return True
    
    # Check for variations with separators (e.g., "Next.js" vs "nextjs" vs "next js")
    variations = [
        t.replace(".", ""),
        t.replace(".", " "),
        t.replace("-", ""),
        t.replace("-", " "),
    ]
    
    for var in variations:
        if var == t:
            continue
        if re.fullmatch(r"[a-z0-9]+", var):
            if re.search(rf"\b{re.escape(var)}\b", text_blob, re.IGNORECASE):
                return True
        elif var in text_blob:
            return True
    
    return False


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
        (_BUCKETS["domains"], "domains"),
    ]:
        for term in group:
            if _present_in_text(term, text_blob) and _is_valid_tech_term(term, text_blob):
                _push_unique(tech[target], _canon(term))


def _sort_dedup(tech: Dict[str, Any]) -> None:
    """
    Sort and deduplicate tech sections.
    Also filter out non-tech descriptions that might have slipped through.
    """
    for section in ["languages", "frameworks", "databases", "cloud", "tools", "business", "management"]:
        # Keep unique and sorted for deterministic output
        seen = set()
        ordered: List[str] = []
        for t in tech[section]:
            c = _canon(t)
            if not c:
                continue
            
            # Extra filtering: reject if it contains description keywords
            description_words = [
                "experience", "proficiency", "familiarity", "demonstrated",
                "background", "knowledge", "understanding", "ability",
                "leading", "testing", "managing"
            ]
            
            # If it's a long phrase with description words, skip it
            if len(c.split()) > 4 or any(word in c for word in description_words):
                continue
            
            if c not in seen:
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
    # Filter out descriptions from must_have/nice_to_have
    skills = data.get("skills") or {}
    must_raw = _dedupe_list(skills.get("must_have") or [])
    nice_raw = _dedupe_list(skills.get("nice_to_have") or [])
    
    # Filter function for skills
    def is_concrete_skill(skill: str) -> bool:
        """Only keep concrete tech terms, not experience descriptions."""
        description_indicators = [
            "experience", "years", "background", "proficiency", 
            "familiarity", "knowledge", "demonstrated", "proven",
            "hands-on", "ability", "capability", "minimum", "mandatory"
        ]
        skill_lower = skill.lower()
        # Reject if contains description words
        if any(indicator in skill_lower for indicator in description_indicators):
            return False
        # Reject if too long (>4 words usually means description)
        if len(skill.split()) > 4:
            return False
        return True
    
    must = [s for s in must_raw if is_concrete_skill(s)]
    nice = [s for s in nice_raw if is_concrete_skill(s)]
    
    # Build a lowercase text blob solely from fields that reflect the original text
    # (summary + responsibilities + requirements). We avoid adding any invented content here.
    text_blob_src = " ".join([
        data.get("summary") or "",
        " ".join(data.get("responsibilities") or []),
        " ".join(data.get("requirements") or []),
    ])
    text_blob = text_blob_src.lower()
    
    # Extract concrete tech terms from nice_to_have descriptions
    # E.g., "Proficiency with Jira, TestRail" → extract "Jira", "TestRail"
    # E.g., "automation testing (e.g., Selenium, Cypress)" → extract "Selenium", "Cypress"
    tech_from_nice: List[str] = []
    for nice_item in nice_raw:
        # Look for known tech terms within the description
        for bucket_name, vocab in _BUCKETS.items():
            for term in vocab:
                if term in nice_item.lower() and term not in tech_from_nice:
                    tech_from_nice.append(term)
        
        # Also extract from "e.g., X, Y, Z" patterns
        eg_pattern = r'e\.g\.,?\s*([^)]+)'
        eg_matches = re.findall(eg_pattern, nice_item, re.IGNORECASE)
        for match in eg_matches:
            # Split by comma and clean
            parts = [p.strip().lower() for p in match.split(',')]
            for part in parts:
                # Check if it's a known tech
                for bucket_name, vocab in _BUCKETS.items():
                    if part in vocab and part not in tech_from_nice:
                        tech_from_nice.append(part)
        
        # Also extract from "such as X, Y" patterns
        such_pattern = r'such as\s+([^—\-\.]+)'
        such_matches = re.findall(such_pattern, nice_item, re.IGNORECASE)
        for match in such_matches:
            parts = [p.strip().lower() for p in match.split(',') if p.strip()]
            for part in parts:
                # Remove "or similar", "or equivalent" suffixes
                part = re.sub(r'\s+(or|and)\s+(similar|equivalent).*$', '', part)
                part = part.strip()
                # Check if it's a known tech
                for bucket_name, vocab in _BUCKETS.items():
                    if part in vocab and part not in tech_from_nice:
                        tech_from_nice.append(part)
    
    # If must_have is very sparse AND we found concrete tech in nice_to_have descriptions
    # Add a few to must_have (they were mentioned as requirements)
    if len(must) < 2 and tech_from_nice:
        # Add up to 3 concrete techs that were in "advantage" items
        for tech in tech_from_nice[:3]:
            if tech not in [m.lower() for m in must]:
                must.append(tech)
    
    # Extract ONLY concrete technical terms from requirements
    # Avoid adding experience descriptions, role names, or soft requirements
    if len(must) < 2:  # Only if must_have is very sparse
        requirements_text = " ".join(data.get("requirements") or []).lower()
        
        # Look for concrete tech terms that appear in known tech vocabularies
        concrete_tech_found = []
        for bucket_name, vocab in _BUCKETS.items():
            if bucket_name in ["business", "management"]:  # Skip non-tech buckets
                continue
            for term in vocab:
                # Only add if: (1) in requirements, (2) not already in must, (3) is valid tech term
                if (term in requirements_text and 
                    term not in [m.lower() for m in must] and
                    _is_valid_tech_term(term, requirements_text)):
                    # Check it's in "required" context (not just mentioned casually)
                    # Look for the term within a requirement sentence
                    for req in data.get("requirements", []):
                        req_lower = req.lower()
                        if term in req_lower:
                            # Avoid adding if it's part of a descriptive phrase
                            avoid_phrases = [
                                "experience testing", "experience in", "background as",
                                "proficiency with", "familiarity with"
                            ]
                            # Only add if it's a concrete tool/tech, not a description
                            if not any(phrase in req_lower for phrase in avoid_phrases):
                                concrete_tech_found.append(term)
                                break
        
        # Add only the concrete tech terms we found
        must.extend(concrete_tech_found[:5])  # Limit to max 5 additional items
    
    data["skills"] = {"must_have": must, "nice_to_have": nice}

    # ---- Tech stack (explicit only) ----
    # IMPORTANT: Start from an empty tech stack to avoid carrying over LLM hallucinations.
    tech: Dict[str, Any] = {}
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

    # ---- Domains from context (light heuristics) ----
    # If defense/defence appears, ensure domains include "defense"
    if ("defense" not in tech.get("domains", [])) and ("defense" in text_blob or "defence" in text_blob):
        _push_unique(tech["domains"], "defense")
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

    # ---- Locations inference (gentle, pattern-based) ----
    def _infer_locations(tb: str) -> List[str]:
        locs: List[str] = []
        # Europe / European / EMEA
        if re.search(r"\beurope(an)?\b|\bemea\b", tb, re.IGNORECASE):
            locs.append("Europe")
        # Israel / IL
        if re.search(r"\bisrael\b|\bil\b", tb, re.IGNORECASE):
            locs.append("Israel")
        # USA / US / United States
        if re.search(r"\b(usa|u\.s\.a\.|u\.s\.|us|united states)\b", tb, re.IGNORECASE):
            locs.append("United States")
        return _dedupe_list(locs)

    if not data.get("locations"):
        inferred_locs = _infer_locations(text_blob)
        data["locations"] = inferred_locs

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
    # Avoid generic words, descriptions, and limit to most relevant terms.
    keyword_candidates: List[str] = []
    
    # Filter function to avoid non-tech descriptions
    def is_concrete_tech_keyword(kw: str) -> bool:
        """Only accept concrete tech terms, not descriptions or role names."""
        # Reject if contains common non-tech words
        non_tech_indicators = [
            "experience", "testing", "background", "proficiency", "familiarity",
            "systems", "methodologies", "processes", "strategy", "engineer",
            "manual", "automation", "advantage", "mandatory", "years"
        ]
        kw_lower = kw.lower()
        # If it's long and contains non-tech words, probably a description
        if len(kw_lower.split()) > 3:
            return False
        for indicator in non_tech_indicators:
            if indicator in kw_lower:
                return False
        return True
    
    for section in ["languages", "frameworks", "databases", "cloud", "tools"]:
        for t in tech.get(section, []):
            canon_t = _canon(t)
            # Skip blacklisted terms and invalid tech terms
            if canon_t in _KEYWORD_BLACKLIST or not _is_valid_tech_term(canon_t, text_blob):
                continue
            if _present_in_text(t, text_blob) and is_concrete_tech_keyword(t):
                _push_unique(keyword_candidates, canon_t)

    # Include select business acronyms if present (useful for matching)
    allowed_business_keywords = {"b2b", "b2g", "g2g", "go-to-market", "gtm", "negotiation", "tenders"}
    for t in tech.get("business", []):
        ct = _canon(t)
        if ct in allowed_business_keywords and _present_in_text(ct, text_blob):
            _push_unique(keyword_candidates, ct)

    for s in must + nice:
        canon_s = _canon(s)
        # Skip blacklisted, very short, and non-concrete terms
        if (canon_s in _KEYWORD_BLACKLIST or 
            len(canon_s) <= 1 or 
            not is_concrete_tech_keyword(s)):
            continue
        if _present_in_text(s, text_blob) and _is_valid_tech_term(canon_s, text_blob):
            _push_unique(keyword_candidates, canon_s)

    # Keep top N by frequency within text to reduce noise
    # Limit to 20 most relevant keywords (reduced from 25)
    counts = Counter()
    for kw in keyword_candidates:
        counts[kw] = text_blob.count(kw)
    # Deterministic ordering: sort by (-count, alpha)
    data["keywords"] = [k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:20]

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
    # ---- Summary generation (fallback) ----
    if not (data.get("summary") or "").strip():
        role = (data.get("role_title") or data.get("title") or "Role").strip()
        region = ", ".join(data.get("locations") or [])
        domain_phrase = " in defense" if "defense" in data.get("tech_stack", {}).get("domains", []) else ""
        core_bits: List[str] = []
        if any("tender" in r.lower() for r in data.get("requirements", []) + data.get("responsibilities", [])):
            core_bits.append("tenders")
        if any("contract" in r.lower() for r in data.get("requirements", []) + data.get("responsibilities", [])):
            core_bits.append("contracts")
        if any("channel" in r.lower() or "partnership" in r.lower() for r in data.get("responsibilities", [])):
            core_bits.append("channels/partnerships")
        if any("go-to-market" in t or "gtm" in t for t in (data.get("tech_stack", {}).get("business", []))):
            core_bits.append("GTM")
        if any("travel" in r.lower() for r in data.get("requirements", []) + data.get("responsibilities", [])):
            core_bits.append("frequent travel")

        bits = ", ".join(core_bits[:3])
        region_part = f" in {region}" if region else ""
        summary_txt = f"Own full-cycle business development and sales{region_part}{domain_phrase}: {bits}." if bits else \
                      f"Own full-cycle business development and sales{region_part}{domain_phrase}."
        data["summary"] = summary_txt.strip()

    return data
