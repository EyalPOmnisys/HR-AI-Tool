# app/services/normalizer.py
from typing import Dict, Any

def normalize_job_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize tech_stack and enrich missing fields without hallucinating."""

    tech = data.get("tech_stack", {})
    must = data.get("skills", {}).get("must_have", [])
    nice = data.get("skills", {}).get("nice_to_have", [])

    all_skills = {s.lower(): s for s in must + nice}

    languages = {"python", "java", "go", "c#", "c++", "typescript", "javascript", "ruby", "rust"}
    frameworks = {"spark", "airflow", "flask", "django", "fastapi", "react", "vue"}
    databases = {"sql", "postgres", "mysql", "mongodb", "snowflake", "bigquery"}
    cloud = {"aws", "azure", "gcp"}

    tech.setdefault("languages", [])
    tech.setdefault("frameworks", [])
    tech.setdefault("databases", [])

    for key, val in all_skills.items():
        if key in languages and val not in tech["languages"]:
            tech["languages"].append(val)
        elif key in frameworks and val not in tech["frameworks"]:
            tech["frameworks"].append(val)
        elif key in databases and val not in tech["databases"]:
            tech["databases"].append(val)
        elif key in cloud and val not in tech["frameworks"]:
            tech["frameworks"].append(val)

    data["tech_stack"] = tech

    if not data.get("responsibilities") and data.get("summary"):
        summary = data["summary"].lower()
        base_resps = []
        if "pipeline" in summary:
            base_resps.append("Design and maintain data pipelines")
        if "infrastructure" in summary:
            base_resps.append("Maintain data infrastructure")
        if "collaborate" in summary or "data scientist" in summary:
            base_resps.append("Collaborate with data scientists to improve models")
        if base_resps:
            data["responsibilities"] = base_resps

    return data
