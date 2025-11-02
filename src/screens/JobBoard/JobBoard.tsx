import { useMemo, useState } from 'react'
import { JobCard } from '../../components/JobCard/JobCard'
import { JobDetailsModal } from '../../components/JobDetailsModal/JobDetailsModal'
import { JobFormModal } from '../../components/JobFormModal/JobFormModal'
import type { Job, JobDraft } from '../../types/job'
import styles from './JobBoard.module.css'

const generateId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2)

const createInitialJobs = (): Job[] => [
  {
    id: generateId(),
    title: 'Data Scientist - HR Analytics',
    description:
      'Build recruiting analytics that reveal high-potential candidates and accelerate hiring outcomes.',
    freeText:
      'We are looking for someone who is equally passionate about people and data and can translate insights into action.',
    icon: '🧠',
    postedAt: new Date().toISOString()
  },
  {
    id: generateId(),
    title: 'Talent Acquisition Lead',
    description:
      'Shape the global hiring strategy and partner closely with senior leadership to deliver exceptional talent experiences.',
    freeText:
      'If you are able to spot the person beyond the resume, we would love to have you on our team.',
    icon: '🤝',
    postedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 6).toISOString()
  }
]

export const JobBoard = () => {
  const [jobs, setJobs] = useState<Job[]>(() => createInitialJobs())
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
  const [editingJobId, setEditingJobId] = useState<string | null>(null)
  const [detailsJobId, setDetailsJobId] = useState<string | null>(null)
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)

  const editingJob = useMemo(
    () => jobs.find((job) => job.id === editingJobId) ?? null,
    [jobs, editingJobId]
  )

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === detailsJobId) ?? null,
    [jobs, detailsJobId]
  )

  const handleCreateClick = () => {
    setModalMode('create')
    setEditingJobId(null)
    setIsModalOpen(true)
  }

  const handleCloseDetails = () => {
    setIsDetailsOpen(false)
    setDetailsJobId(null)
  }

  const handleEditClick = (job: Job) => {
    setModalMode('edit')
    setEditingJobId(job.id)
    setIsModalOpen(true)
    handleCloseDetails()
  }

  const handleCardOpen = (job: Job) => {
    setDetailsJobId(job.id)
    setIsDetailsOpen(true)
  }

  const handleDelete = (jobId: string) => {
    setJobs((prev) => prev.filter((job) => job.id !== jobId))
    if (detailsJobId === jobId) {
      handleCloseDetails()
    }
  }

  const handleSubmit = (draft: JobDraft) => {
    if (modalMode === 'create') {
      const newJob: Job = {
        id: generateId(),
        postedAt: new Date().toISOString(),
        ...draft
      }
      setJobs((prev) => [newJob, ...prev])
    } else if (editingJobId) {
      setJobs((prev) =>
        prev.map((job) =>
          job.id === editingJobId
            ? {
                ...job,
                ...draft
              }
            : job
        )
      )
    }

    setIsModalOpen(false)
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <button type="button" className={styles.createButton} onClick={handleCreateClick}>
          Create new job
        </button>
      </section>

      <section className={styles.board}>
        {jobs.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>📭</div>
            <h3>Let&apos;s get started!</h3>
            <p>Create your first job and let our matching engine start working for you.</p>
            <button type="button" className={styles.emptyButton} onClick={handleCreateClick}>
              Create first job
            </button>
          </div>
        ) : (
          <div className={styles.grid}>
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onEdit={handleEditClick}
                onDelete={handleDelete}
                onOpen={handleCardOpen}
              />
            ))}
          </div>
        )}
      </section>

      <JobFormModal
        open={isModalOpen}
        mode={modalMode}
        job={editingJob}
        onCancel={() => setIsModalOpen(false)}
        onSubmit={handleSubmit}
      />

      <JobDetailsModal
        open={isDetailsOpen}
        job={selectedJob}
        onClose={handleCloseDetails}
        onEdit={handleEditClick}
        onDelete={handleDelete}
      />
    </div>
  )
}
