# Purpose: Job routes with background AI analysis on create and a manual re-run endpoint.

import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.base import get_db, SessionLocal
from app.schemas.job import JobCreate, JobUpdate, JobOut, JobListOut
from app.services.jobs import service as job_service
from app.models.job_candidate import JobCandidate
from app.models.job import Job
from app.models.resume import Resume
from app.schemas.match import CandidateRow
from app.services.resumes import ingestion_pipeline as resume_utils
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CandidateUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.put("/{job_id}/candidates/{resume_id}", status_code=200)
def update_candidate(
    job_id: UUID, 
    resume_id: UUID, 
    payload: CandidateUpdate, 
    db: Session = Depends(get_db)
):
    """Update the status or notes of a candidate for a specific job."""
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
        if payload.status is not None:
            candidate.status = payload.status
        if payload.notes is not None:
            candidate.notes = payload.notes
    else:
        # Create new record if it doesn't exist
        candidate = JobCandidate(
            job_id=job_id,
            resume_id=resume_id,
            status=payload.status or "new",
            notes=payload.notes
        )
        db.add(candidate)
    
    db.commit()
    db.refresh(candidate)
    
    return {"status": "success", "new_status": candidate.status, "notes": candidate.notes}


@router.get("/{job_id}/candidates", response_model=List[CandidateRow])
def get_job_candidates(job_id: UUID, db: Session = Depends(get_db)):
    """Get all candidates for a job (persisted results)."""
    
    # Fetch the job to check if it is a tech role
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    is_tech_role = job.analysis_json.get("is_tech_role", True) if job.analysis_json else True

    # Join JobCandidate with Resume to get contact info
    results = db.query(JobCandidate, Resume).join(
        Resume, JobCandidate.resume_id == Resume.id
    ).filter(
        JobCandidate.job_id == job_id
    ).all()
    
    candidates = []
    
    def _format_experience(years):
        if years is None: return "0 yrs"
        try:
            y = float(years)
            if y < 1 and y > 0: return "<1 yr"
            if y % 1 == 0: return f"{int(y)} yrs"
            return f"{y:.1f} yrs"
        except:
            return str(years)

    def _ensure_string(value):
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value) if value else ""

    for jc, resume in results:
        # Parse stored analysis + extraction data
        analysis = jc.analysis_json or {}
        extraction = resume.extraction_json or {}
        person = extraction.get("person") or {}

        # Determine stability score safely
        stability = analysis.get("stability", {})
        stability_score = 0
        if stability and isinstance(stability, dict):
            try:
                stability_numeric = stability.get("score", 0) or 0
                stability_score = int(float(stability_numeric) * 100)
            except (TypeError, ValueError):
                stability_score = 0

        # Derive resume metadata & contact details
        resume_url = f"/resumes/{resume.id}/file" if resume.file_path else None
        file_name = os.path.basename(resume.file_path) if resume.file_path else None

        contacts = resume_utils._extract_contacts(person)
        email = next((c["value"] for c in contacts if c.get("type") == "email"), None)
        phone = next((c["value"] for c in contacts if c.get("type") == "phone"), None)

        candidate_name = resume_utils._clean(person.get("name")) or resume_utils._infer_name_from_path(resume.file_path)
        title = resume_utils._extract_profession(
            extraction.get("experience") or [],
            extraction.get("education"),
            person
        )
        
        # Get tech-specific experience years (same logic as match service)
        exp_meta = extraction.get("experience_meta", {})
        rec_primary = exp_meta.get("recommended_primary_years", {})
        
        if is_tech_role:
            years_of_experience = rec_primary.get("tech")
        else:
            years_of_experience = rec_primary.get("other")

        candidates.append(CandidateRow(
            resume_id=jc.resume_id,
            match=jc.match_score or 0,
            candidate=candidate_name or "Unknown",
            title=title,
            experience=_format_experience(years_of_experience),
            email=email,
            phone=phone,
            resume_url=resume_url,
            file_name=file_name,
            
            rag_score=jc.rag_score or 0,
            llm_score=jc.llm_score,
            llm_verdict=analysis.get("llm_verdict"),
            llm_strengths=_ensure_string(analysis.get("llm_strengths")),
            llm_concerns=_ensure_string(analysis.get("llm_concerns")),
            stability_score=stability_score,
            stability_verdict=stability.get("verdict") if isinstance(stability, dict) else None,
            
            status=jc.status,
            notes=jc.notes
        ))
    
    # Sort by match score descending
    candidates.sort(key=lambda x: x.match, reverse=True)
    
    return candidates


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
    
    # If additional_skills were provided, store them in analysis_json immediately
    if payload.additional_skills:
        # Ensure analysis_json is a dict
        current_analysis = dict(job.analysis_json) if job.analysis_json and isinstance(job.analysis_json, dict) else {}
        current_analysis['additional_skills'] = payload.additional_skills
        
        job.analysis_json = current_analysis
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(job, "analysis_json")
        
        db.add(job)
        db.commit()
        db.refresh(job)
    
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

    # Check if content that requires re-analysis has changed
    should_reanalyze = False
    
    # If manual analysis update is provided, we use it and skip AI re-analysis
    manual_analysis_update = False
    if payload.analysis_json is not None:
        job.analysis_json = payload.analysis_json
        manual_analysis_update = True

    if not manual_analysis_update:
        if payload.job_description is not None and payload.job_description != job.job_description:
            should_reanalyze = True
        if payload.free_text is not None and payload.free_text != job.free_text:
            should_reanalyze = True

    job = job_service.update_job(
        db,
        job,
        title=payload.title,
        job_description=payload.job_description,
        free_text=payload.free_text,
        icon=payload.icon,
        status=payload.status,
    )
    
    # Update additional_skills in analysis_json if provided
    # (Only if we didn't just overwrite the whole analysis_json manually)
    if payload.additional_skills is not None and not manual_analysis_update:
        # Ensure analysis_json is a dict (it might be None or something else)
        current_analysis = dict(job.analysis_json) if job.analysis_json and isinstance(job.analysis_json, dict) else {}
        current_analysis['additional_skills'] = payload.additional_skills
        
        # Force update by assigning a new dict (SQLAlchemy JSONB detection)
        job.analysis_json = current_analysis
        
        # Mark the field as modified explicitly if needed, but reassignment usually works
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(job, "analysis_json")
        
        db.add(job)
        db.commit()
        db.refresh(job)
    
    # Only trigger background AI analysis if content actually changed AND we didn't manually update analysis
    if should_reanalyze and not manual_analysis_update:
        background.add_task(_analyze_async, job.id)
        
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_service.delete_job(db, job)
    return None
