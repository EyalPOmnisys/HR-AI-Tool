import { useEffect, useMemo, useState, useRef } from 'react'
import type { ReactElement, ChangeEvent } from 'react'
import { JobCard } from '../../components/job/JobCard/JobCard'
import { JobDetailsModal } from '../../components/job/JobDetailsModal/JobDetailsModal'
import { JobFormModal } from '../../components/job/JobFormModal/JobFormModal'
import { SearchInput } from '../../components/common/SearchInput/SearchInput'
import type { Job, JobDraft } from '../../types/job'
import styles from './JobBoard.module.css'
import { createJob, listJobs, updateJob, deleteJob as deleteJobApi, getJob } from '../../services/jobs'
import type { ApiJob } from '../../types/job'

// Mapper: ApiJob → UI Job
const mapApiToUi = (api: ApiJob): Job => ({
  id: api.id,
  title: api.title,
  description: api.job_description,
  freeText: api.free_text ?? '',
  icon: api.icon ?? '👥',
  postedAt: api.created_at,
  analysis: api.analysis_json,
})

export const JobBoard = (): ReactElement => {
  const [jobs, setJobs] = useState<Job[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
  const [editingJobId, setEditingJobId] = useState<string | null>(null)
  const [detailsJobId, setDetailsJobId] = useState<string | null>(null)
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // simple in-flight polling refs to avoid multiple intervals
  const pollingMapRef = useRef<Record<string, number>>({})

  useEffect(() => {
    const loadJobs = async () => {
      try {
        setIsLoading(true)
        const response = await listJobs()
        const uiJobs = response.items.map(mapApiToUi)
        setJobs(uiJobs)
      } catch (error) {
        console.error('Failed to load jobs:', error)
      } finally {
        setIsLoading(false)
      }
    }
    loadJobs()
  }, [])

  const editingJob = useMemo(
    () => jobs.find((job) => job.id === editingJobId) ?? null,
    [jobs, editingJobId]
  )

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === detailsJobId) ?? null,
    [jobs, detailsJobId]
  )

  const filteredJobs = useMemo(() => {
    if (!searchQuery.trim()) return jobs
    const query = searchQuery.toLowerCase()
    return jobs.filter(
      (job) =>
        job.title.toLowerCase().includes(query) ||
        job.description.toLowerCase().includes(query) ||
        job.freeText.toLowerCase().includes(query)
    )
  }, [jobs, searchQuery])

  const handleSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value)
  }

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

  const handleDelete = async (jobId: string) => {
    try {
      await deleteJobApi(jobId)
      setJobs((prev) => prev.filter((job) => job.id !== jobId))
      if (detailsJobId === jobId) {
        handleCloseDetails()
      }
    } catch (error) {
      console.error('Failed to delete job:', error)
      alert('Failed to delete job. Please try again.')
    }
  }

  // Poll for analysis_json (lightweight, 3s intervals, up to 30s)
  const startAnalysisPolling = (jobId: string) => {
    if (pollingMapRef.current[jobId]) return
    let elapsed = 0
    const intervalId = window.setInterval(async () => {
      try {
        const api = await getJob(jobId)
        if (api.analysis_json) {
          setJobs((prev) =>
            prev.map((j) => (j.id === jobId ? mapApiToUi(api) : j))
          )
          clearInterval(intervalId)
          delete pollingMapRef.current[jobId]
        } else {
          elapsed += 3000
          if (elapsed >= 30000) {
            clearInterval(intervalId)
            delete pollingMapRef.current[jobId]
          }
        }
      } catch {
        clearInterval(intervalId)
        delete pollingMapRef.current[jobId]
      }
    }, 3000)
    pollingMapRef.current[jobId] = intervalId
  }

  const handleSubmit = async (draft: JobDraft) => {
    try {
      if (modalMode === 'create') {
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
        startAnalysisPolling(ui.id)
      } else if (editingJobId) {
        const payload = {
          title: draft.title,
          job_description: draft.description,
          free_text: draft.freeText,
          icon: draft.icon,
        }
        const updated = await updateJob(editingJobId, payload)
        const ui = mapApiToUi(updated)
        setJobs((prev) => prev.map((job) => (job.id === editingJobId ? ui : job)))
        startAnalysisPolling(ui.id)
      }
      setIsModalOpen(false)
    } catch (error) {
      console.error('Failed to save job:', error)
      alert('Failed to save job. Please try again.')
    }
  }

  useEffect(() => {
    return () => {
      // cleanup polling intervals on unmount
      Object.values(pollingMapRef.current).forEach((id) => clearInterval(id))
      pollingMapRef.current = {}
    }
  }, [])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Job Board</h1>
        <SearchInput
          value={searchQuery}
          onChange={handleSearchChange}
          placeholder="Search jobs..."
        />
        <button type="button" className={styles.createButton} onClick={handleCreateClick}>
          Create New Job
        </button>
      </header>

      <section className={styles.board}>
        {isLoading ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>⏳</div>
            <h3>Loading jobs...</h3>
          </div>
        ) : jobs.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>👥</div>
            <h3>Let&apos;s get started!</h3>
            <p>Create your first job and let our matching engine start working for you.</p>
            <button type="button" className={styles.emptyButton} onClick={handleCreateClick}>
              Create first job
            </button>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>🔍</div>
            <h3>No jobs found</h3>
            <p>Try adjusting your search query.</p>
          </div>
        ) : (
          <div className={styles.grid}>
            {filteredJobs.map((job) => (
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
