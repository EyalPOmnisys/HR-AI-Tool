# backend/app/models/__init__.py
from app.models.job import Job
from app.models.resume import Resume
from app.models.job_candidate import JobCandidate

__all__ = [
    "Job",
    "Resume",
    "JobCandidate",
]
