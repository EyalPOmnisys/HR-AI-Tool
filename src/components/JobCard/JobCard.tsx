import type { Job } from '../../types/job'
import styles from './JobCard.module.css'

type JobCardProps = {
  job: Job
  onEdit: (job: Job) => void
  onDelete: (jobId: string) => void
}

const formatDate = (value: string) => {
  const date = new Date(value)
  return date.toLocaleDateString('he-IL', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

export const JobCard = ({ job, onEdit, onDelete }: JobCardProps) => {
  return (
    <article className={styles.card}>
      <div className={styles.iconWrapper} aria-hidden>
        <span>{job.icon}</span>
      </div>

      <div className={styles.content}>
        <header className={styles.header}>
          <div>
            <h3 className={styles.title}>{job.title}</h3>
            <p className={styles.meta}>פורסם ב־{formatDate(job.postedAt)}</p>
          </div>
          <div className={styles.actions}>
            <button type="button" className={styles.actionButton} onClick={() => onEdit(job)}>
              עדכון
            </button>
            <button
              type="button"
              className={`${styles.actionButton} ${styles.delete}`}
              onClick={() => onDelete(job.id)}
            >
              מחיקה
            </button>
          </div>
        </header>

        <p className={styles.description}>{job.description}</p>
        <div className={styles.freeText}>{job.freeText}</div>
      </div>
    </article>
  )
}
