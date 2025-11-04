import { useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { JobCard } from '../../components/job/JobCard/JobCard'
import { JobDetailsModal } from '../../components/job/JobDetailsModal/JobDetailsModal'
import { JobFormModal } from '../../components/job/JobFormModal/JobFormModal'
import type { Job, JobDraft } from '../../types/job'
import styles from './JobBoard.module.css'
import { createJob } from '../../services/jobs'   // ← NEW
import type { ApiJob } from '../../services/jobs' // ← NEW

const generateId = (): string =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2)

const createInitialJobs = (): Job[] => [] // start empty; data now comes from API on create

// Mapper: ApiJob → UI Job
const mapApiToUi = (api: ApiJob): Job => ({
  id: api.id,
  title: api.title,
  description: api.job_description,
  freeText: api.free_text ?? '',
  icon: api.icon ?? '👥',
  postedAt: api.created_at,
})

export const JobBoard = (): ReactElement => {
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

  const handleSubmit = async (draft: JobDraft) => {
    if (modalMode === 'create') {
      // send to backend: map UI fields → API payload
      const payload = {
        title: draft.title,
        job_description: draft.description,
        free_text: draft.freeText,
        icon: draft.icon,
        status: 'draft',
      }
      const created = await createJob(payload)
      const ui = mapApiToUi(created)
      setJobs((prev) => [ui, ...prev])
    } else if (editingJobId) {
      // for now keep local edit; later we’ll wire PUT /jobs/{id}
      setJobs((prev) =>
        prev.map((job) =>
          job.id === editingJobId
            ? { ...job, ...draft }
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
            <div className={styles.emptyIcon}>👥</div>
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
