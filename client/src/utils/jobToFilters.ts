// Derive resume-search filters from an already-analyzed job.
//
// The mapping was chosen empirically against the full production dataset
// (~7,000 real resumes), measuring how many of each job's known-good match
// candidates survive each strategy. Findings:
//   - Matching the job's role title against resume professions is brittle
//     ("AI Engineer" misses "AI Software Engineer"; "Systems Analyst" misses
//     "System Analyst") — so it is NOT used.
//   - Tech roles: an ANY match over the concrete technologies keeps ~all good
//     candidates. Requiring ALL keeps almost none.
//   - Non-tech roles: the "skills" are soft phrases that never appear as resume
//     skills, so only keyword matching over the full text works.
// Hence the adaptive rule below. It favors recall (this is a pre-fill the user
// then narrows), so it never silently drops strong candidates.

import type { FilterState } from '../components/Resume/ResumeFilters/ResumeFilters'
import type { ApiJob } from '../types/job'

// Words that make a "skill" a description rather than a concrete technology.
const GENERIC_SKILL_WORDS = new Set([
  'experience', 'scripting', 'knowledge', 'skills', 'platforms', 'tools',
  'proficiency', 'familiarity', 'ability', 'strong', 'excellent', 'good',
])

// Generic role words to strip when extracting distinctive tokens from a title.
const ROLE_STOP = new Set([
  'and', 'of', 'the', 'with', 'for', 'a', 'in', 'to', 'senior', 'junior',
  'lead', 'principal', 'staff', 'engineer', 'developer', 'specialist',
  'expert', 'manager', 'role', 'position',
])

function isConcreteSkill(s: string): boolean {
  const words = s.trim().split(/\s+/)
  if (words.length === 0 || words.length > 3) return false // long phrase = description
  const core = words.filter((w) => !GENERIC_SKILL_WORDS.has(w.toLowerCase()))
  return core.length > 0
}

const emptyFilters = (): FilterState => ({
  profession: [],
  minExperience: '',
  maxExperience: '',
  skills: [],
  skillsMatchMode: 'any',
  freeText: [],
  excludeKeywords: [],
})

export function deriveFiltersFromJob(job: ApiJob): FilterState {
  const a = job.analysis_json
  const filters = emptyFilters()
  if (!a) return filters

  filters.minExperience = a.experience?.years_min != null ? String(a.experience.years_min) : ''

  const isTech = a.is_tech_role !== false
  if (isTech) {
    // Concrete technologies from must-have + tech stack, matched as ANY.
    const ts = a.tech_stack
    const techItems = ts
      ? [...ts.languages, ...ts.frameworks, ...ts.databases, ...ts.cloud, ...ts.tools]
      : []
    const raw = [...(a.skills?.must_have ?? []), ...techItems]
    const concrete = Array.from(
      new Set(raw.filter(isConcreteSkill).map((s) => s.trim()))
    )
    filters.skills = concrete
    filters.skillsMatchMode = 'any'
  } else {
    // Non-tech: distinctive tokens from the role title, matched as ANY via a
    // single OR-chip so the keyword filter does not require all of them.
    const title = a.role_title || job.title || ''
    const tokens = Array.from(
      new Set(
        title
          .split(/[^A-Za-z/]+/)
          .map((t) => t.trim())
          .filter((t) => t.length > 1 && !ROLE_STOP.has(t.toLowerCase()))
      )
    )
    if (tokens.length > 0) {
      filters.freeText = [tokens.join(' OR ')]
    }
  }

  return filters
}
