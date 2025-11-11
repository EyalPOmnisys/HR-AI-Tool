# app/services/common/text_normalizer.py
from __future__ import annotations
import re
from typing import Iterable, List


# Matches any HTML-like tag to strip it before downstream processing
_TAG_RE = re.compile(r"<[^>]+>")

# Sentence splitter (simple, language-agnostic heuristic)
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> List[str]:
    """
    Very light sentence splitter that avoids heavy NLP dependencies.
    It is good enough to deduplicate repeated lines/paragraphs in JDs.
    """
    if not text:
        return []
    # Normalize whitespace first to avoid accidental duplicates due to spacing
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    # Split using punctuation boundaries
    parts = _SENT_SPLIT_RE.split(compact)
    # Also split hard line breaks (common in pasted JDs)
    out: List[str] = []
    for p in parts:
        for sub in re.split(r"\s*\n+\s*", p):
            s = sub.strip()
            if s:
                out.append(s)
    return out


def _dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """
    Deduplicate while preserving order (stable set) and skipping empty items.
    """
    seen = set()
    out: List[str] = []
    for it in items:
        key = it.strip()
        if key and key.lower() not in seen:
            seen.add(key.lower())
            out.append(key)
    return out


def normalize_text_for_fts(*parts: str) -> str:
    """
    Normalize text for simple FTS usage:
    1) join parts
    2) strip HTML tags
    3) collapse whitespace
    4) trim
    5) **deduplicate repeated sentences** (common in JDs copied twice)
    """
    # Join and strip tags
    buf = " ".join([p for p in parts if p])
    buf = _TAG_RE.sub(" ", buf)
    buf = re.sub(r"\s+", " ", buf).strip()
    if not buf:
        return ""

    # Split into sentences and deduplicate (exact text only, no paraphrasing)
    sentences = _split_sentences(buf)
    sentences = _dedupe_preserve_order(sentences)

    # Rebuild in a compact single-line form (friendly for FTS & tokenizers)
    clean = " ".join(sentences)
    return clean


def approx_token_count(text: str) -> int:
    """
    Rough token proxy (word count).
    NOTE: This is intentionally simple—good enough for analytics/ranking signals.
    """
    if not text:
        return 0
    return max(0, len(text.split()))


# ---------------------------------------------------------------------------
# Minimal language detection used by chunker.py
# ---------------------------------------------------------------------------
_HEB_RE = re.compile(r"[\u0590-\u05FF]")          # Hebrew
_AR_RE = re.compile(r"[\u0600-\u06FF]")           # Arabic
_CYR_RE = re.compile(r"[\u0400-\u04FF]")          # Cyrillic
_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")        # Basic Latin letters


def detect_lang_simple(text: str) -> str:
    """
    Ultra-light language guesser with zero external deps.
    Returns a short BCP-47-like code: 'he', 'ar', 'ru', 'en'.
    Fallback: 'en'.

    Heuristics:
    - If Hebrew codepoints present -> 'he'
    - Else if Arabic codepoints present -> 'ar'
    - Else if Cyrillic codepoints present -> 'ru'
    - Else if Latin letters dominate -> 'en'
    - Else default 'en'
    """
    if not text:
        return "en"

    if _HEB_RE.search(text):
        return "he"
    if _AR_RE.search(text):
        return "ar"
    if _CYR_RE.search(text):
        return "ru"

    # If we see Latin letters at all, assume English.
    if _LATIN_LETTER_RE.search(text):
        return "en"

    return "en"
