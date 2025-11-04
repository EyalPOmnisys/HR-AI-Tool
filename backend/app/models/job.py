# path: backend/app/models/job.py
# Purpose: SQLAlchemy ORM model for Job postings.
# Notes: UUID PK, timestamps, simple text fields for MVP.
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    job_description = Column(Text, nullable=False)
    free_text = Column(Text, nullable=True)
    icon = Column(String(64), nullable=True)  # store the icon string/emoji/name
    status = Column(String(32), nullable=False, default="draft")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
