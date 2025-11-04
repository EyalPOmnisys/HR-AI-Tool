# Purpose: Pydantic schema for validating the Job AI analysis payload.

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class SalaryRange(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    currency: Optional[Literal["ILS", "USD", "EUR"]] = None


class LanguageItem(BaseModel):
    name: str
    level: Optional[Literal["basic", "conversational", "fluent", "native"]] = None


class Experience(BaseModel):
    years_min: Optional[int] = None
    years_max: Optional[int] = None


class TechStack(BaseModel):
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)


class Skills(BaseModel):
    must_have: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)


class SecurityClearance(BaseModel):
    mentioned: bool = False
    note: Optional[str] = None


class JobAnalysis(BaseModel):
    version: int = 1
    role_title: Optional[str] = None
    organization: Optional[str] = None
    locations: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    experience: Experience = Field(default_factory=Experience)
    education: List[str] = Field(default_factory=list)
    salary_range: Optional[SalaryRange] = None
    security_clearance: SecurityClearance = Field(default_factory=SecurityClearance)
    tech_stack: TechStack = Field(default_factory=TechStack)
    languages: List[LanguageItem] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)

    class Config:
        extra = "ignore"
