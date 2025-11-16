from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Tuple


# Detect if text includes any Hebrew characters
def is_hebrew_text(text: str) -> bool:
    return bool(re.search(r"[\u0590-\u05FF]", text or ""))


# Preprocess Hebrew resume text for LLM extraction (normalizes punctuation, bullets, headings, dates, and RTL marks)
def preprocess_hebrew_text(text: str, for_llm: bool = True) -> Tuple[str, Dict]:
    t = unicodedata.normalize("NFC", text or "")
    t = _strip_nikud(t)
    t = _normalize_punctuation(t)
    t = _normalize_bullets(t)
    t, headings = _canonicalize_headings(t)
    t = _normalize_mixed_runs(t)
    t = _mark_dates_for_llm(t)
    t = _add_rtl_marks(t)

    meta = {
        "language": "he",
        "headings_map": headings,
        "contacts": extract_contacts(text or ""),
    }
    return t, meta


# Extract basic contacts (email/phone) for redundancy
def extract_contacts(text: str) -> Dict[str, Optional[str]]:
    email_re = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
    phone_re = re.compile(r"(\+972-?\s?\d{8,9}|\+972\d{8,9}|0?5\d-?\s?\d{7})")
    email_m = email_re.search(text)
    phone_m = phone_re.search(text)

    phone_val: Optional[str] = None
    if phone_m:
        p = phone_m.group(0).replace(" ", "").replace("-", "")
        if p.startswith("05"):
            phone_val = "+972" + p[1:]
        elif p.startswith("+9720"):
            phone_val = "+972" + p[5:]
        else:
            phone_val = p

    return {
        "email": email_m.group(0) if email_m else None,
        "phone": phone_val,
    }


# Remove Hebrew diacritics (nikud)
def _strip_nikud(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


# Normalize punctuation and unify bullets spacing
def _normalize_punctuation(text: str) -> str:
    t = text.replace("–", "-").replace("—", "-")
    t = t.replace("“", '"').replace("”", '"').replace("‟", '"').replace("״", '"')
    t = t.replace("’", "'").replace("‚", ",").replace("˙", ".")
    t = re.sub(r"\s*:\s*", ": ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t


# Normalize bullet characters to a consistent "- " prefix
def _normalize_bullets(text: str) -> str:
    return re.sub(r"^\s*[\u2022\u2023\u25E6\u2043\u2219\-\*]\s*", "- ", text, flags=re.MULTILINE)


# Canonicalize common Hebrew section headings to explicit markers
def _canonicalize_headings(text: str) -> Tuple[str, Dict[str, str]]:
    headings_map = {
        r"\bניסיון\b": "EXPERIENCE",
        r"\bניסיון\s+תעסוקתי\b": "EXPERIENCE",
        r"\bניסיון\s+מקצועי\b": "EXPERIENCE",
        r"\bפרויקט(ים)?\b": "PROJECTS",
        r"\bפרויקטים\b": "PROJECTS",
        r"\bתפקיד(ים)?\b": "EXPERIENCE",
        r"\bטכנולוגיות\b": "SKILLS",
        r"\bמיומנויות\b": "SKILLS",
        r"\bכישורים\b": "SKILLS",
        r"\bשפות\s*(תכנות)?\b": "SKILLS",
        r"\bכלים\b": "SKILLS",
        r"\bהשכלה\b": "EDUCATION",
        r"\bלימודים\b": "EDUCATION",
        r"\bשפות\b": "LANGUAGES",
        r"\bפרופיל\b": "SUMMARY",
        r"\bתקציר\b": "SUMMARY",
        r"\bסיכום\b": "SUMMARY",
        r"\bשירות\s+צבאי\b": "MILITARY",
        r"\bקורס(ים)?\b": "COURSES",
    }
    applied: Dict[str, str] = {}
    out = text
    for patt, canon in headings_map.items():
        out_new = re.sub(rf"(?im)^\s*{patt}\s*[:\-]?\s*$", f"<<SECTION:{canon}>>", out)
        if out_new != out:
            applied[patt] = canon
            out = out_new
    return out, applied


# Surround Latin runs inside Hebrew lines with LRM to stabilize bidi rendering
def _normalize_mixed_runs(text: str) -> str:
    lrm = "\u200E"
    def fix_line(line: str) -> str:
        if not is_hebrew_text(line):
            return line
        return re.sub(r"[A-Za-z]+", lambda m: f"{lrm}{m.group(0)}{lrm}", line)
    return "\n".join(fix_line(ln) for ln in text.splitlines())


# Mark Hebrew date ranges and single years to guide LLM
def _mark_dates_for_llm(text: str) -> str:
    months = "ינואר|פברואר|מרץ|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר"
    year = r"(20\d{2}|19\d{2})"
    present = r"(כיום|הווה|נוכחי|present|now)"

    def norm_range(m: re.Match) -> str:
        m1, y1, m2, y2 = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        mnum = {
            "ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4, "מאי": 5, "יוני": 6,
            "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12,
        }
        start = f"{y1:04d}-{mnum.get(m1, 1):02d}-01"
        if re.fullmatch(present, y2, flags=re.I):
            end = "PRESENT"
        else:
            end = f"{int(y2):04d}-{mnum.get(m2, 1):02d}-01"
        return f"[DATE:{start}..{end}]"

    t = re.sub(rf"\b({months})\s+{year}\s*[-–]\s*({months})\s+({year}|{present})\b", norm_range, text, flags=re.I)

    def _yr_range_repl(m: re.Match) -> str:
        y1 = int(m.group(1))
        y2_raw = m.group(2)
        if re.fullmatch(present, y2_raw, flags=re.I):
            end = "PRESENT"
        else:
            end = f"{int(y2_raw):04d}-01-01"
        return f"[DATE:{y1:04d}-01-01..{end}]"

    t = re.sub(rf"\b{year}\s*[-–]\s*({year}|{present})\b", _yr_range_repl, t, flags=re.I)
    t = re.sub(rf"\b({year})\b", r"[YEAR:\1]", t)
    return t


# Add RTL marks to Hebrew lines to reduce bidi confusion
def _add_rtl_marks(text: str) -> str:
    rlm = "\u200F"
    lrm = "\u200E"
    def mark(line: str) -> str:
        if is_hebrew_text(line):
            return rlm + line + lrm
        return line
    return "\n".join(mark(ln) for ln in text.splitlines())
