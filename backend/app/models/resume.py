# Purpose: Resume model for parsed and structured resume storage.
from __future__ import annotations

import uuid
from sqlalchemy import Column, Text, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False, unique=True)
    mime_type = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)

    status = Column(String(32), nullable=False, default="ingested")
    error = Column(Text, nullable=True)

    parsed_text = Column(Text, nullable=True)
    extraction_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    applications = relationship(
        "JobCandidate",
        back_populates="resume",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
