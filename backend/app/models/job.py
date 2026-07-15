# app/models/job.py
# Purpose: Job model for storage and analysis.

from __future__ import annotations

import uuid
from sqlalchemy import Column, Text, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base  # IMPORTANT: Base must be imported


class Job(Base):
    """
    Top-level job row.
    - `normalized_text`: preprocessed text (title + summary + cleaned description) for FTS.
    - `lang` and `tokens`: optional metadata for analytics and ranking.
    - `analysis_json`: structured AI analysis used by the matching engine.
    """
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    job_description = Column(Text, nullable=False)
    free_text = Column(Text, nullable=True)
    icon = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="draft")

    # Helper fields for better retrieval/ranking
    normalized_text = Column(Text, nullable=True)
    lang = Column(String(8), nullable=True)
    tokens = Column(Integer, nullable=True)

    # AI analysis and versioning
    analysis_json = Column(JSONB, nullable=True)
    analysis_model = Column(String(64), nullable=True)
    analysis_version = Column(Integer, nullable=True)
    ai_started_at = Column(DateTime(timezone=True), nullable=True)
    ai_finished_at = Column(DateTime(timezone=True), nullable=True)
    ai_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    candidates = relationship(
        "JobCandidate",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
