# Purpose: Ingest resumes from files, parse text, extract structured fields, chunk, and create embeddings.
from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resume import Resume, ResumeChunk
from app.repositories import resume_repo
from app.services.embedding_service import get_embedding
from app.services.extraction.deterministic import extract_deterministic
from app.services.extraction.llm_boost import llm_enhance


# --- Utils ---

def sha256_of_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def detect_mime(path: Path) -> str:
    guess, _ = mimetypes.guess_type(str(path))
    return guess or "application/octet-stream"


def read_file_bytes(path: Path) -> bytes:
    return path.read_bytes()


# --- Parsing (PDF/DOCX/TXT) ---

def parse_to_text(path: Path) -> str:
    mime = detect_mime(path)
    lower = path.suffix.lower()

    if lower == ".pdf" or mime == "application/pdf":
        # lightweight PDF text extraction
        import pdfplumber
        text_parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                pg_text = page.extract_text() or ""
                text_parts.append(pg_text)
        return "\n".join(text_parts).strip()

    if lower in (".docx",) or mime in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",):
        from docx import Document
        doc = Document(str(path))
        paras = [p.text for p in doc.paragraphs]
        return "\n".join(paras).strip()

    # Fallback: text file or unknown
    return path.read_text(encoding="utf-8", errors="ignore").strip()


# --- Chunking (simple and robust for MVP) ---

def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """
    Heuristic: split on common headings; return list of (section, text)
    """
    import re
    sections = []
    current_section = "general"
    buffer: list[str] = []

    pattern = re.compile(
        r"^\s*(experience|education|skills|projects|summary|languages|certifications|achievements)\s*[:\-]?\s*$",
        re.I,
    )

    for line in text.splitlines():
        if pattern.match(line.strip()):
            if buffer:
                sections.append((current_section, "\n".join(buffer).strip()))
                buffer = []
            current_section = pattern.match(line.strip()).group(1).lower()
        else:
            buffer.append(line)
    if buffer:
        sections.append((current_section, "\n".join(buffer).strip()))
    return [(sec, t) for sec, t in sections if t]


def _chunk_long_text(txt: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    """
    Simple char-based windowing with overlap.
    """
    if len(txt) <= max_chars:
        return [txt]
    chunks = []
    start = 0
    n = len(txt)
    while start < n:
        end = min(n, start + max_chars)
        chunks.append(txt[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def chunk_resume_text(parsed_text: str) -> list[ResumeChunk]:
    # section-aware chunking, then windowing per section
    chunks: list[ResumeChunk] = []
    ord_counter = 0
    for section, sec_text in _split_by_headings(parsed_text):
        for piece in _chunk_long_text(sec_text):
            if not piece.strip():
                continue
            chunk = ResumeChunk(section=section, ord=ord_counter, language=None, text=piece.strip())
            chunks.append(chunk)
            ord_counter += 1
    # if no headings detected, fall back to windowing entire text
    if not chunks:
        for piece in _chunk_long_text(parsed_text):
            if piece.strip():
                chunks.append(ResumeChunk(section=None, ord=len(chunks), language=None, text=piece.strip()))
    return chunks


# --- Public API ---

def ingest_file(db: Session, path: Path) -> Resume:
    data = read_file_bytes(path)
    content_hash = sha256_of_bytes(data)
    existing = resume_repo.get_by_hash(db, content_hash)
    if existing:
        return existing  # idempotent

    mime = detect_mime(path)
    file_size = len(data)
    resume = resume_repo.create_resume(
        db,
        file_path=str(path),
        content_hash=content_hash,
        mime_type=mime,
        file_size=file_size,
    )
    return resume


def _extract_structured(db: Session, resume: Resume) -> Resume:
    """
    Build extraction_json using deterministic extractor with optional LLM enhancement.
    """
    if not resume.parsed_text:
        return resume

    base = extract_deterministic(resume.parsed_text)
    enriched = llm_enhance(resume.parsed_text, base)
    enriched.setdefault("meta", {})["extraction_version"] = getattr(settings, "EXTRACTION_VERSION", 1)
    resume_repo.attach_extraction(db, resume, extraction_json=enriched)
    return resume


def parse_and_store(db: Session, resume: Resume) -> Resume:
    try:
        resume_repo.set_status(db, resume, status="parsing")
        txt = parse_to_text(Path(resume.file_path))
        resume = resume_repo.attach_parsed_text(db, resume, parsed_text=txt)

        # Structured extraction (deterministic + LLM boost on-demand)
        resume = _extract_structured(db, resume)

        resume_repo.set_status(db, resume, status="parsed")
        return resume
    except Exception as e:
        resume_repo.set_status(db, resume, status="error", error=str(e))
        raise


def chunk_and_embed(db: Session, resume: Resume) -> Resume:
    if not resume.parsed_text:
        return resume

    # chunk
    chunks = chunk_resume_text(resume.parsed_text)
    chunks = resume_repo.bulk_add_chunks(db, resume, chunks)

    # optional: embedding for full text (useful for general similarity)
    try:
        full_emb = get_embedding(resume.parsed_text)
        resume = resume_repo.attach_resume_embedding(db, resume, embedding=full_emb)
    except Exception as e:
        # do not fail the pipeline; just record the error
        resume_repo.set_status(db, resume, status="parsed", error=f"full embedding failed: {e}")

    # embeddings per chunk
    resume_repo.set_status(db, resume, status="embedding")
    for ch in chunks:
        try:
            emb = get_embedding(ch.text)
            model = getattr(settings, "EMBEDDING_MODEL", None)
            version = getattr(settings, "ANALYSIS_VERSION", None)
            resume_repo.upsert_chunk_embedding(db, ch, embedding=emb, model=model, version=version)
        except Exception as e:
            resume_repo.set_status(db, resume, status="error", error=f"chunk {ch.ord} embedding failed: {e}")
            raise
    resume_repo.set_status(db, resume, status="ready")
    return resume


def get_resume(db: Session, resume_id: UUID) -> Optional[Resume]:
    return resume_repo.get_resume(db, resume_id)


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
    experience_entries = extraction.get("experience") or []
    education_entries = extraction.get("education") or []

    detail = {
        "id": resume.id,
        "name": _clean_string(person.get("name")) or _infer_name_from_path(resume.file_path),
        "profession": _extract_profession(experience_entries),
        "years_of_experience": _compute_years_of_experience(experience_entries),
        "resume_url": f"/resumes/{resume.id}/file",
        "status": resume.status,
        "file_name": Path(resume.file_path).name if resume.file_path else None,
        "mime_type": resume.mime_type,
        "file_size": resume.file_size,
        "summary": _extract_summary_text(resume.parsed_text),
        "contacts": _extract_contact_items(person),
        "skills": _extract_skill_names(extraction.get("skills") or []),
        "experience": [
            _format_experience_item(entry) for entry in experience_entries if isinstance(entry, dict)
        ],
        "education": [
            _format_education_item(entry) for entry in education_entries if isinstance(entry, dict)
        ],
        "languages": _extract_languages(person),
        "created_at": resume.created_at,
        "updated_at": resume.updated_at,
    }
    return detail


def _resume_to_summary(resume: Resume) -> dict[str, Any]:
    extraction = resume.extraction_json or {}
    person = extraction.get("person") or {}
    experience = extraction.get("experience") or []

    name = _clean_string(person.get("name"))
    if not name:
        name = _infer_name_from_path(resume.file_path)

    summary = {
        "id": resume.id,
        "name": name,
        "profession": _extract_profession(experience),
        "years_of_experience": _compute_years_of_experience(experience),
        "resume_url": f"/resumes/{resume.id}/file",
    }
    return summary


def _clean_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _infer_name_from_path(path_str: str) -> Optional[str]:
    try:
        filename = Path(path_str).stem
    except Exception:
        return None
    clean = filename.replace("_", " ").replace("-", " ").strip()
    if not clean:
        return None
    # Preserve capitalization heuristically
    return " ".join(word.capitalize() for word in clean.split())


def _extract_profession(experience: Any) -> Optional[str]:
    if not isinstance(experience, list):
        return None

    best_title = None
    best_end = None
    now = datetime.utcnow()

    for entry in experience:
        if not isinstance(entry, dict):
            continue
        title = _clean_string(entry.get("title"))
        if not title:
            continue

        end_raw = entry.get("end_date")
        end_dt = _parse_date(end_raw, default_now=True)
        if end_dt is None:
            end_dt = now

        if best_end is None or end_dt > best_end:
            best_end = end_dt
            best_title = title

    return best_title


def _extract_client_link(person: Any) -> Optional[str]:
    if not isinstance(person, dict):
        return None

    profiles = person.get("profiles") or []
    if isinstance(profiles, list):
        # Prefer LinkedIn-style profiles
        for entry in profiles:
            if not isinstance(entry, dict):
                continue
            link = _clean_string(entry.get("value"))
            if not link:
                continue
            type_hint = (entry.get("type") or "").lower()
            if "linkedin" in type_hint:
                return link
        for entry in profiles:
            if not isinstance(entry, dict):
                continue
            link = _clean_string(entry.get("value"))
            if link:
                return link

    links = person.get("links") or []
    if isinstance(links, list):
        for entry in links:
            if not isinstance(entry, dict):
                continue
            link = _clean_string(entry.get("value"))
            if link:
                return link

    direct_link = person.get("client_link")
    return _clean_string(direct_link)


def _compute_years_of_experience(experience: Any) -> Optional[float]:
    if not isinstance(experience, list):
        return None

    spans: list[tuple[datetime, datetime]] = []
    for entry in experience:
        if not isinstance(entry, dict):
            continue

        start_dt = _parse_date(entry.get("start_date"))
        end_dt = _parse_date(entry.get("end_date"), default_now=True)

        if not start_dt:
            continue
        if not end_dt or end_dt < start_dt:
            end_dt = datetime.utcnow()

        spans.append((start_dt, end_dt))

    if not spans:
        return None

    spans.sort(key=lambda span: span[0])
    merged: list[tuple[datetime, datetime]] = []
    cur_start, cur_end = spans[0]
    for start, end in spans[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    total_days = sum((end - start).days for start, end in merged)
    if total_days <= 0:
        return None

    years = total_days / 365.0
    return round(years, 1)


def _parse_date(raw: Any, default_now: bool = False) -> Optional[datetime]:
    if raw is None:
        return datetime.utcnow() if default_now else None

    if isinstance(raw, datetime):
        return raw

    if isinstance(raw, (int, float)):
        try:
            return datetime(int(raw), 1, 1)
        except Exception:
            return datetime.utcnow() if default_now else None

    if not isinstance(raw, str):
        return datetime.utcnow() if default_now else None

    value = raw.strip()
    if not value:
        return datetime.utcnow() if default_now else None

    lowered = value.lower()
    if lowered in {"present", "current", "ongoing", "now", "today"}:
        return datetime.utcnow()

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y-%m",
        "%Y/%m",
        "%m/%Y",
        "%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            if fmt == "%Y":
                dt = dt.replace(month=1, day=1)
            return dt
        except ValueError:
            continue

    return datetime.utcnow() if default_now else None


def _extract_summary_text(parsed_text: Optional[str]) -> Optional[str]:
    if not parsed_text:
        return None

    try:
        sections = _split_by_headings(parsed_text)
        for section, sec_text in sections:
            if not sec_text:
                continue
            if section and section.lower() in {"summary", "professional summary"}:
                cleaned = sec_text.strip()
                if cleaned:
                    return cleaned
        if sections:
            first_section = sections[0][1].strip()
            if first_section:
                return first_section
    except Exception:
        pass

    first_paragraph = parsed_text.strip().split("\n\n", 1)[0].strip()
    return first_paragraph or None


def _extract_contact_items(person: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: Optional[str], label: Optional[str] = None) -> None:
        if not value:
            return
        normalized = value.strip()
        if not normalized:
            return
        key = (kind, normalized.lower())
        if key in seen:
            return
        seen.add(key)
        items.append({"type": kind, "label": label, "value": normalized})

    if isinstance(person, dict):
        emails = person.get("emails")
        if isinstance(emails, list):
            for entry in emails:
                if isinstance(entry, dict):
                    add("email", entry.get("value"))

        phones = person.get("phones")
        if isinstance(phones, list):
            for entry in phones:
                if not isinstance(entry, dict):
                    continue
                value = entry.get("value")
                if not value:
                    continue
                digits = [ch for ch in value if ch.isdigit()]
                if len(digits) < 9:
                    continue
                add("phone", value)

        profiles = person.get("profiles")
        if isinstance(profiles, list):
            for entry in profiles:
                if isinstance(entry, dict):
                    label = entry.get("type")
                    add("profile", entry.get("value"), label=label)

        links = person.get("links")
        if isinstance(links, list):
            for entry in links:
                if isinstance(entry, dict):
                    add("link", entry.get("value"))

    direct = _extract_client_link(person)
    add("profile", direct)

    return items


def _extract_skill_names(skills: Any) -> list[str]:
    if not isinstance(skills, list):
        return []
    names: list[str] = []
    seen: set[str] = set()
    for entry in skills:
        if not isinstance(entry, dict):
            continue
        name = _clean_string(entry.get("name"))
        if not name:
            continue
        normalized = name.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        names.append(name)
    return names


def _format_experience_item(entry: dict[str, Any]) -> dict[str, Any]:
    start_raw = entry.get("start_date")
    end_raw = entry.get("end_date")
    start_dt = _parse_date(start_raw) if start_raw else None
    end_dt = _parse_date(end_raw, default_now=True) if end_raw else None

    duration_years: Optional[float] = None
    if start_dt and end_dt and end_dt >= start_dt:
        duration_years = round((end_dt - start_dt).days / 365.0, 1)

    bullets = entry.get("bullets") if isinstance(entry.get("bullets"), list) else []
    tech = entry.get("tech") if isinstance(entry.get("tech"), list) else []

    return {
        "title": _clean_string(entry.get("title")),
        "company": _clean_string(entry.get("company")),
        "location": _clean_string(entry.get("location")),
        "start_date": _clean_string(start_raw) if isinstance(start_raw, str) else start_raw,
        "end_date": _clean_string(end_raw) if isinstance(end_raw, str) else end_raw,
        "bullets": [
            bullet.strip() for bullet in bullets if isinstance(bullet, str) and bullet.strip()
        ],
        "tech": [item.strip() for item in tech if isinstance(item, str) and item.strip()],
        "duration_years": duration_years,
    }


def _format_education_item(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "degree": _clean_string(entry.get("degree")),
        "field": _clean_string(entry.get("field")),
        "institution": _clean_string(entry.get("institution")),
        "start_date": _clean_string(entry.get("start_date"))
        if isinstance(entry.get("start_date"), str)
        else entry.get("start_date"),
        "end_date": _clean_string(entry.get("end_date"))
        if isinstance(entry.get("end_date"), str)
        else entry.get("end_date"),
    }


def _extract_languages(person: Any) -> list[str]:
    if not isinstance(person, dict):
        return []
    languages = person.get("languages")
    if not isinstance(languages, list):
        return []
    cleaned = [_clean_string(lang) for lang in languages if isinstance(lang, str)]
    return [lang for lang in cleaned if lang]
