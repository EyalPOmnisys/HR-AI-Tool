# Purpose: Pydantic DTOs for Job endpoints including AI analysis fields.

from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from uuid import UUID


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    job_description: str = Field(min_length=1)
    free_text: Optional[str] = None
    icon: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default="draft", max_length=32)
    additional_skills: Optional[list[str]] = None


class JobUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=300)
    job_description: Optional[str] = None
    free_text: Optional[str] = None
    icon: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    additional_skills: Optional[list[str]] = None
    analysis_json: Optional[dict[str, Any]] = None


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
    
    additional_skills: Optional[list[str]] = None

    @model_validator(mode='after')
    def extract_additional_skills(self):
        """Extract additional_skills from analysis_json if available."""
        if self.analysis_json and isinstance(self.analysis_json, dict):
            self.additional_skills = self.analysis_json.get('additional_skills')
        return self

    class Config:
        from_attributes = True


class JobListOut(BaseModel):
    items: list[JobOut]
    total: int
