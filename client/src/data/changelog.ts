// Single source of truth for the app version and the "What's New" list
// shown in the About modal. Update this file on every release.

export type ChangelogEntry = {
  version: string
  date: string
  highlights: string[]
}

export const APP_VERSION = '1.2.0'

export const CHANGELOG: readonly ChangelogEntry[] = [
  {
    version: '1.2.0',
    date: 'July 2026',
    highlights: [
      'AI engine upgraded to Gemma 4 — resume analysis is 4-5x faster',
      'Smarter match scoring: concrete technologies and soft requirements are now evaluated separately',
      'Experience beyond the requirement is treated as an asset — senior candidates are no longer penalized',
      'More resilient resume ingestion — malformed AI output no longer fails whole files',
      'Leaner backend: legacy vector-search (RAG) layer removed',
    ],
  },
  {
    version: '1.1.0',
    date: 'June 2026',
    highlights: [
      'Smart Backfill matching: the AI judge reviews candidates until enough strong matches are found',
      'Job board with AI-analyzed requirements (must-have vs nice-to-have)',
      'Automatic resume ingestion with Hebrew support',
    ],
  },
]
