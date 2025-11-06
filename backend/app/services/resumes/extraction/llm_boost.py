"""LLM-based post-processing to fill resume fields missing from deterministic parsing."""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings
from app.services.common.llm_client import default_llm_client, load_prompt

# Keeping the prompt on disk ensures every LLM instruction lives under app/prompts.
RESUME_EXTRACTION_PROMPT = load_prompt("resumes/resume_extraction.prompt.txt")


def _dedupe_list_of_dicts(items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    """
    Deduplicate dictionaries by a given key (case-insensitive for strings).
    Keeps first occurrence, preserves order.
    """
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items or []:
        v = it.get(key)
        if isinstance(v, str):
            k = v.strip().lower()
        else:
            k = str(v)
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def _merge_skills(base: List[Dict[str, Any]], add: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge skills arrays, dedupe by name, and keep the higher confidence where possible.
    """
    by_name: Dict[str, Dict[str, Any]] = {}
    for src in (base or []):
        if not isinstance(src, dict) or not src.get("name"):
            continue
        by_name[src["name"].lower()] = src

    for src in (add or []):
        if not isinstance(src, dict) or not src.get("name"):
            continue
        key = src["name"].lower()
        if key not in by_name:
            by_name[key] = src
        else:
            # Keep higher confidence
            if src.get("confidence", 0) > by_name[key].get("confidence", 0):
                by_name[key]["confidence"] = src["confidence"]
            # Merge provenance ranges if available
            if src.get("provenance") and by_name[key].get("provenance"):
                by_name[key]["provenance"].extend(src["provenance"])

    # Optional: clamp provenance len to avoid huge payloads
    for v in by_name.values():
        prov = v.get("provenance")
        if isinstance(prov, list) and len(prov) > 20:
            v["provenance"] = prov[:20]
    return list(by_name.values())


def llm_enhance(parsed_text: str, current_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optionally call an LLM to fill missing high-level fields.
    The LLM is asked to RETURN JSON ONLY (schema-aligned).
    """
    if not getattr(settings, "USE_LLM_EXTRACTION", False):
        return current_json

    need_person_name = (current_json.get("person", {}) or {}).get("name") in (None, "")
    need_exp = not current_json.get("experience")
    need_edu = not current_json.get("education")
    need_skills_topup = True  # Allow LLM to add skills not caught deterministically

    if not (need_person_name or need_exp or need_edu or need_skills_topup):
        return current_json

    user = (
        "TEXT:\n"
        f"{parsed_text}\n\n"
        "CURRENT_JSON:\n"
        f"{current_json}\n"
        "Return JSON only."
    )
    messages = [
        {"role": "system", "content": RESUME_EXTRACTION_PROMPT},
        {"role": "user", "content": user},
    ]

    try:
        llm_json = default_llm_client.chat_json(messages, timeout=120).data
        if not isinstance(llm_json, dict):
            return current_json
    except Exception:
        # Fail open to deterministic result
        return current_json

    merged = dict(current_json)

    # --- Person ---
    person_base = dict(merged.get("person", {}) or {})
    person_llm = dict((llm_json.get("person") or {}))
    conf = person_base.setdefault("confidence_details", {})

    if need_person_name and person_llm.get("name"):
        person_base["name"] = person_llm["name"]
        conf["name"] = max(0.75, conf.get("name", 0))

    if person_llm.get("location") and not person_base.get("location"):
        person_base["location"] = person_llm["location"]
        conf["location"] = max(0.7, conf.get("location", 0))

    if person_llm.get("languages") and not person_base.get("languages"):
        person_base["languages"] = person_llm["languages"]
        conf["languages"] = max(0.7, conf.get("languages", 0))

    merged["person"] = person_base

    # --- Education ---
    if need_edu and llm_json.get("education"):
        merged["education"] = llm_json["education"]
        merged.setdefault("confidence", {})["education"] = 0.7

    # --- Experience ---
    if need_exp and llm_json.get("experience"):
        merged["experience"] = llm_json["experience"]
        merged.setdefault("confidence", {})["experience"] = 0.7

    # --- Skills (top-up & dedupe) ---
    base_skills = merged.get("skills") or []
    llm_skills = (llm_json.get("skills") or []) if isinstance(llm_json.get("skills"), list) else []
    merged["skills"] = _merge_skills(base_skills, llm_skills)

    # Clamp large arrays for storage safety (optional)
    if len(merged.get("skills", [])) > 200:
        merged["skills"] = merged["skills"][:200]

    return merged
