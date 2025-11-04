# Purpose: SQLAlchemy ORM model for Job postings including AI analysis fields.

from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    job_description = Column(Text, nullable=False)
    free_text = Column(Text, nullable=True)
    icon = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="draft")

    # AI analysis fields
    analysis_json = Column(JSONB, nullable=True)
    analysis_model = Column(String(64), nullable=True)
    analysis_version = Column(Integer, nullable=True)
    ai_started_at = Column(DateTime(timezone=True), nullable=True)
    ai_finished_at = Column(DateTime(timezone=True), nullable=True)
    ai_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
