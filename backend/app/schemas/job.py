# Purpose: Pydantic DTOs for Job endpoints including AI analysis fields.

from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    job_description: str = Field(min_length=1)
    free_text: Optional[str] = None
    icon: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default="draft", max_length=32)


class JobUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=300)
    job_description: Optional[str] = None
    free_text: Optional[str] = None
    icon: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)


class JobOut(BaseModel):
    id: UUID
    title: str
    job_description: str
    free_text: Optional[str]
    icon: Optional[str]
    status: str

    analysis_json: Optional[Any] = None
    analysis_model: Optional[str] = None
    analysis_version: Optional[int] = None
    ai_started_at: Optional[datetime] = None
    ai_finished_at: Optional[datetime] = None
    ai_error: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobListOut(BaseModel):
    items: list[JobOut]
    total: int
