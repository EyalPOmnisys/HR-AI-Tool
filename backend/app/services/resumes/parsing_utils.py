# app/services/resumes/parsing_utils.py
"""Utilities for reading, parsing, and chunking resume text (English + Hebrew RTL support)."""
from __future__ import annotations

import hashlib
import io
import mimetypes
import re
from pathlib import Path
from typing import List

from app.models.resume import ResumeChunk


# --- RTL Detection and Correction ---

def _is_hebrew_char(char: str) -> bool:
    """Check if a character is Hebrew."""
    return '\u0590' <= char <= '\u05FF'


def _has_significant_hebrew(text: str) -> bool:
    """Check if text contains significant Hebrew content (>30% Hebrew chars)."""
    if not text:
        return False
    hebrew_count = sum(1 for c in text if _is_hebrew_char(c))
    total_letters = sum(1 for c in text if c.isalpha())
    return total_letters > 0 and (hebrew_count / total_letters) > 0.3


def _reverse_rtl_line(line: str) -> str:
    """
    Reverse RTL (Right-to-Left) text that was extracted in wrong direction.
    python-docx extracts Hebrew with characters in correct order but words reversed.
    Example: "יתור ץיבוקשומ" should become "מושקוביץ רותי"
    """
    if not line or not _has_significant_hebrew(line):
        return line
    
    # Split into tokens preserving Hebrew words, English words, numbers, and punctuation
    # Hebrew characters are already in correct order within words, we just need to reverse word order
    tokens = re.findall(r'[\u0590-\u05FF]+|[a-zA-Z]+|\d+|[^\w\s]+|\s+', line)
    
    # Reverse only the order of tokens (words), not the characters within Hebrew words
    reversed_tokens = tokens[::-1]
    
    return ''.join(reversed_tokens)


def _fix_rtl_text(text: str) -> str:
    """
    Fix RTL text that was extracted in reversed order.
    Works line by line to preserve document structure.
    """
    if not text or not _has_significant_hebrew(text):
        return text
    
    lines = text.split('\n')
    fixed_lines = [_reverse_rtl_line(line) for line in lines]
    return '\n'.join(fixed_lines)


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

def _reconstruct_text_from_words(pdf_page) -> str:
    """
    Fallback: reconstruct a page's text from words when extract_text() is empty.
    Groups words by their top (y) position and sorts by x to form lines.
    """
    words = pdf_page.extract_words() or []
    if not words:
        return ""
    # Group by y position (rounded to avoid micro-variations)
    rows = {}
    for w in words:
        y = int(round(w.get("top", 0)))
        rows.setdefault(y, []).append(w)
    lines = []
    for y in sorted(rows.keys()):
        parts = sorted(rows[y], key=lambda w: w.get("x0", 0))
        line = " ".join(p.get("text", "") for p in parts if p.get("text"))
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines)


def parse_to_text(path: Path) -> str:
    """
    Convert resume file (PDF/DOCX/TXT) to plain text.
    - For PDFs, prefer pdfplumber.extract_text() (line-aware); if empty,
      fall back to reconstructing from words to reduce column/bullet fragmentation.
    - For DOCX, use unstructured library for better extraction (tables, headers, footers)
      with fallback to python-docx.
    - Automatically fixes RTL (Hebrew) text that was extracted in reversed order.
    """
    mime = detect_mime(path)
    lower = path.suffix.lower()

    if lower == ".pdf" or mime == "application/pdf":
        import pdfplumber
        parts: List[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if not text.strip():
                    # Fallback reconstruction for scanned or tricky layout pages
                    text = _reconstruct_text_from_words(page) or ""
                # Fix RTL text if needed
                text = _fix_rtl_text(text)
                parts.append(text)
        return "\n".join(parts).strip()

    if lower == ".docx" or mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        file_content = read_file_bytes(path)
        # RTL fix is already applied inside _parse_docx_advanced
        text = _parse_docx_advanced(file_content)
        return text

    # Plain-text fallback
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return _fix_rtl_text(text)


def _parse_docx_advanced(file_content: bytes) -> str:
    """
    Parse DOCX with enhanced Hebrew RTL support.
    Uses python-docx as primary parser with table extraction.
    Applies RTL fix immediately since python-docx extracts Hebrew text reversed.
    """
    try:
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        
        doc = Document(io.BytesIO(file_content))
        parts = []
        
        # Process document body in order (paragraphs and tables)
        for element in doc.element.body:
            # Check if it's a paragraph
            if element.tag.endswith('}p'):
                para = None
                for p in doc.paragraphs:
                    if p._element == element:
                        para = p
                        break
                if para and para.text.strip():
                    # Fix RTL immediately for each paragraph
                    fixed_text = _fix_rtl_text(para.text.strip())
                    parts.append(fixed_text)
            
            # Check if it's a table
            elif element.tag.endswith('}tbl'):
                table = None
                for t in doc.tables:
                    if t._element == element:
                        table = t
                        break
                if table:
                    # Extract table with better formatting
                    table_text = _extract_table_text(table)
                    if table_text:
                        # Fix RTL for table text too
                        fixed_table = _fix_rtl_text(table_text)
                        parts.append(fixed_table)
        
        # If no structured extraction worked, fallback to simple paragraphs
        if not parts:
            return _parse_docx_fallback(file_content)
        
        return "\n\n".join(parts)
    
    except Exception as e:
        print(f"Advanced DOCX parsing failed: {e}")
        return _parse_docx_fallback(file_content)


def _extract_table_text(table) -> str:
    """
    Extract text from DOCX table with proper structure preservation.
    Handles multi-column layouts common in resumes.
    """
    lines = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            cell_text = cell.text.strip()
            if cell_text:
                cells.append(cell_text)
        
        if cells:
            # Join cells with separator
            # If it's a single cell, just add it
            if len(cells) == 1:
                lines.append(cells[0])
            else:
                # Multiple cells - likely structured data
                lines.append(" | ".join(cells))
    
    return "\n".join(lines)


def _parse_docx_fallback(file_content: bytes) -> str:
    """
    Fallback DOCX parser using python-docx.
    Extracts paragraphs and tables with RTL fix.
    """
    from docx import Document
    
    doc = Document(io.BytesIO(file_content))
    parts = []
    
    # Extract paragraphs with RTL fix
    for para in doc.paragraphs:
        if para.text.strip():
            fixed_text = _fix_rtl_text(para.text)
            parts.append(fixed_text)
    
    # Extract tables with RTL fix
    for table in doc.tables:
        for row in table.rows:
            row_cells = [_fix_rtl_text(cell.text.strip()) for cell in row.cells if cell.text.strip()]
            if row_cells:
                parts.append(" | ".join(row_cells))
    
    return "\n".join(parts).strip()


# --- Chunking ---

_SECTION_HEADINGS = (
    "experience|education|skills(?:\\s*&\\s*abilities)?|projects|summary|languages|certifications|achievements|"
    "professional\\s+experience|work\\s+experience|employment|academic\\s+background|qualifications|"
    "technical\\s+skills|core\\s+competencies|expertise|"
    "ניסיון|ניסיון תעסוקתי|ניסיון מקצועי|השכלה|השכלה אקדמית|מיומנויות|כישורים|פרויקטים|סיכום|שפות|הסמכות|כישורים טכניים"
)

def _extract_person_header(text: str) -> tuple[str, str]:
    """
    Extract potential header section (name, contact info) from top of resume.
    Returns (header_text, remaining_text).
    """
    lines = text.splitlines()
    header_lines = []
    
    # Take up to first 10 lines or until we hit a section heading
    pattern = re.compile(rf"^\s*({_SECTION_HEADINGS})\s*[:\-]?\s*$", re.I)
    for i, line in enumerate(lines[:15]):
        if pattern.match(line.strip()):
            return "\n".join(header_lines), "\n".join(lines[i:])
        header_lines.append(line)
    
    # If no section found in first 15 lines, take first 5 as header
    if len(lines) > 5:
        return "\n".join(lines[:5]), "\n".join(lines[5:])
    return "", text


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """
    Split text based on common section headings (English + Hebrew).
    We keep headings-only lines as boundaries to improve chunk topicality.
    Enhanced to handle multi-word headings and variations.
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
_BULLET_PATTERN = re.compile(r"^[\s]*[•\-\*\–]\s*", re.MULTILINE)

def _chunk_long_text_sentence_aware(txt: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    """
    Split long text into overlapping windows, attempting to break on sentence
    boundaries to keep chunks semantically coherent.
    Enhanced with:
    - Larger chunks (1500 chars) for better context
    - Larger overlap (200 chars) to preserve continuity
    - Bullet-aware splitting for experience sections
    """
    if len(txt) <= max_chars:
        return [txt]

    # Check if text has bullet points (likely experience/skills section)
    has_bullets = bool(_BULLET_PATTERN.search(txt))
    
    if has_bullets:
        # For bulleted content, try to keep related bullets together
        return _chunk_bulleted_text(txt, max_chars, overlap)
    
    # Standard sentence-based chunking
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


def _chunk_bulleted_text(txt: str, max_chars: int, overlap: int) -> list[str]:
    """
    Chunk text with bullet points, trying to keep job entries together.
    Used for experience/skills sections.
    """
    # Split by likely job/role boundaries (date patterns or company headers)
    # This is a heuristic: look for patterns like "2020-2022" or "Company Name"
    date_pattern = re.compile(r'\b\d{4}\s*[-–—]\s*(?:\d{4}|present|current)\b', re.I)
    
    paragraphs = txt.split('\n\n')
    chunks: list[str] = []
    cur = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # If current + para fits, add it
        if not cur or len(cur) + len(para) + 2 <= max_chars:
            cur = cur + "\n\n" + para if cur else para
        else:
            # Current chunk is full, save it
            if cur:
                chunks.append(cur.strip())
            
            # Start new chunk with overlap
            if overlap > 0 and len(cur) > overlap:
                cur = cur[-overlap:] + "\n\n" + para
            else:
                cur = para
    
    if cur.strip():
        chunks.append(cur.strip())
    
    return chunks if chunks else [txt]


def chunk_resume_text(parsed_text: str) -> list[ResumeChunk]:
    """
    Generate ResumeChunk objects for each text segment. 
    Enhanced strategy:
    1. Extract header (name, contact) as separate chunk
    2. Split by section headings
    3. Within each section, create context-aware chunks
    4. Add metadata for better embedding quality
    """
    chunks: list[ResumeChunk] = []
    order = 0
    
    # Extract header section first
    header, remaining = _extract_person_header(parsed_text)
    if header.strip():
        chunks.append(ResumeChunk(
            section="header",
            ord=order,
            text=header.strip(),
            language=_detect_language(header)
        ))
        order += 1
    
    # Process remaining sections
    for section, sec_text in _split_by_headings(remaining):
        # Determine chunk size based on section type
        if section in ('experience', 'ניסיון'):
            # Larger chunks for experience to keep roles together
            max_chars, overlap = 2000, 300
        elif section in ('skills', 'מיומנויות'):
            # Medium chunks for skills
            max_chars, overlap = 1200, 150
        else:
            # Default
            max_chars, overlap = 1500, 200
        
        for piece in _chunk_long_text_sentence_aware(sec_text, max_chars, overlap):
            if piece.strip():
                chunks.append(ResumeChunk(
                    section=section,
                    ord=order,
                    text=piece.strip(),
                    language=_detect_language(piece)
                ))
                order += 1

    # Fallback: if no headings found at all, chunk entire text
    if not chunks:
        for piece in _chunk_long_text_sentence_aware(parsed_text):
            if piece.strip():
                chunks.append(ResumeChunk(
                    section=None,
                    ord=len(chunks),
                    text=piece.strip()
                ))
    return chunks


def _detect_language(text: str) -> str:
    """
    Simple heuristic language detection for Hebrew vs English.
    Returns 'he', 'en', or 'mixed'.
    """
    if not text:
        return 'en'
    
    # Count Hebrew vs Latin characters
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    
    total = hebrew_chars + latin_chars
    if total == 0:
        return 'en'
    
    hebrew_ratio = hebrew_chars / total
    if hebrew_ratio > 0.6:
        return 'he'
    elif hebrew_ratio > 0.2:
        return 'mixed'
    else:
        return 'en'
