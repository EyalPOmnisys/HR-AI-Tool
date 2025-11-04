export type JobAnalysis = {
  skills: {
    must_have: string[]
    nice_to_have: string[]
  }
  summary: string
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
  role_title: string
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
  }
  responsibilities: string[]
  security_clearance: {
    note: string | null
    mentioned: boolean
  }
}

export type ApiJob = {
  id: string
  title: string
  job_description: string
  free_text: string | null
  icon: string | null
  status: string
  created_at: string
  updated_at: string
  analysis_json: JobAnalysis | null
  analysis_model: string | null
  analysis_version: number | null
  ai_started_at: string | null
  ai_finished_at: string | null
  ai_error: string | null
}

export type CreateJobPayload = {
  title: string
  job_description: string
  free_text?: string
  icon?: string
  status?: string
}

export type UpdateJobPayload = {
  title?: string
  job_description?: string
  free_text?: string
  icon?: string
  status?: string
}

export type JobListResponse = {
  items: ApiJob[]
  total: number
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function createJob(payload: CreateJobPayload): Promise<ApiJob> {
  const res = await fetch(`${API_URL}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Failed to create job (${res.status}): ${text}`)
  }
  return res.json()
}

export async function listJobs(offset = 0, limit = 100): Promise<JobListResponse> {
  const res = await fetch(`${API_URL}/jobs?offset=${offset}&limit=${limit}`)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Failed to fetch jobs (${res.status}): ${text}`)
  }
  return res.json()
}

export async function getJob(jobId: string): Promise<ApiJob> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Failed to fetch job (${res.status}): ${text}`)
  }
  return res.json()
}

export async function updateJob(jobId: string, payload: UpdateJobPayload): Promise<ApiJob> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Failed to update job (${res.status}): ${text}`)
  }
  return res.json()
}

export async function deleteJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Failed to delete job (${res.status}): ${text}`)
  }
}
