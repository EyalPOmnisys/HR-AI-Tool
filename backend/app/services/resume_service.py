# Purpose: Ingest resumes from files, parse text, extract structured fields, chunk, and create embeddings.
from __future__ import annotations
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Iterable
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories import resume_repo
from app.models.resume import Resume, ResumeChunk

from app.services.embedding_service import get_embedding
from app.core.config import settings

# Hybrid extraction (deterministic + LLM boost)
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
