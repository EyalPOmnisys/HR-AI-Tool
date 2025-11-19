# app/schemas/match.py
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class MatchRunRequest(BaseModel):
    """Request to run matching between job and resumes."""
    job_id: UUID
    top_n: int = Field(ge=1, le=100, default=10)
    min_threshold: int = Field(ge=0, le=100, default=0)  # Deprecated, kept for compatibility


class CandidateRow(BaseModel):
    """Single candidate result."""
    resume_id: UUID
    match: int                                      # Final combined score (0-100)
    candidate: Optional[str] = None                 # Candidate name
    title: Optional[str] = None                     # Job title (from most recent experience)
    experience: Optional[str] = None                # Years of experience
    email: Optional[str] = None
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    
    # Scoring breakdown for transparency
    rag_score: int                                  # Pure vector similarity score (0-100)
    llm_score: Optional[int] = None                 # LLM evaluation score (0-100)
    llm_verdict: Optional[str] = None               # excellent|strong|good|weak|poor|not_evaluated
    llm_strengths: Optional[str] = None             # What the LLM found positive
    llm_concerns: Optional[str] = None              # What the LLM found concerning
    llm_recommendation: Optional[str] = None        # hire_immediately|strong_interview|interview|maybe|pass
    stability_score: Optional[int] = None           # Employment stability score (0-100)
    stability_verdict: Optional[str] = None         # excellent_stability|good_stability|acceptable_stability|moderate_concerns|significant_concerns|severe_stability_issues


class MatchRunResponse(BaseModel):
    """Response from match run."""
    job_id: UUID
    requested_top_n: int
    returned: int
    candidates: List[CandidateRow]
