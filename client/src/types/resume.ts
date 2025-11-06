export interface ApiResumeSummary {
  id: string
  name: string | null
  profession: string | null
  years_of_experience: number | null
  resume_url: string
}

export interface ApiResumeListResponse {
  items: ApiResumeSummary[]
  total: number
}

export interface ApiResumeContactItem {
  type: string
  label: string | null
  value: string
}

export interface ApiResumeExperienceItem {
  title: string | null
  company: string | null
  location: string | null
  start_date: string | null
  end_date: string | null
  bullets: string[]
  tech: string[]
  duration_years: number | null
}

export interface ApiResumeEducationItem {
  degree: string | null
  field: string | null
  institution: string | null
  start_date: string | null
  end_date: string | null
}

export interface ApiResumeDetail {
  id: string
  name: string | null
  profession: string | null
  years_of_experience: number | null
  resume_url: string
  status: string
  file_name: string | null
  mime_type: string | null
  file_size: number | null
  summary: string | null
  contacts: ApiResumeContactItem[]
  skills: string[]
  experience: ApiResumeExperienceItem[]
  education: ApiResumeEducationItem[]
  languages: string[]
  created_at: string
  updated_at: string
}

export interface ResumeSummary {
  id: string
  name: string | null
  profession: string | null
  yearsOfExperience: number | null
  resumeUrl: string
}

export interface ResumeListResponse {
  items: ResumeSummary[]
  total: number
}

export interface ResumeContactItem {
  type: string
  label: string | null
  value: string
}

export interface ResumeExperienceItem {
  title: string | null
  company: string | null
  location: string | null
  startDate: string | null
  endDate: string | null
  bullets: string[]
  tech: string[]
  durationYears: number | null
}

export interface ResumeEducationItem {
  degree: string | null
  field: string | null
  institution: string | null
  startDate: string | null
  endDate: string | null
}

export interface ResumeDetail {
  id: string
  name: string | null
  profession: string | null
  yearsOfExperience: number | null
  resumeUrl: string
  status: string
  fileName: string | null
  mimeType: string | null
  fileSize: number | null
  summary: string | null
  contacts: ResumeContactItem[]
  skills: string[]
  experience: ResumeExperienceItem[]
  education: ResumeEducationItem[]
  languages: string[]
  createdAt: string
  updatedAt: string
}
