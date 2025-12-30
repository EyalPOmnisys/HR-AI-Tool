// src/types/jobs.ts

export type LanguageLevel = 'basic' | 'conversational' | 'fluent' | 'native' | null;

export type CurrencyCode = 'ILS' | 'USD' | 'EUR' | null;

export type LanguageRequirement = {
  name: string;
  level: LanguageLevel;
};

export type SalaryRange = {
  min: number | null;
  max: number | null;
  currency: CurrencyCode;
};

export type TechStack = {
  languages: string[];
  frameworks: string[];
  databases: string[];
  cloud: string[];
  tools: string[];
  business: string[];
};

export type Experience = {
  years_min: number | null;
  years_max: number | null;
};

export type SecurityClearance = {
  mentioned: boolean;
  note: string | null;
};

export type JobAnalysis = {
  version: number;
  role_title: string | null;
  is_tech_role: boolean;
  organization: string | null;
  locations: string[];
  summary: string | null;

  responsibilities: string[];
  requirements: string[];

  skills: {
    must_have: string[];
    nice_to_have: string[];
  };
  
  additional_skills?: string[];

  experience: Experience;
  education: string[];

  salary_range: SalaryRange | null;

  security_clearance: SecurityClearance;

  tech_stack: TechStack;

  // Human languages with proficiency level
  languages: LanguageRequirement[];

  keywords: string[];
  evidence: string[];
};

/** ===== API models ===== */

export type ApiJob = {
  id: string;
  title: string;
  job_description: string;
  free_text: string | null;
  icon: string | null;
  status: string;
  created_at: string;
  updated_at: string;

  additional_skills: string[] | null;

  analysis_json: JobAnalysis | null;
  analysis_model: string | null;
  analysis_version: number | null;

  ai_started_at: string | null;
  ai_finished_at: string | null;
  ai_error: string | null;
};

export type CreateJobPayload = {
  title: string;
  job_description: string;
  free_text?: string;
  icon?: string;
  status?: string;
  additional_skills?: string[];
  analysis_json?: JobAnalysis;
};

export type UpdateJobPayload = {
  title?: string;
  job_description?: string;
  free_text?: string;
  icon?: string;
  status?: string;
  additional_skills?: string[];
  analysis_json?: JobAnalysis;
};

export type JobListResponse = {
  items: ApiJob[];
  total: number;
};

/** ===== Optional (legacy UI model) ===== */
export interface Job {
  id: string;
  title: string;
  description: string;
  freeText?: string;
  icon: string;
  postedAt: string;
  analysis: JobAnalysis | null;
  additionalSkills: string[];
}

export type JobDraft = Omit<Job, 'id' | 'postedAt' | 'analysis'> & { analysis_json?: JobAnalysis };
