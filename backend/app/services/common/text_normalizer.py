from __future__ import annotations
import re
import logging

logger = logging.getLogger("common.text_normalizer")

_TAG_RE = re.compile(r"<[^>]+>")
_HEB_RE = re.compile(r"[\u0590-\u05FF]")  # Hebrew Unicode block


def normalize_text_for_fts(*parts: str) -> str:
    buf = " ".join([p for p in parts if p])
    buf = _TAG_RE.sub(" ", buf)
    buf = re.sub(r"\s+", " ", buf).strip()
    return buf


def approx_token_count(text: str) -> int:
    if not text:
        return 0
    return max(0, len(text.split()))


def detect_lang_simple(text: str) -> str:
    """
    Very lightweight language detector:
    - If Hebrew characters present in meaningful amount -> 'he'
    - Else default to 'en'
    """
    if not text:
        return "en"
    heb = len(_HEB_RE.findall(text))
    if heb >= 2:  # tiny heuristic
        return "he"
    return "en"
