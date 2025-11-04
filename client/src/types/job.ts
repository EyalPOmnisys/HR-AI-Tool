export type JobAnalysis = {
  skills: {
    must_have: string[]
    nice_to_have: string[]
  }
  summary: string | null
  version: number
  evidence: string[]
  keywords: string[]
  education: string[]
  languages: string[]
  locations: string[]
  experience: {
    years_max: number | null
    years_min: number | null
  }
  role_title: string | null
  tech_stack: {
    databases: string[]
    languages: string[]
    frameworks: string[]
  }
  organization: string | null
  requirements: string[]
  salary_range: {
    max: number | null
    min: number | null
    currency: string | null
  } | null
  responsibilities: string[]
  security_clearance: {
    note: string | null
    mentioned: boolean
  }
}

export interface Job {
  id: string
  title: string
  description: string
  freeText: string
  icon: string
  postedAt: string
  analysis: JobAnalysis | null
}

export type JobDraft = Omit<Job, 'id' | 'postedAt' | 'analysis'>
