"""Resume API endpoints: list summaries, fetch detailed structured resume data, and preview original files.

Provides lightweight listing plus rich detail retrieval and format-aware streaming/HTML conversion
for PDF/DOCX/TXT resumes with Hebrew RTL support.
"""
from __future__ import annotations

import io
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse  
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.resume import ResumeDetail, ResumeListOut, ResumeSummary, ResumeSearchAnalysis
from app.services.resumes import ingestion_pipeline as resume_service
from app.services.resumes import search_service

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/search/analyze", response_model=ResumeSearchAnalysis)
def analyze_search(query: str = Query(..., min_length=1)):
    """
    Analyze a natural language search query and return structured filters.
    """
    return search_service.analyze_search_query(query)


@router.get("", response_model=ResumeListOut)
def list_resumes(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(3000, ge=1, le=10000),
):
    summaries, total = resume_service.list_resume_summaries(db, offset=offset, limit=limit)
    items = [ResumeSummary(**summary) for summary in summaries]
    return ResumeListOut(items=items, total=total)


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(resume_id: UUID, db: Session = Depends(get_db)):
    resume = resume_service.get_resume_detail(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return ResumeDetail(**resume)


@router.get("/{resume_id}/file")
def preview_resume(resume_id: UUID, db: Session = Depends(get_db)):
    """
    Return resume file for preview:
    - PDF: stream the original file
    - DOCX: convert to HTML with RTL support for Hebrew
    - TXT: return as HTML with proper formatting
    """
    resume = resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    path = Path(resume.file_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Resume file missing")

    mime = (resume.mime_type or "").lower()
    suffix = path.suffix.lower()
    
    # Encode filename for Content-Disposition header (RFC 5987)
    # This handles Hebrew and other non-ASCII characters
    encoded_filename = quote(path.name.encode('utf-8'))
    
    # For PDF files, stream the original
    if suffix == ".pdf" or "pdf" in mime:
        f = open(path, "rb")
        headers = {
            "Content-Disposition": f'inline; filename*=UTF-8\'\'{encoded_filename}',
        }
        return StreamingResponse(f, media_type="application/pdf", headers=headers)
    
    # For DOCX, stream the original so frontend can render it
    if suffix == ".docx":
        f = open(path, "rb")
        headers = {
            "Content-Disposition": f'inline; filename*=UTF-8\'\'{encoded_filename}',
        }
        return StreamingResponse(f, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)

    # For TXT, convert to HTML
    if suffix == ".txt":
        html_content = _convert_to_html(path, resume.parsed_text or "")
        return HTMLResponse(content=html_content)
    
    # Fallback: try to stream as-is
    f = open(path, "rb")
    headers = {
        "Content-Disposition": f'inline; filename*=UTF-8\'\'{encoded_filename}',
    }
    return StreamingResponse(f, media_type=mime or "application/octet-stream", headers=headers)


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: UUID, db: Session = Depends(get_db)):
    success = resume_service.delete_resume(db, resume_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found")
    return None


def _convert_to_html(file_path: Path, parsed_text: str) -> str:
    """
    Convert TXT file to HTML for browser display.
    Uses parsed_text (already RTL-fixed) and formats it nicely.
    """
    from html import escape
    
    # If we have parsed text, use it (it's already RTL-fixed)
    if parsed_text:
        text = parsed_text
    else:
        # Fallback: read and parse the file
        from app.services.resumes.parsing_utils import parse_to_text
        text = parse_to_text(file_path)
    
    # Escape HTML and preserve line breaks
    safe_text = escape(text)
    
    # Detect if text contains Hebrew
    has_hebrew = any('\u0590' <= char <= '\u05FF' for char in text)
    direction = "rtl" if has_hebrew else "ltr"
    text_align = "right" if has_hebrew else "left"
    
    html = f"""
<!DOCTYPE html>
<html lang="he" dir="{direction}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Preview</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans Hebrew', sans-serif;
            line-height: 1.7;
            padding: 2.5rem;
            max-width: 850px;
            margin: 0 auto;
            background: #ffffff;
            color: #1e293b;
            direction: {direction};
            text-align: {text_align};
            font-size: 15px;
        }}
        .content {{
            white-space: pre-wrap;
            word-wrap: break-word;
            font-feature-settings: "liga" 1, "calt" 1;
        }}
        @media print {{
            body {{
                padding: 1.5rem;
                font-size: 13px;
            }}
        }}
        @media (max-width: 768px) {{
            body {{
                padding: 1.5rem;
                font-size: 14px;
            }}
        }}
    </style>
</head>
<body>
    <div class="content">{safe_text}</div>
</body>
</html>
    """
    return html
