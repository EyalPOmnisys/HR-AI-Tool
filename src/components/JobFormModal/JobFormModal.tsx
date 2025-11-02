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
            <h2>{mode === 'create' ? 'יצירת משרה חדשה' : 'עדכון משרה קיימת'}</h2>
            <p>השלימו את הפרטים כדי שנוכל להציג למועמדים בדיוק את מה שאתם מחפשים.</p>
          </div>
          <button type="button" className={styles.closeButton} onClick={onCancel} aria-label="סגירת החלון">
            ✕
          </button>
        </header>

        <div className={styles.fieldGroup}>
          <label>
            שם המשרה
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="לדוגמה: מנהל\u200f/ת מוצר בכיר\u200f/ה"
              required
            />
          </label>
          <label>
            תיאור קצר
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="מהי המשימה העיקרית של המשרה הזו?"
              rows={3}
              required
            />
          </label>
          <label>
            טקסט חופשי למועמדים
            <textarea
              value={freeText}
              onChange={(event) => setFreeText(event.target.value)}
              placeholder="איזה מסר תרצו שהמועמד\u200f/ת יקחו איתם?"
              rows={3}
            />
          </label>
        </div>

        <div className={styles.iconPicker}>
          <span className={styles.iconLabel}>בחרו אייקון שיספר את הסיפור של המשרה</span>
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
            ביטול
          </button>
          <button type="submit" className={styles.primary} disabled={!isValid}>
            {mode === 'create' ? 'פרסום המשרה' : 'שמירת שינויים'}
          </button>
        </footer>
      </form>
    </div>
  )
}
