# Purpose: Job routes with background AI analysis on create and a manual re-run endpoint.

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.base import get_db, SessionLocal
from app.schemas.job import JobCreate, JobUpdate, JobOut, JobListOut
from app.services.jobs import service as job_service
from app.models.job_candidate import JobCandidate
from pydantic import BaseModel

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CandidateStatusUpdate(BaseModel):
    status: str


@router.put("/{job_id}/candidates/{resume_id}", status_code=200)
def update_candidate_status(
    job_id: UUID, 
    resume_id: UUID, 
    payload: CandidateStatusUpdate, 
    db: Session = Depends(get_db)
):
    """Update the status of a candidate for a specific job."""
    # Check if job exists
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if candidate record exists
    candidate = db.query(JobCandidate).filter(
        JobCandidate.job_id == job_id,
        JobCandidate.resume_id == resume_id
    ).first()

    if candidate:
        candidate.status = payload.status
    else:
        # Create new record if it doesn't exist
        candidate = JobCandidate(
            job_id=job_id,
            resume_id=resume_id,
            status=payload.status
        )
        db.add(candidate)
    
    db.commit()
    db.refresh(candidate)
    
    return {"status": "success", "new_status": candidate.status}


@router.post("", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    job = job_service.create_job(
        db,
        title=payload.title,
        job_description=payload.job_description,
        free_text=payload.free_text,
        icon=payload.icon,
        status=payload.status,
    )
    background.add_task(_analyze_async, job.id)
    return job


def _analyze_async(job_id: UUID):
    """Create a short-lived DB session for the background task."""
    db = SessionLocal()
    try:
        job_service.analyze_and_attach_job(db, job_id)
    finally:
        db.close()


@router.post("/{job_id}/analyze", response_model=JobOut)
def analyze_job(job_id: UUID, db: Session = Depends(get_db)):
    job = job_service.analyze_and_attach_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=JobListOut)
def list_jobs(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    items, total = job_service.list_jobs(db, offset=offset, limit=limit)
    return JobListOut(items=items, total=total)


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: UUID, payload: JobUpdate, background: BackgroundTasks, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_service.update_job(
        db,
        job,
        title=payload.title,
        job_description=payload.job_description,
        free_text=payload.free_text,
        icon=payload.icon,
        status=payload.status,
    )
    # Re-run AI analysis in background after update
    background.add_task(_analyze_async, job.id)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_service.delete_job(db, job)
    return None
