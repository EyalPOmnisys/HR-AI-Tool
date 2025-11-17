// src/types/resume.ts
// -----------------------------------------------------------------------------
// Adds yearsByCategory (per-domain breakdown) and primaryYears (recommended)
// while keeping yearsOfExperience for backward-compat.
// -----------------------------------------------------------------------------

export type SkillItem = {
  name: string;
  source: string;
  weight: number;
  category: string | null;
};

export type ApiResumeSummary = {
  id: string;
  name: string | null;
  profession: string | null;
  years_of_experience: number | null;
  resume_url: string;
  // NEW:
  years_by_category?: Record<string, number>; // optional on summary
};

export type ApiResumeListResponse = {
  items: ApiResumeSummary[];
  total: number;
};

export type ApiResumeDetail = {
  id: string;
  name: string | null;
  profession: string | null;
  years_of_experience: number | null;
  resume_url: string;
  status: string;
  file_name: string | null;
  mime_type: string | null;
  file_size: number | null;
  summary: string | null;
  contacts: Array<{
    type: string;
    label: string | null;
    value: string;
  }>;
  skills: SkillItem[];
  experience: Array<{
    title: string | null;
    company: string | null;
    location: string | null;
    start_date: string | null;
    end_date: string | null;
    bullets?: string[];
    tech?: string[];
    duration_years: number | null;
  }>;
  education: Array<{
    degree: string | null;
    field: string | null;
    institution: string | null;
    start_date: string | null;
    end_date: string | null;
  }>;
  languages: string[];
  created_at: string; // ISO
  updated_at: string; // ISO
  // NEW:
  years_by_category?: Record<string, number>;
  primary_years?: number | null;
};

export type ResumeSummary = {
  id: string;
  name: string | null;
  profession: string | null;
  yearsOfExperience: number | null;
  resumeUrl: string;
  // NEW:
  yearsByCategory: Record<string, number>;
};

export type ResumeListResponse = {
  items: ResumeSummary[];
  total: number;
};

export type ResumeDetail = {
  id: string;
  name: string | null;
  profession: string | null;
  yearsOfExperience: number | null;
  resumeUrl: string;
  status: string;
  fileName: string | null;
  mimeType: string | null;
  fileSize: number | null;
  summary: string | null;
  contacts: Array<{ type: string; label: string | null; value: string }>;
  skills: SkillItem[];
  experience: Array<{
    title: string | null;
    company: string | null;
    location: string | null;
    startDate: string | null;
    endDate: string | null;
    bullets: string[];
    tech: string[];
    durationYears: number | null;
  }>;
  education: Array<{
    degree: string | null;
    field: string | null;
    institution: string | null;
    startDate: string | null;
    endDate: string | null;
  }>;
  languages: string[];
  createdAt: string; // ISO
  updatedAt: string; // ISO
  yearsByCategory: Record<string, number>;
  primaryYears: number | null;
};
