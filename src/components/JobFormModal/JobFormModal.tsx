import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { Job, JobDraft } from '../../types/job'
import styles from './JobFormModal.module.css'

type JobFormModalProps = {
  open: boolean
  mode: 'create' | 'edit'
  job?: Job | null
  onCancel: () => void
  onSubmit: (draft: JobDraft) => void
}

const iconOptions = ['💼', '🧑\u200d💻', '🧠', '📈', '🎯', '🛠️', '📣', '🤝', '⚡', '🚀']

export const JobFormModal = ({ open, mode, job, onCancel, onSubmit }: JobFormModalProps) => {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [freeText, setFreeText] = useState('')
  const [icon, setIcon] = useState(iconOptions[0])

  useEffect(() => {
    if (job) {
      setTitle(job.title)
      setDescription(job.description)
      setFreeText(job.freeText)
      setIcon(job.icon)
    } else {
      setTitle('')
      setDescription('')
      setFreeText('')
      setIcon(iconOptions[0])
    }
  }, [job])

  if (!open) {
    return null
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSubmit({ title, description, freeText, icon })
  }

  const isValid = title.trim().length > 0 && description.trim().length > 0

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true">
      <form className={styles.modal} onSubmit={handleSubmit}>
        <header className={styles.header}>
          <div>
            <h2>{mode === 'create' ? 'Create a new job' : 'Update job details'}</h2>
            <p>Complete the details so candidates know exactly what you are offering.</p>
          </div>
          <button type="button" className={styles.closeButton} onClick={onCancel} aria-label="Close dialog">
            ✕
          </button>
        </header>

        <div className={styles.fieldGroup}>
          <label>
            Job title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Example: Senior Product Manager"
              required
            />
          </label>
          <label>
            Short description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What is the core mission for this role?"
              rows={3}
              required
            />
          </label>
          <label>
            Candidate message
            <textarea
              value={freeText}
              onChange={(event) => setFreeText(event.target.value)}
              placeholder="What impression should candidates leave with?"
              rows={3}
            />
          </label>
        </div>

        <div className={styles.iconPicker}>
          <span className={styles.iconLabel}>Choose an icon that reflects the role</span>
          <div className={styles.iconGrid}>
            {iconOptions.map((option) => (
              <button
                type="button"
                key={option}
                className={`${styles.iconButton} ${option === icon ? styles.iconSelected : ''}`}
                onClick={() => setIcon(option)}
                aria-pressed={option === icon}
              >
                {option}
              </button>
            ))}
          </div>
        </div>

        <footer className={styles.footer}>
          <button type="button" className={styles.secondary} onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className={styles.primary} disabled={!isValid}>
            {mode === 'create' ? 'Publish job' : 'Save changes'}
          </button>
        </footer>
      </form>
    </div>
  )
}
