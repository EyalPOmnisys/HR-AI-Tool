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
    file_name: Optional[str] = None  # Added for file type detection
    
    # Scoring breakdown for transparency
    rag_score: int                                  # Pure vector similarity score (0-100)
    llm_score: Optional[int] = None                 # LLM evaluation score (0-100)
    llm_verdict: Optional[str] = None               # excellent|strong|good|weak|poor|not_evaluated
    llm_strengths: Optional[str] = None             # What the LLM found positive
    llm_concerns: Optional[str] = None              # What the LLM found concerning
    stability_score: Optional[int] = None           # Employment stability score (0-100)
    stability_verdict: Optional[str] = None         # excellent_stability|good_stability|acceptable_stability|moderate_concerns|significant_concerns|severe_stability_issues
    
    # Status tracking
    status: str = "new"                             # new|reviewed|shortlisted|rejected
    
    # User Notes
    notes: Optional[str] = None                     # Free text notes from user


class MatchRunResponse(BaseModel):
    """Response from match run."""
    job_id: UUID
    requested_top_n: int
    min_threshold: int
    new_candidates: List[CandidateRow]
    new_count: int
    previously_reviewed_count: int
    all_candidates_already_reviewed: bool
