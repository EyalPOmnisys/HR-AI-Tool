export type ApiJob = {
  id: string
  title: string
  job_description: string
  free_text: string | null
  icon: string | null
  status: string
  created_at: string
  updated_at: string
}

export type CreateJobPayload = {
  title: string
  job_description: string
  free_text?: string
  icon?: string
  status?: string
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
