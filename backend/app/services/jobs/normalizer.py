import re
import logging
from typing import Dict, Any, List
from collections import Counter

logger = logging.getLogger("jobs.normalizer")

# Canonical names/aliases for tech normalization
_ALIAS_TO_CANON = {
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "node": "Node.js",
    "node.js": "Node.js",
    "express": "Express.js",
    "express.js": "Express.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "redis": "Redis",
    "zod": "Zod",
    "tanstack-query": "TanStack Query",
    "tanstack query": "TanStack Query",
    "mui": "MUI",
    "material ui": "MUI",
    "opentelemetry": "OpenTelemetry",
    "open telemetry": "OpenTelemetry",
    "websocket": "WebSockets",
    "websockets": "WebSockets",
    "rest": "REST",
    "vite": "Vite",
    "drizzle-orm": "Drizzle ORM",
    "drizzle orm": "Drizzle ORM",
    "react": "React",
    "react.js": "React",
}

# Buckets (lowercase keys)
_BUCKETS = {
    "languages": {"javascript", "typescript", "python", "java", "go", "ruby", "rust", "scala", "php", "swift", "kotlin", "c#", "c++"},
    "frameworks": {"react", "express", "express.js", "spring", "django", "flask", "fastapi", "angular", "vue", "nextjs", "nuxt", "dotnet", "tailwind", "bootstrap"},
    "databases": {"postgres", "postgresql", "mysql", "mariadb", "mongodb", "snowflake", "bigquery", "oracle", "redis", "dynamodb", "elasticsearch"},
    "cloud": {"aws", "azure", "gcp", "digitalocean", "heroku"},
    "tools": {
        "git","docker","kubernetes","jenkins","terraform","ansible","jira","confluence","notion","slack","figma",
        "selenium","cypress","appium","testrail","testng","junit","pytest","postman","soapui","jmeter","vscode","intellij",
        "powershell","bash","shell","excel","powerbi","tableau","opentelemetry","websockets","rest","vite","zod","tanstack-query","mui","drizzle-orm"
    },
    "business": {"crm","salesforce","hubspot","b2b","b2c","marketing","negotiation","lead generation","account management","pipeline","forecast","customer success"},
    "management": {"agile","scrum","kanban","ci/cd","devops","waterfall","qa strategy","risk management","stakeholder management","mentoring","coaching","leadership","budgeting","planning"},
}

def _canon(term: str) -> str:
    t = (term or "").strip()
    if not t:
        return ""
    key = t.lower()
    return _ALIAS_TO_CANON.get(key, t.strip().title() if key in {"rest"} else t.strip())

def _push_unique(bucket: List[str], value: str) -> None:
    v = value.strip()
    if v and v not in bucket:
        bucket.append(v)

def _ensure_tech_keys(tech: Dict[str, Any]) -> None:
    for k in ("languages","frameworks","databases","cloud","tools","business","management"):
        tech.setdefault(k, [])

def _scan_and_fill_from_text(text_blob: str, tech: Dict[str, Any]) -> None:
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
    for section in ["languages","frameworks","databases","cloud","tools","business","management"]:
        tech[section] = sorted(list({_canon(t) for t in tech[section] if t}))

def _infer_work_mode_and_location(text_blob: str, data: Dict[str, Any]) -> None:
    # Work mode
    if not data.get("work_mode"):
        if any(w in text_blob for w in ["work from our office", "from our office", "onsite", "on-site"]):
            data["work_mode"] = "Onsite"
        elif "hybrid" in text_blob:
            data["work_mode"] = "Hybrid"
        elif any(w in text_blob for w in ["remote", "work from home"]):
            data["work_mode"] = "Remote"

    # Location (simple heuristics for sample)
    locs = set(data.get("locations") or [])
    if any(w in text_blob for w in ["ramat-gan", "ramat gan", "ramat-gan,", "ramat-gan.", "bursa"]):
        locs.add("Ramat Gan, Israel")
    if locs:
        data["locations"] = sorted(locs)

def normalize_job_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Normalizing job analysis JSON")
    tech = data.get("tech_stack") or {}
    skills = data.get("skills") or {}
    must = [s for s in skills.get("must_have", []) if s]
    nice = [s for s in skills.get("nice_to_have", []) if s]
    data["skills"] = {"must_have": must, "nice_to_have": nice}

    _ensure_tech_keys(tech)

    # From skills into tech buckets
    all_skills = must + nice
    for raw in all_skills:
        key = raw.lower().strip()
        for bucket_name, items in _BUCKETS.items():
            if key in items:
                _push_unique(tech[bucket_name], _canon(raw))

    text_blob = " ".join((data.get("summary") or "", " ".join(data.get("responsibilities", [])), " ".join(data.get("requirements", [])))).lower()

    # From free-text into buckets
    _scan_and_fill_from_text(text_blob, tech)
    _sort_dedup(tech)

    # Experience min (fallback)
    if not (data.get("experience") or {}).get("years_min"):
        m = re.search(r"(\d+)\+?\s+year", text_blob)
        if m:
            data.setdefault("experience", {})["years_min"] = int(m.group(1))

    # Languages of candidate (not coding langs)
    if not data.get("languages"):
        langs = []
        for lang in ["english", "hebrew", "french", "german", "spanish", "arabic", "russian"]:
            if lang in text_blob:
                langs.append({"name": lang.capitalize(), "level": None})
        if not langs:
            # default to English for typical JD
            langs = [{"name": "English", "level": None}]
        data["languages"] = langs

    # Keywords (fallback)
    if not data.get("keywords"):
        words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]+", text_blob) if len(w) > 3]
        counter = Counter(words)
        data["keywords"] = [w for w, _ in counter.most_common(20)]

    # Work mode + location inference
    _infer_work_mode_and_location(text_blob, data)

    # Enrich management if hiring/mentoring present
    if any(kw in text_blob for kw in ["hire", "hiring", "mentor", "mentoring", "teach", "coaching"]):
        _push_unique(tech["management"], "Mentoring")
        _sort_dedup(tech)

    data["tech_stack"] = tech

    # Pre-compute simple evidence indices assuming chunk layout from chunker:
    # [optional summary], responsibilities..., requirements..., [tech_stack], [notes]
    resps = data.get("responsibilities") or []
    reqs = data.get("requirements") or []
    has_summary = bool((data.get("summary") or "").strip())
    base = 1 if has_summary else 0
    ev = {
        "responsibilities": list(range(base, base + len(resps))),
        "requirements": list(range(base + len(resps), base + len(resps) + len(reqs))),
        "tech_stack": [base + len(resps) + len(reqs)] if any(tech.values()) else [],
    }
    data["evidence"] = ev

    logger.info("Normalization done: %d responsibilities, %d requirements, tech sections: %s",
                len(resps), len(reqs), ", ".join([k for k in tech if tech[k]]))
    return data
