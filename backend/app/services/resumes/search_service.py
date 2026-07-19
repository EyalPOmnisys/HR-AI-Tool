from app.services.common.llm_client import default_llm_client, load_prompt
from app.schemas.resume import ResumeSearchAnalysis
import logging

logger = logging.getLogger(__name__)

def analyze_search_query(query: str) -> ResumeSearchAnalysis:
    """
    Analyzes a natural language search query and extracts structured filters.
    """
    logger.info(f"Analyzing search query: {query}")
    prompt_template = load_prompt("resumes/search_query_analysis.prompt.txt")
    
    messages = [
        {"role": "system", "content": "You are a helpful HR assistant."},
        {"role": "user", "content": prompt_template.format(query=query)}
    ]

    response = default_llm_client.chat_json(messages=messages)
    data = response.data
    
    logger.info(f"LLM Response data: {data}")

    # Handle LLM errors gracefully by falling back to free text
    if "__llm_error__" in data:
        logger.error(f"LLM Error encountered: {data}")
        return ResumeSearchAnalysis(free_text=query)
    
    # Normalize skills to Title Case to ensure DB matching
    raw_skills = data.get("skills", [])
    normalized_skills = []
    for skill in raw_skills:
        if isinstance(skill, str):
            # Capitalize first letter (e.g. "python" -> "Python")
            normalized_skills.append(skill[0].upper() + skill[1:] if len(skill) > 0 else skill)
        else:
            normalized_skills.append(skill)

    result = ResumeSearchAnalysis(
        profession=data.get("profession", []),
        min_experience=data.get("min_experience"),
        max_experience=data.get("max_experience"),
        skills=normalized_skills,
        free_text=None,
        exclude_keywords=data.get("exclude_keywords", [])
    )
    logger.info(f"Parsed analysis result: {result}")
    return result


def expand_related_titles(title: str) -> list[str]:
    """Use the LLM to expand a role title into the job titles that strong
    candidates would realistically have on their resume - synonyms, adjacent
    roles, and seniority variants (e.g. "DevOps Engineer" -> Platform Engineer,
    SRE, Infrastructure Engineer, Senior DevOps...).

    Powers title-based narrowing of resume search: title is a far stronger and
    tighter filter than skills alone, and one exact title misses phrasing
    variants ("System Analyst" vs "Systems Analyst"). Returns the original
    title plus related ones. Falls back to just the original on any error.
    """
    title = (title or "").strip()
    if not title:
        return []

    logger.info(f"Expanding related titles for: {title}")
    system = (
        "You are an expert technical recruiter. Given a JOB TITLE, list the job "
        "titles that STRONG candidates for this role realistically have on their "
        "resume: close synonyms, adjacent roles, and common seniority variants "
        "(Junior/Senior/Lead). Stay tight and on-domain - do NOT drift to unrelated "
        "fields. Include singular/plural and common spellings. "
        'Return ONLY JSON: {"titles": ["...", "..."]} with 6-12 short titles.'
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Job title: {title}"},
    ]
    resp = default_llm_client.chat_json(messages=messages)
    data = resp.data or {}
    if "__llm_error__" in data:
        logger.error(f"related-titles LLM error: {data}")
        return [title]

    raw = data.get("titles") or data.get("related_titles") or data.get("job_titles") or []
    out: list[str] = []
    seen: set[str] = set()
    for t in [title] + list(raw):
        if isinstance(t, str) and t.strip() and t.strip().lower() not in seen:
            out.append(t.strip())
            seen.add(t.strip().lower())
    return out[:12]

