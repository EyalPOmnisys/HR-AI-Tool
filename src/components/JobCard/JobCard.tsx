import styles from './JobCard.module.css'
import type { KeyboardEvent, MouseEvent } from 'react'
import type { Job } from '../../types/job'

type JobCardProps = {
  job: Job
  onEdit: (job: Job) => void
  onDelete: (jobId: string) => void
  onOpen: (job: Job) => void
}

const EditIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path
      d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    />
    <path
      d="M14.06 6.19l2.12-2.12a1.5 1.5 0 0 1 2.12 0l1.63 1.63a1.5 1.5 0 0 1 0 2.12l-2.12 2.12"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const DeleteIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path
      d="M5 7h14"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
    <path
      d="M10 3h4a1 1 0 0 1 1 1v2H9V4a1 1 0 0 1 1-1z"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M18 7v11a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
)

export const JobCard = ({ job, onEdit, onDelete, onOpen }: JobCardProps) => {
  const handleOpen = () => {
    onOpen(job)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onOpen(job)
    }
  }

  const handleEdit = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    onEdit(job)
  }

  const handleDelete = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    onDelete(job.id)
  }

  return (
    <article
      className={styles.card}
      role="button"
      tabIndex={0}
      onClick={handleOpen}
      onKeyDown={handleKeyDown}
    >
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <div className={styles.iconWrapper} aria-hidden>
            <span>{job.icon}</span>
          </div>
          <h3 className={styles.title} title={job.title}>
            {job.title}
          </h3>
        </div>
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.actionButton}
            onClick={handleEdit}
            aria-label="Edit job"
          >
            <EditIcon />
          </button>
          <button
            type="button"
            className={styles.actionButton}
            onClick={handleDelete}
            aria-label="Delete job"
          >
            <DeleteIcon />
          </button>
        </div>
      </header>
      <div className={styles.body}>
        <p className={styles.description} title={job.description}>
          {job.description}
        </p>
        {job.freeText && (
          <p className={styles.candidateMessage} title={job.freeText}>
            {job.freeText}
          </p>
        )}
      </div>
    </article>
  )
}
