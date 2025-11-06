from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse  
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.resume import ResumeDetail, ResumeListOut, ResumeSummary
from app.services.resumes import ingestion_pipeline as resume_service

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=ResumeListOut)
def list_resumes(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
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
    resume = resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    path = Path(resume.file_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Resume file missing")

    mime = (resume.mime_type or "").lower() or "application/pdf"
    f = open(path, "rb")
    headers = {
        "Content-Disposition": f'inline; filename="{path.name}"',
    }
    return StreamingResponse(f, media_type=mime, headers=headers)
