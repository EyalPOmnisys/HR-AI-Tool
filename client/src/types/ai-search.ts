export type PipelineTrend = 'up' | 'down' | 'steady'

export type SkillDistribution = {
  skill: string
  percentage: number
}

export type PipelineStage = {
  label: string
  count: number
  trend: PipelineTrend
}

export type CandidateProfile = {
  id: string
  name: string
  currentRole: string
  experience: string
  score: number
  strengths: string[]
  notes: string
  resumeUrl: string
  phone: string
  email: string
}

export type JobAnalytics = {
  jobId: string
  jobTitle: string
  department: string
  location: string
  summary: string
  highlights: string[]
  metrics: {
    suitability: number
    cultureAdd: number
    velocity: number
  }
  pipeline: PipelineStage[]
  skillFocus: SkillDistribution[]
  recommendedCandidates: CandidateProfile[]
}

export type JobOption = {
  id: string
  label: string
  openings: number
}
