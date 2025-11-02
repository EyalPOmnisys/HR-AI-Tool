import type { JobAnalytics, JobOption } from '../types/ai-search'

export const jobOptions: readonly JobOption[] = [
  {
    id: 'senior-product-manager',
    label: 'Senior Product Manager · Core Platform',
    openings: 1
  },
  {
    id: 'ml-engineer',
    label: 'Machine Learning Engineer · Recommendations',
    openings: 2
  },
  {
    id: 'talent-partner',
    label: 'Senior Talent Partner · GTM',
    openings: 1
  }
]

export const analyticsByJobId: Record<string, JobAnalytics> = {
  'senior-product-manager': {
    jobId: 'senior-product-manager',
    jobTitle: 'Senior Product Manager',
    department: 'Product · Core Platform',
    location: 'Hybrid · Tel Aviv',
    summary:
      'High alignment with platform stability strategy. Prioritised candidates bring deep marketplace expertise and proven track records launching revenue-driving features.',
    highlights: [
      'Top candidates ship complex initiatives within 120-day cycles',
      'Strong cross-functional collaboration scores from previous orgs',
      'Proven ability to balance experimentation with platform uptime goals'
    ],
    metrics: {
      suitability: 92,
      cultureAdd: 87,
      velocity: 78
    },
    pipeline: [
      { label: 'Sourcing', count: 38, trend: 'up' },
      { label: 'Screened', count: 18, trend: 'up' },
      { label: 'Interview', count: 8, trend: 'steady' },
      { label: 'Offer', count: 2, trend: 'up' }
    ],
    skillFocus: [
      { skill: 'Platform Strategy', percentage: 32 },
      { skill: 'Stakeholder Alignment', percentage: 24 },
      { skill: 'Experimentation', percentage: 21 },
      { skill: 'Revenue Optimisation', percentage: 16 },
      { skill: 'Team Leadership', percentage: 7 }
    ],
    recommendedCandidates: [
      {
        id: 'cpm-01',
        name: 'Lia Vered',
        currentRole: 'Director of Product · FinTech OS',
        experience: '12 yrs · Ex-PayPal, Ex-Wix',
        score: 96,
        strengths: [
          'Scaled platform to 4M users with zero downtime launches',
          'Created multi-quarter strategy with 18% ARR uplift'
        ],
        notes: 'High executive exposure, top quartile collaborator feedback from engineering and design peers.'
      },
      {
        id: 'cpm-02',
        name: 'Jonah Beck',
        currentRole: 'Principal PM · Marketplace Co.',
        experience: '10 yrs · Ex-Airbnb',
        score: 92,
        strengths: [
          'Led experimentation backlog reducing churn by 6.4%',
          'Coached squads on KPI-driven prioritisation frameworks'
        ],
        notes: 'Recently relocated to Tel Aviv, long runway for growth, strong storytelling in exec reviews.'
      },
      {
        id: 'cpm-03',
        name: 'Anita Chawla',
        currentRole: 'Senior PM · SaaS Infrastructure',
        experience: '9 yrs · Ex-Atlassian',
        score: 88,
        strengths: [
          'Partnered with data science to ship intelligent SLA routing',
          'Scaled agile cadence across 7 squads post-merger'
        ],
        notes: 'Excellent behavioural interview signals, ready for panel within a week.'
      }
    ]
  },
  'ml-engineer': {
    jobId: 'ml-engineer',
    jobTitle: 'Machine Learning Engineer',
    department: 'Data & Intelligence · Recommendations',
    location: 'Hybrid · Tel Aviv',
    summary:
      'Candidate pool optimised for real-time recommendations and ranking systems. Benchmarked profiles excel in productionising models with MLOps maturity.',
    highlights: [
      'Hands-on experience with low-latency inference pipelines',
      'Documented ownership of experimentation frameworks',
      'Consistent contribution to knowledge-sharing and mentoring'
    ],
    metrics: {
      suitability: 89,
      cultureAdd: 85,
      velocity: 81
    },
    pipeline: [
      { label: 'Sourcing', count: 54, trend: 'up' },
      { label: 'Screened', count: 26, trend: 'up' },
      { label: 'Interview', count: 11, trend: 'up' },
      { label: 'Offer', count: 3, trend: 'steady' }
    ],
    skillFocus: [
      { skill: 'Ranking Models', percentage: 29 },
      { skill: 'Feature Stores', percentage: 22 },
      { skill: 'MLOps', percentage: 19 },
      { skill: 'Experimentation', percentage: 17 },
      { skill: 'Leadership', percentage: 13 }
    ],
    recommendedCandidates: [
      {
        id: 'ml-01',
        name: 'Yael Mor',
        currentRole: 'Staff ML Engineer · Streamly',
        experience: '9 yrs · Ex-Google Research',
        score: 95,
        strengths: [
          'Reduced inference latency by 37% with distillation pipeline',
          'Productionised multi-armed bandit experimentation layer'
        ],
        notes: 'Mentors ML Ops guild, very strong communication. Available for onsite in 10 days.'
      },
      {
        id: 'ml-02',
        name: 'Noah Feld',
        currentRole: 'Senior Applied Scientist · ShopNext',
        experience: '8 yrs · Ex-Microsoft',
        score: 91,
        strengths: [
          'Shipped session-based ranking improving CTR by 14%',
          'Instrumented automated regression checks for drift'
        ],
        notes: 'Prefers hybrid schedule, exceptional peer feedback on pairing sessions.'
      },
      {
        id: 'ml-03',
        name: 'Ines Vidal',
        currentRole: 'Machine Learning Lead · InsightIQ',
        experience: '11 yrs · Ex-Spotify',
        score: 87,
        strengths: [
          'Built feature store governance with 0 production incidents',
          'Drove experimentation council to bi-weekly cadence'
        ],
        notes: 'Excels at storytelling with product partners, recommended for leadership interview loop.'
      }
    ]
  },
  'talent-partner': {
    jobId: 'talent-partner',
    jobTitle: 'Senior Talent Partner',
    department: 'People · GTM',
    location: 'Hybrid · Tel Aviv',
    summary:
      'Talent partner bench prioritises proactive sourcing and advisory experience. Candidate signals emphasise bias-aware hiring rituals and talent brand elevation.',
    highlights: [
      'Blend of strategic advisory and hands-on recruiting execution',
      'Momentum in building inclusive hiring frameworks across orgs',
      'Strong calibration history with senior leadership stakeholders'
    ],
    metrics: {
      suitability: 86,
      cultureAdd: 93,
      velocity: 74
    },
    pipeline: [
      { label: 'Sourcing', count: 29, trend: 'steady' },
      { label: 'Screened', count: 14, trend: 'up' },
      { label: 'Interview', count: 6, trend: 'steady' },
      { label: 'Offer', count: 1, trend: 'up' }
    ],
    skillFocus: [
      { skill: 'Executive Hiring', percentage: 27 },
      { skill: 'Inclusive Frameworks', percentage: 24 },
      { skill: 'Stakeholder Coaching', percentage: 23 },
      { skill: 'Pipeline Analytics', percentage: 15 },
      { skill: 'Employer Branding', percentage: 11 }
    ],
    recommendedCandidates: [
      {
        id: 'tp-01',
        name: 'Adi Klein',
        currentRole: 'Lead Talent Partner · GrowthLabs',
        experience: '10 yrs · Ex-Monday.com',
        score: 94,
        strengths: [
          'Rolled out inclusive hiring playbook cutting time-to-fill by 22%',
          'Coached GTM leadership through three high-volume ramps'
        ],
        notes: 'Trusted advisor profile, excellent executive presence, ready for stakeholder loop next week.'
      },
      {
        id: 'tp-02',
        name: 'Maya Dror',
        currentRole: 'Senior Recruiter · NovaScale',
        experience: '8 yrs · Ex-Google',
        score: 89,
        strengths: [
          'Built analytics layer forecasting pipeline health weekly',
          'Scaled talent brand program that doubled inbound leads'
        ],
        notes: 'Operates with high autonomy, recommended to pair with new GTM leadership team.'
      },
      {
        id: 'tp-03',
        name: 'Isaac Romero',
        currentRole: 'Principal Recruiter · CloudSignal',
        experience: '11 yrs · Ex-Salesforce',
        score: 86,
        strengths: [
          'Designed bias-aware interview kits adopted company-wide',
          'Maintains strong passive talent community partnerships'
        ],
        notes: 'Calm under pressure, strong facilitator for panel debriefs.'
      }
    ]
  }
}
