from app.services.common.llm_client import default_llm_client, load_prompt
from app.schemas.resume import ResumeSearchAnalysis, ResumeScoringRequest, ResumeScoringResponse, ResumeScore
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
    
    result = ResumeSearchAnalysis(
        profession=data.get("profession", []),
        min_experience=data.get("min_experience"),
        max_experience=data.get("max_experience"),
        skills=data.get("skills", []),
        free_text=None
    )
    logger.info(f"Parsed analysis result: {result}")
    return result


def score_resumes(request: ResumeScoringRequest) -> ResumeScoringResponse:
    """
    Scores a list of resumes against a job description/query.
    """
    logger.info(f"Scoring {len(request.candidates)} resumes for query: {request.query}")
    
    # Format candidates for the prompt
    candidates_text = ""
    for cand in request.candidates:
        skills_str = ", ".join([s.name for s in cand.skills])
        candidates_text += f"""
Candidate ID: {cand.id}
Name: {cand.name or 'Unknown'}
Profession: {cand.profession or 'Unknown'}
Summary: {cand.summary or 'No summary'}
Experience: {cand.years_of_experience or 0} years
Skills: {skills_str}
-------------------
"""

    prompt_template = load_prompt("resumes/resume_scoring.prompt.txt")
    
    messages = [
        {"role": "system", "content": "You are an expert Technical Recruiter."},
        {"role": "user", "content": prompt_template.format(job_description=request.query, candidates=candidates_text)}
    ]

    response = default_llm_client.chat_json(messages=messages)
    data = response.data
    
    logger.info(f"LLM Scoring Response: {data}")

    if "__llm_error__" in data:
        logger.error(f"LLM Error in scoring: {data}")
        return ResumeScoringResponse(scores=[])
        
    scores_data = data.get("scores", [])
    scores = []
    for item in scores_data:
        try:
            scores.append(ResumeScore(
                id=item["id"],
                score=item["score"],
                reason=item["reason"]
            ))
        except Exception as e:
            logger.error(f"Error parsing score item {item}: {e}")
            
    return ResumeScoringResponse(scores=scores)
