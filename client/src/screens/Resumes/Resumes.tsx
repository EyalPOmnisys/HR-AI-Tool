import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type ReactElement } from 'react'

import { SearchInput } from '../../components/common/SearchInput'
import { ResumeDetailPanel } from '../../components/Resume/ResumeDetail'
import { ResumeCard } from '../../components/Resume/ResumeCard/ResumeCard'
import { getResumeDetail, listResumes } from '../../services/resumes'
import type { ResumeDetail, ResumeSummary } from '../../types/resume'
import styles from './Resumes.module.css'

export const Resumes = (): ReactElement => {
  const [resumes, setResumes] = useState<ResumeSummary[]>([])
  const [query, setQuery] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null)
  const [selectedResume, setSelectedResume] = useState<ResumeDetail | null>(null)
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailReloadKey, setDetailReloadKey] = useState<number>(0)

  useEffect(() => {
    let isMounted = true

    const fetchResumes = async () => {
      setIsLoading(true)
      try {
        const response = await listResumes(0, 100)
        if (isMounted) {
          setResumes(response.items)
          setError(null)
        }
      } catch (err) {
        if (isMounted) {
          const message = err instanceof Error ? err.message : 'Failed to load resumes'
          setError(message)
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    fetchResumes()

    return () => {
      isMounted = false
    }
  }, [])

  const handleSearchChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    setQuery(event.target.value)
  }, [])

  const handleSelectResume = useCallback((resume: ResumeSummary) => {
    setSelectedResumeId((currentId) => (currentId === resume.id ? null : resume.id))
  }, [])

  const handleClosePanel = useCallback(() => {
    setSelectedResumeId(null)
    setSelectedResume(null)
    setDetailError(null)
    setIsDetailLoading(false)
  }, [])

  const handleRetryDetail = useCallback(() => {
    if (!selectedResumeId) return
    setDetailReloadKey((key) => key + 1)
  }, [selectedResumeId])

  useEffect(() => {
    if (!selectedResumeId) {
      setSelectedResume(null)
      setDetailError(null)
      setIsDetailLoading(false)
      return undefined
    }

    let isActive = true
    setIsDetailLoading(true)
    setDetailError(null)
    setSelectedResume(null)

    getResumeDetail(selectedResumeId)
      .then((detail) => {
        if (!isActive) return
        setSelectedResume(detail)
        setIsDetailLoading(false)
      })
      .catch((err) => {
        if (!isActive) return
        const message = err instanceof Error ? err.message : 'Failed to load resume'
        setDetailError(message)
        setIsDetailLoading(false)
      })

    return () => {
      isActive = false
    }
  }, [selectedResumeId, detailReloadKey])

  const filteredResumes = useMemo(() => {
    if (!query.trim()) {
      return resumes
    }
    const normalized = query.trim().toLowerCase()
    return resumes.filter((resume) => {
      const nameMatch = resume.name?.toLowerCase().includes(normalized)
      const professionMatch = resume.profession?.toLowerCase().includes(normalized)
      return Boolean(nameMatch || professionMatch)
    })
  }, [resumes, query])

  const listContent = useMemo(() => {
    if (isLoading) {
      return <p className={styles.status}>Loading resumes...</p>
    }
    if (error) {
      return <p className={`${styles.status} ${styles.error}`}>{error}</p>
    }
    if (filteredResumes.length === 0) {
      return <p className={styles.status}>No resumes found.</p>
    }

    return (
      <ul className={styles.list}>
        {filteredResumes.map((resume) => {
          const isActive = resume.id === selectedResumeId
          return (
            <li key={resume.id} className={isActive ? styles.selectedItem : undefined}>
              <ResumeCard resume={resume} onSelect={handleSelectResume} />
            </li>
          )
        })}
      </ul>
    )
  }, [filteredResumes, handleSelectResume, isLoading, error, selectedResumeId])

  const isPanelOpen = Boolean(selectedResumeId)

  return (
    <section className={styles.page} aria-labelledby="resumes-title">
      <header className={styles.header}>
        <h1 id="resumes-title" className={styles.title}>
          Resumes
        </h1>
        <SearchInput
          value={query}
          onChange={handleSearchChange}
          placeholder="Search by name or profession"
          className={styles.search}
          aria-label="Search resumes"
        />
      </header>

      <div className={`${styles.body} ${isPanelOpen ? styles.bodyWithPanel : ''}`}>
        <div className={styles.listWrapper}>{listContent}</div>
        {isPanelOpen && (
          <ResumeDetailPanel
            resume={selectedResume}
            isOpen={isPanelOpen}
            isLoading={isDetailLoading}
            error={detailError}
            onClose={handleClosePanel}
            onRetry={handleRetryDetail}
          />
        )}
      </div>
    </section>
  )
}
