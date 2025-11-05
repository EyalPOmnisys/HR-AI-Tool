# Purpose: Resume models for RAG-ready storage.
from __future__ import annotations
import uuid
from sqlalchemy import Column, Text, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.base import Base


EMBED_DIM = 768  


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

    embedding = Column(Vector(EMBED_DIM), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chunks = relationship("ResumeChunk", back_populates="resume", cascade="all, delete-orphan", passive_deletes=True)


class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)

    section = Column(String(64), nullable=True)
    ord = Column(Integer, nullable=False, default=0)
    language = Column(String(16), nullable=True)
    text = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    resume = relationship("Resume", back_populates="chunks")
    embedding_row = relationship("ResumeEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan", passive_deletes=True)


class ResumeEmbedding(Base):
    __tablename__ = "resume_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("resume_chunks.id", ondelete="CASCADE"), unique=True, nullable=False)

    embedding = Column(Vector(EMBED_DIM), nullable=False)
    embedding_model = Column(String(64), nullable=True)
    embedding_version = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunk = relationship("ResumeChunk", back_populates="embedding_row")
