import { useEffect, useState } from 'react'
import type { FormEvent, MouseEvent, ReactElement } from 'react'
import type { Job, JobDraft } from '../../../types/job'
import styles from './JobFormModal.module.css'

type JobFormModalProps = {
  open: boolean
  mode: 'create' | 'edit'
  job?: Job | null
  onCancel: () => void
  onSubmit: (draft: JobDraft) => void
}

const iconOptions = [
  '👥',
  '🧠',
  '💼',
  '🛠️',
  '📊',
  '🤝',
  '🚀',
  '🔍',
  '💡',
  '🛡️',
  '💻',
  '🎯',
  '📁',
  '🌐'
]

const CloseIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
)

export const JobFormModal = ({ open, mode, job, onCancel, onSubmit }: JobFormModalProps): ReactElement | null => {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [freeText, setFreeText] = useState('')
  const [icon, setIcon] = useState(iconOptions[0])
  const [additionalSkills, setAdditionalSkills] = useState<string[]>([])
  const [currentSkill, setCurrentSkill] = useState('')

  useEffect(() => {
    if (job) {
      setTitle(job.title)
      setDescription(job.description)
      setFreeText(job.freeText)
      const jobIcon = job.icon && iconOptions.includes(job.icon) ? job.icon : iconOptions[0]
      setIcon(jobIcon)
      setAdditionalSkills(job.additionalSkills || [])
    } else {
      setTitle('')
      setDescription('')
      setFreeText('')
      setIcon(iconOptions[0])
      setAdditionalSkills([])
    }
    setCurrentSkill('')
  }, [job])

  if (!open) {
    return null
  }

  const handleBackdropInteraction = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      onCancel()
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSubmit({ title, description, freeText, icon, additionalSkills })
  }

  const handleAddSkill = () => {
    const trimmedSkill = currentSkill.trim()
    if (trimmedSkill && !additionalSkills.includes(trimmedSkill)) {
      setAdditionalSkills([...additionalSkills, trimmedSkill])
      setCurrentSkill('')
    }
  }

  const handleRemoveSkill = (skillToRemove: string) => {
    setAdditionalSkills(additionalSkills.filter(skill => skill !== skillToRemove))
  }

  const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      handleAddSkill()
    }
  }

  const isValid = title.trim().length > 0 && description.trim().length > 0

  return (
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      onMouseDown={handleBackdropInteraction}
      onClick={handleBackdropInteraction}
    >
      <form className={styles.modal} onSubmit={handleSubmit}>
        <header className={styles.header}>
          <div>
            <h2>{mode === 'create' ? 'Create a new job' : 'Update job details'}</h2>
            <p>Complete the details so candidates know exactly what you are offering.</p>
          </div>
          <button type="button" className={styles.closeButton} onClick={onCancel} aria-label="Close dialog">
            <CloseIcon />
          </button>
        </header>

        <div className={styles.body}>
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
            <label>
              Additional Skills
              <span style={{ fontSize: '0.85rem', color: '#64748b', marginLeft: '0.5rem' }}>Add specific skills the AI might not identify</span>
              <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                <input
                  value={currentSkill}
                  onChange={(event) => setCurrentSkill(event.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="e.g., Python, Leadership, etc."
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  onClick={handleAddSkill}
                  disabled={!currentSkill.trim()}
                  style={{
                    padding: '0 16px',
                    background: currentSkill.trim() ? '#3b82f6' : '#d1d5db',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: currentSkill.trim() ? 'pointer' : 'not-allowed',
                    fontWeight: 500
                  }}
                >
                  Add
                </button>
              </div>
              {additionalSkills.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
                  {additionalSkills.map((skill) => (
                    <span
                      key={skill}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        background: '#f0f9ff',
                        border: '1px solid #bfdbfe',
                        borderRadius: '999px',
                        fontSize: '0.875rem',
                        color: '#1e40af'
                      }}
                    >
                      {skill}
                      <button
                        type="button"
                        onClick={() => handleRemoveSkill(skill)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          padding: '0',
                          display: 'flex',
                          alignItems: 'center',
                          color: '#1e40af',
                          fontSize: '1.1rem',
                          lineHeight: 1
                        }}
                        aria-label={`Remove ${skill}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
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
