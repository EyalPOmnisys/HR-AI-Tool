# path: backend/app/api/routers/jobs.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.job import JobCreate, JobUpdate, JobOut, JobListOut
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    return job_service.create_job(
        db,
        title=payload.title,
        job_description=payload.job_description,
        free_text=payload.free_text,
        icon=payload.icon,
        status=payload.status,
    )


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
def update_job(job_id: UUID, payload: JobUpdate, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_service.update_job(
        db,
        job,
        title=payload.title,
        job_description=payload.job_description,
        free_text=payload.free_text,
        icon=payload.icon,
        status=payload.status,
    )


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_service.delete_job(db, job)
    return None
