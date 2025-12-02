# backend/app/models/__init__.py
from app.models.job import Job, JobChunk, JobEmbedding
from app.models.resume import Resume, ResumeChunk, ResumeEmbedding
from app.models.job_candidate import JobCandidate

__all__ = [
    "Job",
    "JobChunk", 
    "JobEmbedding",
    "Resume",
    "ResumeChunk",
    "ResumeEmbedding",
    "JobCandidate",
]
