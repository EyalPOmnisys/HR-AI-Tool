"""Utilities for reading, parsing, and chunking resume text."""
from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path
from typing import List

from app.models.resume import ResumeChunk


# --- File I/O ---

def sha256_of_bytes(data: bytes) -> str:
    """Return SHA256 hash of bytes."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def detect_mime(path: Path) -> str:
    """Guess MIME type from extension."""
    guess, _ = mimetypes.guess_type(str(path))
    return guess or "application/octet-stream"


def read_file_bytes(path: Path) -> bytes:
    """Read file content as bytes."""
    return path.read_bytes()


# --- Parsing ---

def parse_to_text(path: Path) -> str:
    """
    Convert resume file (PDF/DOCX/TXT) to plain text.
    The PDF path uses pdfplumber for robust text layout extraction.
    """
    mime = detect_mime(path)
    lower = path.suffix.lower()

    if lower == ".pdf" or mime == "application/pdf":
        import pdfplumber
        parts: List[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                # extract_text() provides line-aware extraction and is usually more reliable than raw OCR for digital PDFs
                text = page.extract_text() or ""
                parts.append(text)
        return "\n".join(parts).strip()

    if lower == ".docx" or mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        from docx import Document
        doc = Document(str(path))
        # Preserve paragraph boundaries
        return "\n".join(p.text for p in doc.paragraphs).strip()

    # Plain-text fallback
    return path.read_text(encoding="utf-8", errors="ignore").strip()


# --- Chunking ---

_SECTION_HEADINGS = (
    "experience|education|skills|projects|summary|languages|certifications|achievements|"
    "ניסיון|השכלה|מיומנויות|פרויקטים|סיכום|שפות|הסמכות"
)

def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """
    Split text based on common section headings (English + Hebrew).
    We keep headings-only lines as boundaries to improve chunk topicality.
    """
    pattern = re.compile(rf"^\s*({_SECTION_HEADINGS})\s*[:\-]?\s*$", re.I)
    sections, buffer = [], []
    current_section = "general"

    for line in text.splitlines():
        if pattern.match(line.strip()):
            if buffer:
                sections.append((current_section, "\n".join(buffer).strip()))
                buffer.clear()
            current_section = pattern.match(line.strip()).group(1).lower()
        else:
            buffer.append(line)
    if buffer:
        sections.append((current_section, "\n".join(buffer).strip()))
    return [(sec, t) for sec, t in sections if t]


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Zא-ת0-9])")

def _chunk_long_text_sentence_aware(txt: str, max_chars: int = 1200, overlap: int = 160) -> list[str]:
    """
    Split long text into overlapping windows, attempting to break on sentence
    boundaries to keep chunks semantically coherent.
    """
    if len(txt) <= max_chars:
        return [txt]

    sentences = _SENT_SPLIT.split(txt)
    chunks: list[str] = []
    cur = ""
    for sent in sentences:
        if not cur:
            cur = sent
            continue
        # If adding the next sentence would exceed max, flush current
        if len(cur) + 1 + len(sent) > max_chars:
            chunks.append(cur.strip())
            # Start next chunk with an overlap from the end of the previous chunk
            if overlap > 0 and len(cur) > overlap:
                cur = cur[-overlap:] + " " + sent
            else:
                cur = sent
        else:
            cur = cur + " " + sent
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def chunk_resume_text(parsed_text: str) -> list[ResumeChunk]:
    """
    Generate ResumeChunk objects for each text segment. We first split by
    headings; within each section we generate sentence-aware windows.
    """
    chunks: list[ResumeChunk] = []
    order = 0
    for section, sec_text in _split_by_headings(parsed_text):
        for piece in _chunk_long_text_sentence_aware(sec_text):
            if piece.strip():
                chunks.append(ResumeChunk(section=section, ord=order, text=piece.strip()))
                order += 1

    # Fallback: if no headings found at all, chunk entire text
    if not chunks:
        for piece in _chunk_long_text_sentence_aware(parsed_text):
            if piece.strip():
                chunks.append(ResumeChunk(section=None, ord=len(chunks), text=piece.strip()))
    return chunks
