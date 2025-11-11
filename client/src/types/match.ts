// src/types/match.ts

export type MatchRunRequest = {
  job_id: string;
  top_n?: number; // User selects 1-20, default 10
  min_threshold?: number; // Not used anymore
};

export type RAGBreakdown = {
  requirements: number;
  tech: number;
  responsibility: number;
  bonuses: number;
  penalties: number;
};

export type CandidateRow = {
  resume_id: string;
  match: number;
  candidate: string | null;
  experience: string | null;
  email: string | null;
  phone: string | null;
  resume_url: string | null;
  rag_breakdown?: RAGBreakdown;
  llm_score?: number;
  llm_verdict?: string;
};

export type MatchRunResponse = {
  job_id: string;
  requested_top_n: number;
  min_threshold: number;
  returned: number;
  candidates: CandidateRow[];
};
