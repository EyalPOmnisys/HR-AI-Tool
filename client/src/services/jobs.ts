// src/services/jobs.ts
import type {
  ApiJob,
  CreateJobPayload,
  UpdateJobPayload,
  JobListResponse,
} from '../types/job';
import type { CandidateRow } from '../types/match';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export async function createJob(payload: CreateJobPayload): Promise<ApiJob> {
  const res = await fetch(`${API_URL}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to create job (${res.status}): ${text}`);
  }
  return res.json();
}

export async function listJobs(offset = 0, limit = 100): Promise<JobListResponse> {
  const res = await fetch(`${API_URL}/jobs?offset=${offset}&limit=${limit}`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch jobs (${res.status}): ${text}`);
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<ApiJob> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch job (${res.status}): ${text}`);
  }
  return res.json();
}

export async function getJobCandidates(jobId: string): Promise<CandidateRow[]> {
  const res = await fetch(`${API_URL}/jobs/${jobId}/candidates`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch candidates (${res.status}): ${text}`);
  }
  return res.json();
}

export async function updateJob(jobId: string, payload: UpdateJobPayload): Promise<ApiJob> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to update job (${res.status}): ${text}`);
  }
  return res.json();
}

export async function deleteJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`, { method: 'DELETE' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to delete job (${res.status}): ${text}`);
  }
}

export async function updateCandidate(
  jobId: string, 
  resumeId: string, 
  payload: { status?: string; notes?: string }
): Promise<{ status: string; new_status: string; notes?: string }> {
  const res = await fetch(`${API_URL}/jobs/${jobId}/candidates/${resumeId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to update candidate (${res.status}): ${text}`);
  }
  return res.json();
}

// Deprecated: Use updateCandidate instead
export async function updateCandidateStatus(jobId: string, resumeId: string, status: string) {
  return updateCandidate(jobId, resumeId, { status });
}
