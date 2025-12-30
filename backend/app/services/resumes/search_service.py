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

