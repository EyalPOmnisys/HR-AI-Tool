import styles from './JobDetailsModal.module.css'
import type { MouseEvent, ReactElement } from 'react'
import type { Job } from '../../../types/job'

type JobDetailsModalProps = {
  open: boolean
  job: Job | null
  onClose: () => void
  onEdit: (job: Job) => void
  onDelete: (jobId: string) => void
}

const CloseIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path
      d="M6 6l12 12M18 6 6 18"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
  </svg>
)

const formatDate = (value: string): string => {
  const date = new Date(value)
  return date.toLocaleDateString('en-US', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

export const JobDetailsModal = ({ open, job, onClose, onEdit, onDelete }: JobDetailsModalProps): ReactElement | null => {
  if (!open || !job) {
    return null
  }

  const handleBackdropClick = () => {
    onClose()
  }

  const handleContentClick = (event: MouseEvent<HTMLDivElement>) => {
    event.stopPropagation()
  }

  const handleEdit = () => {
    onEdit(job)
    onClose()
  }

  const handleDelete = () => {
    onDelete(job.id)
    onClose()
  }

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" onClick={handleBackdropClick}>
      <div className={styles.modal} onClick={handleContentClick}>
        <header className={styles.header}>
          <div className={styles.jobHeader}>
            <div className={styles.iconWrapper} aria-hidden>
              <span>{job.icon}</span>
            </div>
            <div>
              <h2>{job.title}</h2>
              <p className={styles.meta}>Posted on {formatDate(job.postedAt)}</p>
            </div>
          </div>
          <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close dialog">
            <CloseIcon />
          </button>
        </header>

        <div className={styles.body}>
          <section className={styles.section}>
            <h3>Description</h3>
            <p>{job.description}</p>
          </section>
          {job.freeText && (
            <section className={styles.section}>
              <h3>Candidate message</h3>
              <p>{job.freeText}</p>
            </section>
          )}
        </div>

        <footer className={styles.footer}>
          <button type="button" className={styles.secondary} onClick={handleDelete}>
            Delete
          </button>
          <button type="button" className={styles.primary} onClick={handleEdit}>
            Edit job
          </button>
        </footer>
      </div>
    </div>
  )
}
