# app/services/normalizer.py
import re
import json
from typing import Dict, Any, List
from collections import Counter

def normalize_job_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    tech = data.get("tech_stack", {})
    skills = data.get("skills", {})
    must = skills.get("must_have", [])
    nice = skills.get("nice_to_have", [])
    all_skills = {s.lower().replace("advantage", "").replace("experience", "").replace("knowledge of", "").strip(): s for s in must + nice}

    languages = {"python", "java", "go", "c#", "c++", "typescript", "javascript", "ruby", "rust", "scala", "php", "swift", "kotlin"}
    frameworks = {"spark", "airflow", "flask", "django", "fastapi", "react", "vue", "angular", "node", "express", "spring", "dotnet", "nextjs", "nuxt", "tailwind", "bootstrap"}
    databases = {"sql", "postgres", "mysql", "mariadb", "mongodb", "snowflake", "bigquery", "oracle", "redis", "dynamodb", "elasticsearch"}
    cloud = {"aws", "azure", "gcp", "digitalocean", "heroku"}
    tools = {"git", "docker", "kubernetes", "jenkins", "terraform", "ansible", "jira", "confluence", "notion", "slack", "figma"}
    sales = {"crm", "salesforce", "hubspot", "b2b", "b2c", "marketing", "negotiation", "lead generation", "account management", "pipeline", "forecast", "cold calling"}
    data_tools = {"pandas", "numpy", "matplotlib", "powerbi", "tableau", "excel", "looker", "databricks"}

    tech.setdefault("languages", [])
    tech.setdefault("frameworks", [])
    tech.setdefault("databases", [])
    tech.setdefault("cloud", [])
    tech.setdefault("tools", [])
    tech.setdefault("business", [])

    for key, val in all_skills.items():
        if key in languages and val not in tech["languages"]:
            tech["languages"].append(val)
        elif key in frameworks and val not in tech["frameworks"]:
            tech["frameworks"].append(val)
        elif key in databases and val not in tech["databases"]:
            tech["databases"].append(val)
        elif key in cloud and val not in tech["cloud"]:
            tech["cloud"].append(val)
        elif key in tools and val not in tech["tools"]:
            tech["tools"].append(val)
        elif key in sales and val not in tech["business"]:
            tech["business"].append(val)
        elif key in data_tools and val not in tech["tools"]:
            tech["tools"].append(val)

    text_blob = " ".join(data.get("responsibilities", []) + data.get("requirements", [])).lower()
    for group, target in [
        (languages, "languages"),
        (frameworks, "frameworks"),
        (databases, "databases"),
        (cloud, "cloud"),
        (tools, "tools"),
        (sales, "business"),
        (data_tools, "tools"),
    ]:
        for term in group:
            if term in text_blob and term.capitalize() not in tech[target]:
                tech[target].append(term.capitalize())

    for section in ["languages", "frameworks", "databases", "cloud", "tools", "business"]:
        tech[section] = sorted(list({t.strip() for t in tech[section] if t}))

    data["skills"]["must_have"] = [s for s in must if s]
    data["skills"]["nice_to_have"] = [s for s in nice if s]

    if not data.get("experience", {}).get("years_min"):
        match = re.search(r"(\d+)\+?\s+year", text_blob)
        if match:
            data.setdefault("experience", {})["years_min"] = int(match.group(1))

    if not data.get("languages"):
        langs = []
        for lang in ["english", "hebrew", "french", "german", "spanish", "arabic"]:
            if lang in text_blob:
                langs.append({"name": lang.capitalize(), "level": None})
        data["languages"] = langs

    if not data.get("keywords"):
        words = [w for w in re.findall(r"[a-zA-Z]+", text_blob) if len(w) > 3]
        counter = Counter(words)
        data["keywords"] = [w for w, c in counter.most_common(8)]

    if not data.get("responsibilities") and data.get("summary"):
        summary = data["summary"].lower()
        base_resps: List[str] = []
        if "pipeline" in summary:
            base_resps.append("Design and maintain data pipelines")
        if "sales" in summary:
            base_resps.append("Drive sales processes and client relationships")
        if "qa" in summary or "testing" in summary:
            base_resps.append("Perform system and software quality assurance testing")
        if "project" in summary:
            base_resps.append("Manage project timelines and deliverables")
        if base_resps:
            data["responsibilities"] = base_resps

    data["tech_stack"] = tech
    return data
