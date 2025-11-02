import type { Job } from '../../types/job'
import styles from './JobCard.module.css'

type JobCardProps = {
  job: Job
  onEdit: (job: Job) => void
  onDelete: (jobId: string) => void
}

const formatDate = (value: string) => {
  const date = new Date(value)
  return date.toLocaleDateString('en-US', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

const getStatusBadge = (value: string) => {
  const now = new Date()
  const posted = new Date(value)
  const diffInDays = (now.getTime() - posted.getTime()) / (1000 * 60 * 60 * 24)

  if (diffInDays < 1) {
    return { label: 'New', variant: 'new' as const }
  }

  if (diffInDays < 5) {
    return { label: 'Updated', variant: 'updated' as const }
  }

  return { label: 'Active', variant: 'active' as const }
}

export const JobCard = ({ job, onEdit, onDelete }: JobCardProps) => {
  const status = getStatusBadge(job.postedAt)

  return (
    <article className={styles.card}>
      <div className={styles.iconWrapper} aria-hidden>
        <span>{job.icon}</span>
      </div>

      <div className={styles.content}>
        <header className={styles.header}>
          <div className={styles.headerText}>
            <div className={styles.metaRow}>
              <span className={`${styles.status} ${styles[`status-${status.variant}`]}`}>{status.label}</span>
              <span className={styles.meta}>Posted on {formatDate(job.postedAt)}</span>
            </div>
            <h3 className={styles.title} title={job.title}>
              {job.title}
            </h3>
          </div>
          <div className={styles.actions}>
            <button type="button" className={styles.actionButton} onClick={() => onEdit(job)}>
              Edit
            </button>
            <button
              type="button"
              className={`${styles.actionButton} ${styles.delete}`}
              onClick={() => onDelete(job.id)}
            >
              Delete
            </button>
          </div>
        </header>

        <p className={styles.description} title={job.description}>
          {job.description}
        </p>
        <div className={styles.freeText} title={job.freeText}>
          {job.freeText}
        </div>
      </div>
    </article>
  )
}
