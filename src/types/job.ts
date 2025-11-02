export interface Job {
  id: string
  title: string
  description: string
  freeText: string
  icon: string
  postedAt: string
}

export type JobDraft = Omit<Job, 'id' | 'postedAt'>
