# app/schemas/resume.py  (the Pydantic models file you provided)
# -----------------------------------------------------------------------------
# CHANGELOG (English-only comments as requested)
# - Add optional years_by_category: dict[str, float] to both ResumeSummary and ResumeDetail.
# - Add optional primary_years: float to ResumeDetail (recommended primary years, e.g., "tech").
# - Keep years_of_experience for backward compatibility (legacy total).
# - No breaking changes: all new fields are optional and default to None/{}.
# -----------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict
from uuid import UUID

from pydantic import BaseModel, Field


class ResumeSummary(BaseModel):
    id: UUID
    name: Optional[str] = None
    profession: Optional[str] = None
    years_of_experience: Optional[float] = Field(None, ge=0)
    resume_url: str
    # New: per-category breakdown (optional)
    years_by_category: Dict[str, float] = Field(default_factory=dict)


class ResumeListOut(BaseModel):
    items: list[ResumeSummary]
    total: int


class ResumeContactItem(BaseModel):
    type: str
    label: Optional[str] = None
    value: str


class ResumeExperienceItem(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)
    tech: list[str] = Field(default_factory=list)
    duration_years: Optional[float] = Field(None, ge=0)


class ResumeEducationItem(BaseModel):
    degree: Optional[str] = None
    field: Optional[str] = None
    institution: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ResumeDetail(BaseModel):
    id: UUID
    name: Optional[str] = None
    profession: Optional[str] = None
    years_of_experience: Optional[float] = Field(None, ge=0)
    resume_url: str
    status: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    summary: Optional[str] = None
    contacts: list[ResumeContactItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience: list[ResumeExperienceItem] = Field(default_factory=list)
    education: list[ResumeEducationItem] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    years_by_category: Dict[str, float] = Field(default_factory=dict)
    primary_years: Optional[float] = Field(None, ge=0)
