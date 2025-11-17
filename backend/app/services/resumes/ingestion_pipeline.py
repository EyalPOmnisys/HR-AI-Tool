# app/services/resumes/ingestion_pipeline.py
"""
Resume Ingestion Pipeline - End-to-end processing from file upload to searchable resume.
Handles parsing, extraction, chunking, embedding, and API response formatting for resume data.
"""
# -----------------------------------------------------------------------------
# CHANGELOG (English-only comments)
# - get_resume_detail(): expose years_by_category (from extraction_json.experience_meta.totals_by_category)
#   and primary_years (prefer LLM recommended_primary_years["tech"], fallback to deterministic totals["tech"]).
# - _resume_to_summary(): use primary years if available; fallback retains previous behavior.
# - compute_years_of_experience remains for backward compatibility.
# - Date parsing updated to support month-name formats (e.g., "Jan 2020", "January 2020", "March 3, 2024").
# - No new imports/files; only enrich returned dicts and parsing robustness.
# -----------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resume import Resume
from app.repositories import resume_repo
from app.services.common.embedding_client import default_embedding_client
from app.services.resumes.parsing_utils import (
    read_file_bytes,
    detect_mime,
    sha256_of_bytes,
    parse_to_text,
    chunk_resume_text,
)
from app.services.resumes.extraction_pipeline import extract_structured
from app.services.resumes.embedding_utils import (
    enrich_chunk_for_embedding,
    create_search_optimized_embedding_text,
)
from app.services.resumes.validation import validate_extraction, create_quality_report


# ---------------------------------------------------------------------
# INGESTION & PIPELINE STEPS
# ---------------------------------------------------------------------

def ingest_file(db: Session, path: Path) -> Resume:
    data = read_file_bytes(path)
    content_hash = sha256_of_bytes(data)

    existing = resume_repo.get_by_hash(db, content_hash)
    if existing:
        return existing

    mime = detect_mime(path)
    resume = resume_repo.create_resume(
        db,
        file_path=str(path),
        content_hash=content_hash,
        mime_type=mime,
        file_size=len(data),
    )
    return resume


def parse_and_extract(db: Session, resume: Resume) -> Resume:
    try:
        resume_repo.set_status(db, resume, status="parsing")
        txt = parse_to_text(Path(resume.file_path))
        resume = resume_repo.attach_parsed_text(db, resume, parsed_text=txt or "")

        resume_repo.set_status(db, resume, status="extracting")
        resume = extract_structured(db, resume)

        # Validate extraction quality
        if resume.extraction_json:
            validation = validate_extraction(resume.extraction_json)
            
            # Add quality report to extraction_json
            if "meta" not in resume.extraction_json:
                resume.extraction_json["meta"] = {}
            resume.extraction_json["meta"]["quality_report"] = validation.summary
            
            # Log warnings
            if validation.warnings:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Resume {resume.id} quality warnings: {validation.warnings}")
            
            # If critical errors, mark status
            if not validation.is_valid:
                resume_repo.set_status(
                    db, 
                    resume, 
                    status="warning",
                    error=f"Quality issues: {', '.join(validation.errors[:3])}"
                )
            else:
                resume_repo.set_status(db, resume, status="parsed")
        else:
            resume_repo.set_status(db, resume, status="parsed")
        
        return resume

    except Exception as e:
        resume_repo.set_status(db, resume, status="error", error=str(e))
        raise


def chunk_and_embed(db: Session, resume: Resume) -> Resume:
    if not resume.parsed_text:
        return resume

    chunks = chunk_resume_text(resume.parsed_text)
    chunks = resume_repo.bulk_add_chunks(db, resume, chunks)

    # Get person name from extraction for enrichment
    extraction = resume.extraction_json or {}
    person = extraction.get("person", {})
    person_name = person.get("name")

    # Create optimized full-resume embedding
    try:
        full_text = create_search_optimized_embedding_text(resume)
        full_emb = default_embedding_client.embed(full_text)
        resume_repo.attach_resume_embedding(db, resume, embedding=full_emb)
    except Exception as e:
        resume_repo.set_status(
            db,
            resume,
            status="parsed",
            error=f"full embedding failed: {e}",
        )

    # Embed each chunk with enrichment
    resume_repo.set_status(db, resume, status="embedding")
    model = getattr(settings, "EMBEDDING_MODEL", None)
    version = getattr(settings, "ANALYSIS_VERSION", None)

    any_failure = False
    for ch in chunks:
        try:
            # Enrich chunk text with context for better embeddings
            enriched_text = enrich_chunk_for_embedding(
                chunk=ch,
                resume=resume,
                person_name=person_name,
                extraction_json=extraction
            )
            
            emb = default_embedding_client.embed(enriched_text)
            resume_repo.upsert_chunk_embedding(
                db, ch, embedding=emb, model=model, version=version
            )
        except Exception as e:
            any_failure = True
            resume_repo.note_chunk_error(db, ch, error=str(e))

    resume_repo.set_status(db, resume, status=("ready" if not any_failure else "warning"))
    return resume


# ---------------------------------------------------------------------
# LISTING & DETAIL (API COMPATIBILITY)
# ---------------------------------------------------------------------

def list_resume_summaries(
    db: Session, *, offset: int = 0, limit: int = 20
) -> tuple[list[dict[str, Any]], int]:
    rows, total = resume_repo.list_resumes(db, offset=offset, limit=limit)
    items = [_resume_to_summary(row) for row in rows]
    return items, total


def get_resume_detail(db: Session, resume_id: UUID) -> Optional[dict[str, Any]]:
    resume = resume_repo.get_resume(db, resume_id)
    if not resume:
        return None

    extraction = resume.extraction_json or {}
    person = extraction.get("person") or {}

    # Contacts (email/phone only)
    contacts = _extract_contacts(person)
    skills = _extract_skills(extraction)
    experience_entries = _extract_experience(extraction)
    education_entries = _extract_education(extraction)
    languages = _extract_languages(extraction)

    # Derive years_by_category + primary_years if available
    exp_meta = extraction.get("experience_meta") or {}
    totals_by_category = exp_meta.get("totals_by_category") or {}
    rec_primary = exp_meta.get("recommended_primary_years") or {}

    primary_years = None
    if isinstance(rec_primary, dict):
        primary_years = rec_primary.get("tech")
    if primary_years is None and isinstance(totals_by_category, dict):
        primary_years = totals_by_category.get("tech")

    detail = {
        "id": resume.id,
        "name": _clean(person.get("name")) or _infer_name_from_path(resume.file_path),
        "profession": _extract_profession(extraction.get("experience") or []),
        "years_of_experience": _compute_years_of_experience(extraction.get("experience") or []),
        "resume_url": f"/resumes/{resume.id}/file",
        "status": resume.status or "parsed",
        "file_name": Path(resume.file_path).name if resume.file_path else None,
        "mime_type": resume.mime_type,
        "file_size": resume.file_size,
        "summary": None,
        "contacts": contacts,
        "skills": skills,
        "experience": experience_entries,
        "education": education_entries,
        "languages": languages,
        "created_at": resume.created_at,
        "updated_at": resume.updated_at,
        # New fields:
        "years_by_category": totals_by_category or {},
        "primary_years": primary_years,
    }
    return detail


# ----------------------------- Helpers -----------------------------

def _extract_contacts(person: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for em in person.get("emails") or []:
        val = (em or {}).get("value")
        if _clean(val):
            out.append({"type": "email", "label": None, "value": val})
    for ph in person.get("phones") or []:
        val = (ph or {}).get("value")
        if _clean(val):
            out.append({"type": "phone", "label": None, "value": val})
    return out


def _extract_skills(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract skills with source and weight information.
    Returns list of SkillItem dicts: {name, source, weight, category?}
    
    Logic:
    1. Skills from experience.tech that appear in bullets -> source: work_experience, weight: 1.0
    2. Skills from experience.tech that don't appear in bullets -> source: skills_list, weight: 0.4
    3. Skills from extraction.skills (if provided) -> use their source/weight
    
    Keeps only the highest-weighted occurrence of each skill.
    """
    seen = {}  # skill_name.lower() -> {name, source, weight, category}
    
    # First pass: collect all skills mentioned in experience bullets
    experience_skills_in_bullets = set()
    for exp in extraction.get("experience") or []:
        if not isinstance(exp, dict):
            continue
        
        # Collect all text from bullets
        bullets_text = " ".join(exp.get("bullets") or []).lower()
        
        # Check which tech skills actually appear in bullets
        for tech in exp.get("tech") or []:
            if isinstance(tech, str) and tech.strip():
                tech_lower = tech.lower()
                # Check if skill appears in bullets (as whole word or part of phrase)
                if tech_lower in bullets_text:
                    experience_skills_in_bullets.add(tech_lower)
    
    # Second pass: process all tech skills from experience
    for exp in extraction.get("experience") or []:
        if not isinstance(exp, dict):
            continue
            
        for tech in exp.get("tech") or []:
            if not isinstance(tech, str) or not tech.strip():
                continue
                
            name = _clean(tech)
            if not name:
                continue
            
            key = name.lower()
            
            # Determine source and weight based on whether skill appears in bullets
            if key in experience_skills_in_bullets:
                source = "work_experience"
                weight = 1.0
            else:
                source = "skills_list"
                weight = 0.4
            
            # Keep highest weight for each skill
            if key in seen:
                if weight > seen[key]["weight"]:
                    seen[key] = {
                        "name": name,
                        "source": source,
                        "weight": weight,
                        "category": None
                    }
            else:
                seen[key] = {
                    "name": name,
                    "source": source,
                    "weight": weight,
                    "category": None
                }
    
    # Third pass: handle extraction.skills (if provided by LLM with explicit source/weight)
    for s in extraction.get("skills") or []:
        if isinstance(s, dict):
            name = _clean(s.get("name"))
            if not name:
                continue
            
            source = s.get("source", "skills_list")
            weight = s.get("weight", 0.4)
            category = s.get("category")
            
            key = name.lower()
            if key in seen:
                if weight > seen[key]["weight"]:
                    seen[key] = {
                        "name": name,
                        "source": source,
                        "weight": weight,
                        "category": category
                    }
            else:
                seen[key] = {
                    "name": name,
                    "source": source,
                    "weight": weight,
                    "category": category
                }
        elif isinstance(s, str):
            # Legacy format: plain string (fallback to skills_list)
            name = _clean(s)
            if name:
                key = name.lower()
                if key not in seen:
                    seen[key] = {
                        "name": name,
                        "source": "skills_list",
                        "weight": 0.4,
                        "category": None
                    }
    
    # Return as list, preserving order
    return list(seen.values())


def _extract_experience(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for e in extraction.get("experience") or []:
        if not isinstance(e, dict):
            continue
        start = _clean(e.get("start_date"))
        end = _clean(e.get("end_date"))
        duration = _duration_years(start, end)

        items.append({
            "title": _clean(e.get("title")),
            "company": _clean(e.get("company")),
            "location": _clean(e.get("location")),
            "start_date": start,
            "end_date": end,
            "bullets": [b for b in (e.get("bullets") or []) if _clean(b)],
            "tech": [t for t in (e.get("tech") or []) if _clean(t)],
            "duration_years": duration,
        })
    return items


def _extract_education(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for ed in extraction.get("education") or []:
        if not isinstance(ed, dict):
            continue
        items.append({
            "degree": _clean(ed.get("degree")),
            "field": _clean(ed.get("field")),
            "institution": _clean(ed.get("institution")),
            "start_date": _clean(ed.get("start_date")),
            "end_date": _clean(ed.get("end_date")),
        })
    return items


def _extract_languages(extraction: dict[str, Any]) -> list[str]:
    person = extraction.get("person") or {}
    langs = person.get("languages") or []
    seen = set()
    uniq = []
    for l in langs:
        if not _clean(l):
            continue
        key = l.strip().lower()
        if key not in seen:
            seen.add(key)
            uniq.append(l.strip())
    return uniq


def _duration_years(start_raw: Optional[str], end_raw: Optional[str]) -> Optional[float]:
    s = _parse_date(start_raw)
    e = _parse_date(end_raw, default_now=True)
    if not (s and e and e >= s):
        return None
    days = (e - s).days
    return round(days / 365.0, 1) if days > 0 else None


def _resume_to_summary(resume: Resume) -> dict[str, Any]:
    extraction = resume.extraction_json or {}
    person = extraction.get("person") or {}
    experience = extraction.get("experience") or []

    # Prefer primary years if available
    primary_years = None
    exp_meta = extraction.get("experience_meta") or {}
    totals_by_category = exp_meta.get("totals_by_category") or {}
    rec_primary = exp_meta.get("recommended_primary_years") or {}
    if isinstance(rec_primary, dict):
        primary_years = rec_primary.get("tech")
    if primary_years is None and isinstance(totals_by_category, dict):
        primary_years = totals_by_category.get("tech")

    return {
        "id": resume.id,
        "name": _clean(person.get("name")) or _infer_name_from_path(resume.file_path),
        "profession": _extract_profession(experience),
        "years_of_experience": primary_years if primary_years is not None else _compute_years_of_experience(experience),
        "resume_url": f"/resumes/{resume.id}/file",
        # Carry along years_by_category for consumers that list summaries (optional)
        "years_by_category": totals_by_category or {},
    }


def _clean(value: Optional[str]) -> Optional[str]:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _infer_name_from_path(path_str: str) -> Optional[str]:
    try:
        filename = Path(path_str).stem
    except Exception:
        return None
    clean = filename.replace("_", " ").replace("-", " ").strip()
    return " ".join(word.capitalize() for word in clean.split()) if clean else None


def _extract_profession(experience: Any) -> Optional[str]:
    if not isinstance(experience, list):
        return None
    best_title, best_end = None, None
    for entry in experience:
        if not isinstance(entry, dict):
            continue
        title = _clean(entry.get("title"))
        if not title:
            continue
        end_dt = _parse_date(entry.get("end_date"), default_now=True)
        if best_end is None or end_dt > best_end:
            best_end, best_title = end_dt, title
    return best_title


def _compute_years_of_experience(experience: Any) -> Optional[float]:
    if not isinstance(experience, list):
        return None
    spans = []
    for e in experience:
        s, e_ = _parse_date(e.get("start_date")), _parse_date(e.get("end_date"), default_now=True)
        if s and e_ and e_ >= s:
            spans.append((s, e_))
    if not spans:
        return None
    spans.sort(key=lambda s: s[0])
    merged = []
    cur_s, cur_e = spans[0]
    for s, e_ in spans[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e_)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e_
    merged.append((cur_s, cur_e))
    total_days = sum((e - s).days for s, e in merged)
    return round(total_days / 365.0, 1) if total_days > 0 else None


def _parse_date(raw: Any, default_now: bool = False):
    """
    Parse multiple loose formats including month-name variants.
    If raw is falsy and default_now=True, return now.
    """
    from datetime import datetime
    if not raw:
        return datetime.utcnow() if default_now else None
    try:
        val = str(raw).strip().lower().replace("–", "-").replace("—", "-")
        if val in {"present", "current", "now"}:
            return datetime.utcnow()
        if "-" in val and val.count("-") == 1 and len(val) == 9 and val[:4].isdigit() and val[-4:].isdigit():
            val = val.split("-")[0]
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
    return datetime.utcnow() if default_now else None


def get_resume(db: Session, resume_id: UUID) -> Optional[Resume]:
    return resume_repo.get_resume(db, resume_id)


def run_full_ingestion(db: Session, path: Path) -> Resume:
    resume = ingest_file(db, path)
    resume = parse_and_extract(db, resume)
    resume = chunk_and_embed(db, resume)
    return resume
