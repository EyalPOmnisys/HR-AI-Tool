import { useMemo, useState } from 'react'
import { JobCard } from '../../components/JobCard/JobCard'
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
    description: 'ניתוח נתוני גיוס, בניית מודלים וחיזוי מועמדים עם פוטנציאל גבוה.',
    freeText: 'אנחנו מחפשים מישהי\u200f/ו עם תשוקה לאנשים ולדאטה, שיוכל לחבר מספרים לסיפור אנושי.',
    icon: '🧠',
    postedAt: new Date().toISOString()
  },
  {
    id: generateId(),
    title: 'Talent Acquisition Lead',
    description: 'הובלת אסטרטגיית הגיוס הגלובלית ועבודה צמודה עם מנהלים בכירים.',
    freeText: 'אם יש לכם יכולת לראות את הבן אדם מאחורי קורות החיים – אנחנו רוצים אתכם איתנו.',
    icon: '🤝',
    postedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 6).toISOString()
  }
]

export const JobBoard = () => {
  const [jobs, setJobs] = useState<Job[]>(() => createInitialJobs())
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
  const [editingJobId, setEditingJobId] = useState<string | null>(null)

  const editingJob = useMemo(
    () => jobs.find((job) => job.id === editingJobId) ?? null,
    [jobs, editingJobId]
  )

  const handleCreateClick = () => {
    setModalMode('create')
    setEditingJobId(null)
    setIsModalOpen(true)
  }

  const handleEditClick = (job: Job) => {
    setModalMode('edit')
    setEditingJobId(job.id)
    setIsModalOpen(true)
  }

  const handleDelete = (jobId: string) => {
    setJobs((prev) => prev.filter((job) => job.id !== jobId))
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
                ...draft,
                postedAt: job.postedAt
              }
            : job
        )
      )
    }

    setIsModalOpen(false)
  }

  const headline = jobs.length ? 'המשרות הפעילות שלכם' : 'אין עדיין משרות פעילות'

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div>
          <p className={styles.tag}>AI Recruitment Hub</p>
          <h1>ניהול משרות חכם ומהיר לצוות ה-HR</h1>
          <p className={styles.subtitle}>
            צרו, עדכנו והציגו משרות בלחיצת כפתור אחת. המערכת שלנו יודעת לחבר בין הצורך העסקי לבין
            המועמד\u200f/ת המדויקים ביותר.
          </p>
        </div>
        <button type="button" className={styles.createButton} onClick={handleCreateClick}>
          + יצירת משרה חדשה
        </button>
      </section>

      <section className={styles.board}>
        <header className={styles.boardHeader}>
          <h2>{headline}</h2>
          <span className={styles.counter}>{jobs.length} משרות</span>
        </header>

        {jobs.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>✨</div>
            <h3>בואו נתחיל!</h3>
            <p>צרו את המשרה הראשונה שלכם ותנו לאלגוריתם שלנו להתחיל לעבוד בשבילכם.</p>
            <button type="button" className={styles.emptyButton} onClick={handleCreateClick}>
              יצירת משרה ראשונה
            </button>
          </div>
        ) : (
          <div className={styles.grid}>
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} onEdit={handleEditClick} onDelete={handleDelete} />
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
    </div>
  )
}
