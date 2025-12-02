from __future__ import annotations
from typing import Optional, Tuple, Iterable
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.resume import Resume, ResumeChunk, ResumeEmbedding


def get_by_hash(db: Session, content_hash: str) -> Optional[Resume]:
    stmt = select(Resume).where(Resume.content_hash == content_hash)
    return db.execute(stmt).scalar_one_or_none()


def create_resume(db: Session, *, file_path: str, content_hash: str, mime_type: Optional[str], file_size: Optional[int]) -> Resume:
    r = Resume(file_path=file_path, content_hash=content_hash, mime_type=mime_type, file_size=file_size, status="ingested")
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def set_status(db: Session, resume: Resume, *, status: str, error: Optional[str] = None) -> Resume:
    resume.status = status
    resume.error = error
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def attach_parsed_text(db: Session, resume: Resume, *, parsed_text: str) -> Resume:
    resume.parsed_text = parsed_text
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def attach_extraction(db: Session, resume: Resume, *, extraction_json) -> Resume:
    resume.extraction_json = extraction_json
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def attach_resume_embedding(db: Session, resume: Resume, *, embedding: list[float]) -> Resume:
    resume.embedding = embedding
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def bulk_add_chunks(db: Session, resume: Resume, chunks: Iterable[ResumeChunk]) -> list[ResumeChunk]:
    for c in chunks:
        c.resume_id = resume.id
        db.add(c)
    db.commit()
    # refresh list
    rows = db.execute(select(ResumeChunk).where(ResumeChunk.resume_id == resume.id).order_by(ResumeChunk.ord)).scalars().all()
    return rows


def upsert_chunk_embedding(db: Session, chunk: ResumeChunk, *, embedding: list[float], model: Optional[str], version: Optional[int]) -> ResumeEmbedding:
    existing = db.execute(select(ResumeEmbedding).where(ResumeEmbedding.chunk_id == chunk.id)).scalar_one_or_none()
    if existing:
        existing.embedding = embedding
        existing.embedding_model = model
        existing.embedding_version = version
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = ResumeEmbedding(chunk_id=chunk.id, embedding=embedding, embedding_model=model, embedding_version=version)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_resumes(db: Session, *, offset: int = 0, limit: int = 20) -> Tuple[list[Resume], int]:
    total = db.execute(select(func.count()).select_from(Resume)).scalar_one()
    rows = db.execute(
        select(Resume).order_by(Resume.created_at.desc()).offset(offset).limit(limit)
    ).scalars().all()
    return rows, total


def get_resume(db: Session, resume_id: UUID) -> Optional[Resume]:
    return db.get(Resume, resume_id)


def delete_resume(db: Session, resume_id: UUID) -> bool:
    resume = get_resume(db, resume_id)
    if not resume:
        return False
    db.delete(resume)
    db.commit()
    return True
