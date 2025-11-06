import type { JobAnalytics, PipelineStage, SkillDistribution, CandidateProfile } from '../types/ai-search'

// Helper: clamp percentage 0..100
const pct = (n: number) => Math.max(0, Math.min(100, Math.round(n)))

function buildPipeline(total: number): PipelineStage[] {
  const applied = Math.max(12, Math.round(total * 0.4))
  const screened = Math.max(8, Math.round(total * 0.25))
  const shortlisted = Math.max(5, Math.round(total * 0.2))
  const interviews = Math.max(3, Math.round(total * 0.1))
  const offers = Math.max(1, Math.round(total * 0.05))
  return [
    { label: 'Applied', count: applied, trend: 'up' },
    { label: 'Screened', count: screened, trend: 'steady' },
    { label: 'Shortlisted', count: shortlisted, trend: 'up' },
    { label: 'Interviews', count: interviews, trend: 'up' },
    { label: 'Offers', count: offers, trend: 'steady' },
  ]
}

function defaultSkills(topic: string): SkillDistribution[] {
  const base: SkillDistribution[] = [
    { skill: `${topic} Fundamentals`, percentage: 28 },
    { skill: 'Problem Solving', percentage: 22 },
    { skill: 'Communication', percentage: 18 },
    { skill: 'System Design', percentage: 17 },
    { skill: 'Leadership', percentage: 15 },
  ]
  // Normalize to 100
  const sum = base.reduce((a, b) => a + b.percentage, 0)
  return base.map((s) => ({ ...s, percentage: Math.round((s.percentage / sum) * 100) }))
}

function makeCandidate(i: number, role: string): CandidateProfile {
  const scores = [92, 88, 85, 81, 78, 75, 73, 71, 89, 86, 83, 80, 77, 74, 72, 90, 87, 84, 82, 79]
  const names = [
    'Alex Kim',
    'Jordan Lee',
    'Taylor Cohen',
    'Riley Shah',
    'Noa Levi',
    'Dana Adler',
    'Avi Bar',
    'Sam Rivera',
    'Casey Morgan',
    'Morgan Blake',
    'Jamie Davis',
    'Jordan Foster',
    'Alex Pierce',
    'Sam Carter',
    'Taylor Mitchell',
    'Riley Cooper',
    'Casey Graham',
    'Morgan Hayes',
    'Jamie Pierce',
    'Alex Stewart',
  ]
  const roles = [
    `${role} Engineer`,
    `Senior ${role}`,
    `${role} Specialist`,
    `${role} Lead`,
    `${role} IC`,
    `${role} Consultant`,
    `${role} Analyst`,
    `${role} Manager`,
    `${role} Architect`,
    `${role} Developer`,
  ]
  const strengthsPool = [
    'Data-driven decisions',
    'Cross-team collaboration',
    'Clear communication',
    'Mentors juniors',
    'Delivers under pressure',
    'Deep technical expertise',
    'Process improvement',
    'Strategic planning',
    'Problem-solving skills',
    'Leadership qualities',
  ]
  
  const nameFormatted = names[i % names.length].toLowerCase().replace(' ', '.')
  const email = `${nameFormatted}@email.com`
  const phone = `+1 (${555 + (i % 100)}) ${Math.floor(Math.random() * 1000)}-${Math.floor(Math.random() * 10000)
    .toString()
    .padStart(4, '0')}`
  
  return {
    id: `cand-${i + 1}`,
    name: names[i % names.length],
    currentRole: roles[i % roles.length],
    experience: `${5 + (i % 12)} yrs experience`,
    score: scores[i % scores.length],
    strengths: [strengthsPool[i % strengthsPool.length], strengthsPool[(i + 3) % strengthsPool.length]],
    notes: 'Calibrated match based on skills, impact, and domain alignment.',
    resumeUrl: '#',
    phone,
    email,
  }
}

function buildDefaultAnalytics(jobId: string): JobAnalytics {
  const title = 'AI-Selected Role'
  const dept = 'General'
  const location = '—'
  const roleTopic = 'Core Skills'

  const recommended: CandidateProfile[] = new Array(20).fill(0).map((_, i) => makeCandidate(i, 'Talent'))

  return {
    jobId,
    jobTitle: title,
    department: dept,
    location,
    summary:
      'Auto-generated insights for the selected role. This is mock data used to render the dashboard while backend analytics are wiring up.',
    highlights: [
      'Strong pipeline health across top-of-funnel',
      'Balanced skills distribution with emphasis on fundamentals',
      'Curated candidates prioritised for interview readiness',
    ],
    metrics: {
      suitability: pct(84),
      cultureAdd: pct(77),
      velocity: pct(69),
    },
    pipeline: buildPipeline(60),
    skillFocus: defaultSkills(roleTopic),
    recommendedCandidates: recommended,
  }
}

// A small set of prefilled examples (useful if your job IDs are known)
const prefills: Record<string, JobAnalytics> = {}

// On-demand mock map: any unknown jobId will get a deterministic default analytics object.
export const analyticsByJobId: Record<string, JobAnalytics> = new Proxy(prefills, {
  get(target, prop: string | symbol) {
    if (typeof prop !== 'string') return (target as any)[prop]
    if (prop in target) return target[prop]
    const generated = buildDefaultAnalytics(prop)
    target[prop] = generated
    return generated
  },
}) as unknown as Record<string, JobAnalytics>
