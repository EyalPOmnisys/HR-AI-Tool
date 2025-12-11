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
  title: string | null;
  experience: string | null;
  email: string | null;
  phone: string | null;
  resume_url: string | null;
  file_name?: string | null;
  rag_breakdown?: RAGBreakdown;
  rag_score?: number;
  llm_score?: number;
  llm_verdict?: string;
  llm_strengths?: string;
  llm_concerns?: string;
  stability_score?: number;
  stability_verdict?: string;
  status?: string; // new, reviewed, shortlisted, rejected
  notes?: string; // Free text notes
};

export type MatchRunResponse = {
  job_id: string;
  requested_top_n: number;
  min_threshold: number;
  new_candidates: CandidateRow[];
  new_count: number;
  previously_reviewed_count: number;
  all_candidates_already_reviewed: boolean;
};
