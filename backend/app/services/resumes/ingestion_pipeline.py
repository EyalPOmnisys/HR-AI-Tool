"""End-to-end resume ingestion pipeline: parsing, extraction, chunking, and embeddings."""
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


# ---------------------------------------------------------------------
# INGESTION & PIPELINE STEPS
# ---------------------------------------------------------------------

def ingest_file(db: Session, path: Path) -> Resume:
    """
    Register or retrieve an existing resume entry by content hash.
    This prevents duplicates even if filenames differ.
    """
    data = read_file_bytes(path)
    content_hash = sha256_of_bytes(data)

    existing = resume_repo.get_by_hash(db, content_hash)
    if existing:
        # If the file already exists, keep its original path for traceability.
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
    """
    Parse file → extract structured JSON (deterministic + optional LLM).
    We keep status transitions granular to help operational visibility.
    """
    try:
        resume_repo.set_status(db, resume, status="parsing")

        txt = parse_to_text(Path(resume.file_path))
        resume = resume_repo.attach_parsed_text(db, resume, parsed_text=txt or "")

        resume_repo.set_status(db, resume, status="extracting")
        resume = extract_structured(db, resume)

        resume_repo.set_status(db, resume, status="parsed")
        return resume

    except Exception as e:
        # Persist error inside DB record for UI observability
        resume_repo.set_status(db, resume, status="error", error=str(e))
        raise


def chunk_and_embed(db: Session, resume: Resume) -> Resume:
    """
    Split parsed text into chunks and compute embeddings for both
    the full text and each chunk. Errors on a single chunk do not
    abort the whole pipeline.
    """
    if not resume.parsed_text:
        # Nothing to chunk/embed if parsing failed or text is empty
        return resume

    chunks = chunk_resume_text(resume.parsed_text)
    chunks = resume_repo.bulk_add_chunks(db, resume, chunks)

    # Embed full resume text
    try:
        full_emb = default_embedding_client.embed(resume.parsed_text)
        resume_repo.attach_resume_embedding(db, resume, embedding=full_emb)
    except Exception as e:
        # Do not fail the pipeline for full embedding issues
        resume_repo.set_status(
            db,
            resume,
            status="parsed",
            error=f"full embedding failed: {e}",
        )

    # Embed each chunk
    resume_repo.set_status(db, resume, status="embedding")
    model = getattr(settings, "EMBEDDING_MODEL", None)
    version = getattr(settings, "ANALYSIS_VERSION", None)

    any_failure = False
    for ch in chunks:
        try:
            emb = default_embedding_client.embed(ch.text)
            resume_repo.upsert_chunk_embedding(
                db, ch, embedding=emb, model=model, version=version
            )
        except Exception as e:
            any_failure = True
            # Persist per-chunk error, but continue
            resume_repo.note_chunk_error(db, ch, error=str(e))

    resume_repo.set_status(db, resume, status=("ready" if not any_failure else "warning"))
    return resume


# ---------------------------------------------------------------------
# LISTING & DETAIL (API COMPATIBILITY)
# ---------------------------------------------------------------------

def list_resume_summaries(
    db: Session, *, offset: int = 0, limit: int = 20
) -> tuple[list[dict[str, Any]], int]:
    """Return summarized resume info for listing view."""
    rows, total = resume_repo.list_resumes(db, offset=offset, limit=limit)
    items = [_resume_to_summary(row) for row in rows]
    return items, total


def get_resume_detail(db: Session, resume_id: UUID) -> Optional[dict[str, Any]]:
    """Return full detail view of a single resume with extracted fields."""
    resume = resume_repo.get_resume(db, resume_id)
    if not resume:
        return None

    extraction = resume.extraction_json or {}
    person = extraction.get("person") or {}

    # ---- Contacts (נחזיר רק אימייל/טלפון; הפרונט גם ככה מסנן) ----
    contacts = _extract_contacts(person)

    # ---- Skills ----
    skills = _extract_skills(extraction)

    # ---- Experience ----
    experience_entries = _extract_experience(extraction)

    # ---- Education ----
    education_entries = _extract_education(extraction)

    # ---- Languages ----
    languages = _extract_languages(extraction)

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
        "summary": None,  # אפשר להוסיף סיכום בעתיד אם תרצה
        "contacts": contacts,
        "skills": skills,
        "experience": experience_entries,
        "education": education_entries,
        "languages": languages,
        "created_at": resume.created_at,
        "updated_at": resume.updated_at,
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
    # אם תרצה, אפשר להוסיף כאן גם קישורים/פרופילים, אבל לפי הבקשה אתה מציג רק אימייל/טלפון
    return out


def _extract_skills(extraction: dict[str, Any]) -> list[str]:
    names = []
    for s in extraction.get("skills") or []:
        name = _clean((s or {}).get("name"))
        if name:
            names.append(name)
    # ייחוד + שמירה על סדר הופעה
    seen = set()
    uniq = []
    for n in names:
        key = n.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(n)
    return uniq


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
    # ייחוד + ניקוי
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


# ---------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------

def _resume_to_summary(resume: Resume) -> dict[str, Any]:
    extraction = resume.extraction_json or {}
    person = extraction.get("person") or {}
    experience = extraction.get("experience") or []

    return {
        "id": resume.id,
        "name": _clean(person.get("name")) or _infer_name_from_path(resume.file_path),
        "profession": _extract_profession(experience),
        "years_of_experience": _compute_years_of_experience(experience),
        "resume_url": f"/resumes/{resume.id}/file",
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
    """
    Heuristic: the most recent role title is a good proxy for profession.
    If end_date is None or 'present', we treat it as ongoing.
    """
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
    """
    Merge overlapping spans and sum total days; return years to 1 decimal.
    """
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
    Robust parse for variants like:
    - '2024', '2024-05', '05/2024'
    - '2024–present', '2021-2022' (we only parse single endpoint here)
    - 'present'/'current'/'now'
    Returns a naive UTC datetime (YYYY-01-01 if only year).
    """
    from datetime import datetime
    if not raw:
        return datetime.utcnow() if default_now else None
    try:
        val = str(raw).strip().lower().replace("–", "-").replace("—", "-")
        if val in {"present", "current", "now"}:
            return datetime.utcnow()
        # Keep only the first endpoint if a range is mistakenly provided
        if "-" in val and val.count("-") == 1 and len(val) == 9 and val[:4].isdigit() and val[-4:].isdigit():
            val = val.split("-")[0]  # e.g., "2021-2022" -> "2021"

        # Try multiple formats
        fmts = ("%Y-%m-%d", "%Y-%m", "%m/%Y", "%Y/%m", "%Y")
        for fmt in fmts:
            try:
                dt = datetime.strptime(val, fmt)
                # Normalize to month/day if absent
                if fmt == "%Y":
                    dt = dt.replace(month=1, day=1)
                elif fmt in {"%Y-%m", "%m/%Y", "%Y/%m"}:
                    dt = dt.replace(day=1)
                return dt
            except ValueError:
                continue
    except Exception:
        pass
    return datetime.utcnow() if default_now else None


def get_resume(db: Session, resume_id: UUID) -> Optional[Resume]:
    """Fetch a Resume by its ID."""
    return resume_repo.get_resume(db, resume_id)


# ---------------------------------------------------------------------
# FULL PIPELINE EXECUTION
# ---------------------------------------------------------------------

def run_full_ingestion(db: Session, path: Path) -> Resume:
    """
    Run the full ingestion pipeline:
      1. Register or retrieve the file
      2. Parse and extract structured information
      3. Chunk and embed the text
      4. Return the final Resume object

    This is the main entry point for automated ingestion flows
    such as the resume watcher.
    """
    resume = ingest_file(db, path)
    resume = parse_and_extract(db, resume)
    resume = chunk_and_embed(db, resume)
    return resume
