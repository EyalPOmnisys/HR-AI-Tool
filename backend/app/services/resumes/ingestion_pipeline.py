"""End-to-end resume ingestion handling parsing, extraction, chunking, embedding, and API response formatting from upload to searchable data."""
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
        
        # --- DEBUG PRINT ---
        print(f"--- DEBUG: Extracted text for {resume.file_path} ---")
        print((txt or "")[:500])
        print("---------------------------------------------------")
        # -------------------

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
    model = default_embedding_client.model
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
        "profession": _extract_profession(
            extraction.get("experience") or [],
            extraction.get("education"),
            person
        ),
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
    
    Simplified logic (binary weighting):
    1. If skill appears in work experience bullets -> source: work_experience, weight: 1.0
    2. Otherwise -> general skill -> retain original source (if any) and assign weight: 0.6

    Keeps only the highest-weighted occurrence (experience overrides general).
    """
    from app.services.common.skills_normalizer import normalize_skill
    
    seen = {}  # skill_name.lower() -> {name, source, weight, category}
    
    # First pass: collect all text from experience bullets and build searchable corpus
    all_bullets_text = ""
    for exp in extraction.get("experience") or []:
        if not isinstance(exp, dict):
            continue
        bullets = exp.get("bullets") or []
        all_bullets_text += " " + " ".join(bullets)
    
    all_bullets_text_lower = all_bullets_text.lower()
    
    # Helper function to check if a skill appears in work experience
    def skill_in_work_experience(skill_name: str) -> bool:
        """Check if skill name appears in bullets (case-insensitive, flexible matching)"""
        if not skill_name or not all_bullets_text_lower:
            return False
        
        skill_lower = skill_name.lower().strip()
        # Also check normalized version for better matching (e.g., "Node.js" vs "nodejs")
        skill_normalized = normalize_skill(skill_name).lower()
        
        # Check both original and normalized forms
        return skill_lower in all_bullets_text_lower or skill_normalized in all_bullets_text_lower
    
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
            if skill_in_work_experience(name):
                source = "work_experience"
                weight = 1.0
            else:
                source = "skills_list"
                weight = 0.6
            
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
    
    # Third pass: handle extraction.skills (if provided by LLM or deterministic extraction)
    # Check each skill against bullets to determine if it's from work experience
    for s in extraction.get("skills") or []:
        if isinstance(s, dict):
            name = _clean(s.get("name"))
            if not name:
                continue
            
            # Check if this skill appears in work experience bullets
            appears_in_work = skill_in_work_experience(name)
            
            # Determine source and weight
            if appears_in_work:
                source = "work_experience"
                weight = 1.0
            else:
                source = s.get("source", "skills_list")
                if source == "experience":
                    source = "work_experience"
                # Force binary weighting
                weight = 0.6
            
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
            # Legacy format: plain string - check if it appears in work experience
            name = _clean(s)
            if name:
                key = name.lower()
                
                # Check if skill appears in work experience
                if skill_in_work_experience(name):
                    source = "work_experience"
                    weight = 1.0
                else:
                    source = "skills_list"
                    weight = 0.6
                
                if key not in seen:
                    seen[key] = {
                        "name": name,
                        "source": source,
                        "weight": weight,
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
    education = extraction.get("education") or []

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
        "profession": _extract_profession(experience, education, person),
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


def _extract_profession(experience: Any, education: Any = None, person: Any = None) -> Optional[str]:
    """
    Extract candidate's current/most relevant title.
    
    Priority: 
    1. Self-declared title (from summary/header)
    2. Most recent role with explicit title from real work experience
    3. If no work experience, infer from education field
    4. Last resort: most recent title from any entry
    """
    # Check self-declared title first
    if isinstance(person, dict):
        self_title = _clean(person.get("self_declared_title"))
        if self_title:
            return self_title

    if not isinstance(experience, list):
        experience = []
    
    # Helper to check if role is real work experience (not project/volunteer)
    def _is_real_work(entry: dict) -> bool:
        company = _clean(entry.get("company", ""))
        title = _clean(entry.get("title", ""))
        
        if not company:
            return False
        
        company_lower = company.lower()
        title_lower = title.lower() if title else ""
        
        # Exclude projects and volunteer work
        if any(keyword in company_lower for keyword in ["project", "personal", "volunteer", "פרויקט"]):
            return False
        if any(keyword in title_lower for keyword in ["project", "personal", "volunteer", "פרויקט"]):
            return False
        
        return True
    
    # Find most recent title from real work
    best_title, best_end = None, None
    best_real_work_title, best_real_work_end = None, None
    
    for entry in experience:
        if not isinstance(entry, dict):
            continue
        
        title = _clean(entry.get("title"))
        if not title:
            continue
        
        end_dt = _parse_date(entry.get("end_date"), default_now=True)
        
        # Track most recent title (any experience)
        if best_end is None or end_dt > best_end:
            best_end, best_title = end_dt, title
        
        # Track most recent REAL WORK title
        if _is_real_work(entry):
            if best_real_work_end is None or end_dt > best_real_work_end:
                best_real_work_end, best_real_work_title = end_dt, title
    
    # Check Education status
    is_student = False
    student_title = None
    if isinstance(education, list) and education:
        for edu in education:
            if not isinstance(edu, dict):
                continue
            end_dt = _parse_date(edu.get("end_date"), default_now=True)
            # If education ends in future or is very recent (last 6 months)
            # Note: _parse_date returns UTC now for 'present', so we check if it's close to now
            if end_dt:
                # If end_date is effectively "now" or future
                if end_dt >= datetime.utcnow() or (datetime.utcnow() - end_dt).days < 180:
                    is_student = True
                    field = _clean(edu.get("field", ""))
                    degree = _clean(edu.get("degree", ""))
                    
                    # Construct a nice student title
                    if field:
                        # Clean up field
                        field = field.replace("Bachelor of Science in", "").replace("B.Sc", "").strip()
                        student_title = f"{field} Student"
                    elif degree:
                        student_title = f"{degree} Student"
                    else:
                        student_title = "Student"
                    break # Found current education

    # Decision Logic
    
    # If we have a real work title
    if best_real_work_title:
        # If currently a student, and real work ended > 1 year ago, prefer Student
        # This handles cases like "Former Military Technician, now CS Student"
        if is_student and best_real_work_end:
             days_since_work = (datetime.utcnow() - best_real_work_end).days
             if days_since_work > 365:
                 return student_title
        
        return best_real_work_title
    
    # If no real work title, but we have a general title (e.g. from projects)
    if best_title:
        # If currently a student, prefer Student over "Project" title
        if is_student:
             return student_title
        return best_title
    
    # Fallback: infer from education if we haven't found a title yet
    if student_title:
        return student_title
        
    if isinstance(education, list) and education:
        for edu in education:
            if not isinstance(edu, dict):
                continue
            field = _clean(edu.get("field", ""))
            if field:
                field_lower = field.lower()
                if "computer" in field_lower or "software" in field_lower or "מחשב" in field_lower:
                    return "Software Developer"
                elif "data" in field_lower and "science" in field_lower:
                    return "Data Scientist"
                elif "engineer" in field_lower:
                    return "Engineer"
                else:
                    return field
    
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


def delete_resume(db: Session, resume_id: UUID) -> bool:
    return resume_repo.delete_resume(db, resume_id)
