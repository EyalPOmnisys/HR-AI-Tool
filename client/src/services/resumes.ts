// src/services/resumes.ts
// -----------------------------------------------------------------------------
// Maps new backend fields: years_by_category -> yearsByCategory, primary_years -> primaryYears.
// Keeps existing yearsOfExperience for backward-compat.
// -----------------------------------------------------------------------------
import type {
  ApiResumeDetail,
  ApiResumeListResponse,
  ApiResumeSummary,
  ResumeDetail,
  ResumeListResponse,
  ResumeSummary,
} from '../types/resume';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

const normalizeUrl = (value: string): string => {
  if (!value) return value;
  if (/^https?:\/\//i.test(value)) return value;
  const base = API_URL.endsWith('/') ? API_URL.slice(0, -1) : API_URL;
  const suffix = value.startsWith('/') ? value : `/${value}`;
  return `${base}${suffix}`;
};

const mapSummary = (item: ApiResumeSummary): ResumeSummary => ({
  id: item.id,
  name: item.name,
  profession: item.profession,
  yearsOfExperience: item.years_of_experience,
  resumeUrl: normalizeUrl(item.resume_url),
  // NEW:
  yearsByCategory: item.years_by_category ?? {},
  skills: item.skills ?? [],
  summary: item.summary ?? null,
});

export async function listResumes(offset = 0, limit = 10000): Promise<ResumeListResponse> {
  const res = await fetch(`${API_URL}/resumes?offset=${offset}&limit=${limit}`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch resumes (${res.status}): ${text}`);
  }

  const data: ApiResumeListResponse = await res.json();
  return {
    total: data.total,
    items: data.items.map(mapSummary),
  };
}

const mapDetail = (item: ApiResumeDetail): ResumeDetail => ({
  id: item.id,
  name: item.name,
  profession: item.profession,
  yearsOfExperience: item.years_of_experience,
  resumeUrl: normalizeUrl(item.resume_url),
  status: item.status,
  fileName: item.file_name,
  mimeType: item.mime_type,
  fileSize: item.file_size,
  summary: item.summary,
  contacts: item.contacts.map((contact) => ({
    type: contact.type,
    label: contact.label,
    value: contact.value,
  })),
  skills: item.skills.map((skill) => ({
    name: skill.name,
    source: skill.source,
    weight: skill.weight,
    category: skill.category,
  })),
  experience: item.experience.map((exp) => ({
    title: exp.title,
    company: exp.company,
    location: exp.location,
    startDate: exp.start_date,
    endDate: exp.end_date,
    bullets: exp.bullets ?? [],
    tech: exp.tech ?? [],
    durationYears: exp.duration_years,
  })),
  education: item.education.map((edu) => ({
    degree: edu.degree,
    field: edu.field,
    institution: edu.institution,
    startDate: edu.start_date,
    endDate: edu.end_date,
  })),
  languages: item.languages,
  createdAt: item.created_at,
  updatedAt: item.updated_at,
  // NEW:
  yearsByCategory: item.years_by_category ?? {},
  primaryYears: item.primary_years ?? null,
});

export async function getResumeDetail(resumeId: string): Promise<ResumeDetail> {
  const res = await fetch(`${API_URL}/resumes/${resumeId}`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch resume (${res.status}): ${text}`);
  }

  const data: ApiResumeDetail = await res.json();
  return mapDetail(data);
}

export async function deleteResume(resumeId: string): Promise<void> {
  const res = await fetch(`${API_URL}/resumes/${resumeId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to delete resume (${res.status}): ${text}`);
  }
}
