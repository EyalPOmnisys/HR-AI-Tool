from __future__ import annotations

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

class JobCandidate(Base):
    """
    Join table representing the state of a candidate (Resume) for a specific Job.
    """
    __tablename__ = "job_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    
    # Status: new, reviewed, shortlisted, rejected
    status = Column(String(32), nullable=False, default="new")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    job = relationship("Job", back_populates="candidates")
    resume = relationship("Resume", back_populates="applications")

    # Ensure unique pair of job+resume
    __table_args__ = (
        UniqueConstraint('job_id', 'resume_id', name='uq_job_candidate_job_resume'),
    )
