from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from app.services.common.text_normalizer import detect_lang_simple

logger = logging.getLogger("jobs.chunker")

def _safe_lines(items: Optional[List[str]]) -> List[str]:
    if not items:
        return []
    return [x.strip() for x in items if isinstance(x, str) and x.strip()]

def _basic_fallback_chunks(text: str, max_chunk_chars: int = 800) -> List[str]:
    paras = [p.strip() for p in text.splitlines() if p.strip()]
    chunks: List[str] = []
    buf: List[str] = []
    acc = 0
    for p in paras:
        if acc + len(p) + 1 > max_chunk_chars and buf:
            chunks.append(" ".join(buf).strip())
            buf, acc = [], 0
        buf.append(p)
        acc += len(p) + 1
    if buf:
        chunks.append(" ".join(buf).strip())
    return chunks or ([text.strip()] if text.strip() else [])

def build_chunks_from_analysis(
    *,
    title: str,
    job_description: str,
    free_text: Optional[str],
    analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cursor = 0

    logger.info("Building chunks for job '%s'", title)

    summary = (analysis.get("summary") or "").strip()
    if summary:
        out.append({"section": "summary", "ord": cursor, "text": summary, "lang": None})
        cursor += 1

    for line in _safe_lines(analysis.get("responsibilities")):
        out.append({"section": "responsibility", "ord": cursor, "text": line, "lang": None})
        cursor += 1

    for line in _safe_lines(analysis.get("requirements")):
        out.append({"section": "requirement", "ord": cursor, "text": line, "lang": None})
        cursor += 1

    tech_stack = analysis.get("tech_stack") or {}
    tech_parts: List[str] = []
    for key in ("languages", "frameworks", "databases", "cloud", "tools", "business", "management"):
        vals = _safe_lines(tech_stack.get(key))
        if vals:
            tech_parts.append(f"{key}: " + ", ".join(vals))
    if tech_parts:
        out.append({"section": "tech_stack", "ord": cursor, "text": " | ".join(tech_parts), "lang": None})
        cursor += 1

    if not out:
        for chunk in _basic_fallback_chunks(job_description):
            out.append({"section": "description", "ord": cursor, "text": chunk, "lang": None})
            cursor += 1

    if free_text and free_text.strip():
        out.append({"section": "notes", "ord": cursor, "text": free_text.strip(), "lang": None})

    # Fill language per-chunk
    for c in out:
        if not c.get("lang"):
            c["lang"] = detect_lang_simple(c.get("text", ""))

    logger.info("Built %d chunks (summary=%s)", len(out), "yes" if summary else "no")
    return out
