from __future__ import annotations
from typing import Dict, Any, List
from app.core.config import settings
from app.services.embedding_service import get_embedding  
from app.services.llm_service import _post_chat 

PROMPT = """You are an information extractor for resumes (HE/EN). 
Return ONLY JSON. Fill missing fields in this schema:
{
  "person": { "name": string|null, "location": string|null, "languages": [string] },
  "education": [{"degree": string|null, "field": string|null, "institution": string|null, "start_date": string|null, "end_date": string|null}],
  "experience": [{"title": string|null, "company": string|null, "location": string|null, "start_date": string|null, "end_date": string|null, "bullets":[string], "tech":[string]}]
}
Use what is present; do not hallucinate. If unknown, use null or [].
"""

def llm_enhance(parsed_text: str, current_json: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.USE_LLM_EXTRACTION:
        return current_json

    need_person_name = current_json.get("person", {}).get("name") in (None, "",)
    need_exp = not current_json.get("experience")
    need_edu = not current_json.get("education")

    if not (need_person_name or need_exp or need_edu):
        return current_json

    user = f"TEXT:\n{parsed_text}\n\nCURRENT_JSON:\n{current_json}\nReturn JSON only."
    messages = [{"role": "system", "content": PROMPT}, {"role": "user", "content": user}]
    try:
        llm_json = _post_chat(messages, timeout=120)
    except Exception:
        return current_json 

    merged = dict(current_json)
    person = dict(merged.get("person", {}))
    if need_person_name and llm_json.get("person", {}).get("name"):
        person["name"] = llm_json["person"]["name"]
        person.setdefault("confidence_details", {})["name"] = 0.75
    if llm_json.get("person", {}).get("location") and not person.get("location"):
        person["location"] = llm_json["person"]["location"]
        person.setdefault("confidence_details", {})["location"] = 0.7
    if llm_json.get("person", {}).get("languages") and not person.get("languages"):
        person["languages"] = llm_json["person"]["languages"]
        person.setdefault("confidence_details", {})["languages"] = 0.7
    merged["person"] = person

    if need_edu and llm_json.get("education"):
        merged["education"] = llm_json["education"]
        merged.setdefault("confidence", {})["education"] = 0.7

    if need_exp and llm_json.get("experience"):
        merged["experience"] = llm_json["experience"]
        merged.setdefault("confidence", {})["experience"] = 0.7

    return merged
