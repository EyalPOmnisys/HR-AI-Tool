# app/models/job.py
# Purpose: Job models for RAG-friendly storage and retrieval.
# Notes:
# - Keep EMBED_DIM consistent across the whole project.
# - We store a coarse job-level embedding and fine-grained chunk-level embeddings.

from __future__ import annotations

import uuid
from sqlalchemy import Column, Text, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.base import Base  # IMPORTANT: Base must be imported

EMBED_DIM = 3072


class Job(Base):
    """
    Top-level job row.
    - `embedding`: coarse embedding for quick recall.
    - `normalized_text`: preprocessed text (title + summary + cleaned description) for FTS.
    - `lang` and `tokens`: optional metadata for analytics and ranking.
    - `chunks`: child rows with fine-grained text spans and per-chunk embeddings.
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

    # Vector embeddings (coarse job-level)
    embedding = Column(Vector(EMBED_DIM), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    chunks = relationship(
        "JobChunk",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class JobChunk(Base):
    """
    Fine-grained text spans extracted from a job (e.g., requirements bullets).
    One chunk gets at most one embedding row (1:1 via JobEmbedding).
    """
    __tablename__ = "job_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    # Optional categorization and ordering
    section = Column(String(64), nullable=True)  # e.g., "requirement" / "responsibility" / "summary"
    ord = Column(Integer, nullable=False, default=0)

    # Chunk content
    text = Column(Text, nullable=False)
    lang = Column(String(8), nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    job = relationship("Job", back_populates="chunks")
    embedding_row = relationship(
        "JobEmbedding",
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class JobEmbedding(Base):
    """
    Chunk-level embedding row (1:1 with a JobChunk).
    """
    __tablename__ = "job_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Vector embedding + versioning metadata
    embedding = Column(Vector(EMBED_DIM), nullable=True)
    embedding_model = Column(String(64), nullable=True)
    embedding_version = Column(Integer, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    chunk = relationship("JobChunk", back_populates="embedding_row")
