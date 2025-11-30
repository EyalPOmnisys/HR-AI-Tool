import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type ReactElement } from 'react'
import { FaRegFolderOpen } from 'react-icons/fa'

import { SearchInput } from '../../components/common/SearchInput'
import { ResumeDetailPanel } from '../../components/Resume/ResumeDetail'
import { ResumeCard } from '../../components/Resume/ResumeCard/ResumeCard'
import { ResumeFilters, type FilterState } from '../../components/Resume/ResumeFilters/ResumeFilters'
import { getResumeDetail, listResumes } from '../../services/resumes'
import type { ResumeDetail, ResumeSummary } from '../../types/resume'
import styles from './Resumes.module.css'

export const Resumes = (): ReactElement => {
  const [resumes, setResumes] = useState<(ResumeSummary & { searchableText?: string })[]>([])
  const [query, setQuery] = useState<string>('')
  const [filters, setFilters] = useState<FilterState>({
    profession: '',
    minExperience: '',
    maxExperience: '',
    skills: [],
    freeText: ''
  })
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
        if (!isMounted) return

        setResumes(response.items)
        setError(null)
        setIsLoading(false)

        // Fetch details for all resumes to populate skills, summary, and searchable text
        const detailPromises = response.items.map(async (item) => {
          try {
            const detail = await getResumeDetail(item.id)

            const experienceText = detail.experience
              .map((e) =>
                [e.company, e.title, e.location, ...(e.bullets || []), ...(e.tech || [])]
                  .filter(Boolean)
                  .join(' ')
              )
              .join(' ')

            const educationText = detail.education
              .map((e) => [e.institution, e.degree, e.field].filter(Boolean).join(' '))
              .join(' ')

            const searchableText = [
              detail.summary,
              experienceText,
              educationText,
              detail.contacts.map((c) => c.value).join(' '),
            ]
              .filter(Boolean)
              .join(' ')
              .toLowerCase()

            return {
              id: item.id,
              skills: detail.skills.map((s) => s.name),
              summary: detail.summary,
              searchableText,
            }
          } catch {
            return null
          }
        })

        const details = await Promise.all(detailPromises)

        if (isMounted) {
          setResumes((prev) =>
            prev.map((r) => {
              const d = details.find((det) => det?.id === r.id)
              return d
                ? {
                    ...r,
                    skills: d.skills,
                    summary: d.summary,
                    searchableText: d.searchableText,
                  }
                : r
            })
          )
        }
      } catch (err) {
        if (isMounted) {
          const message = err instanceof Error ? err.message : 'Failed to load resumes'
          setError(message)
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
    let result = resumes

    if (query.trim()) {
      const normalized = query.trim().toLowerCase()
      result = result.filter((resume) => {
        const nameMatch = resume.name?.toLowerCase().includes(normalized)
        const professionMatch = resume.profession?.toLowerCase().includes(normalized)
        return Boolean(nameMatch || professionMatch)
      })
    }

    if (filters.profession) {
      const normProf = filters.profession.toLowerCase()
      result = result.filter(r => r.profession?.toLowerCase().includes(normProf))
    }

    if (filters.minExperience) {
      const min = parseFloat(filters.minExperience)
      if (!isNaN(min)) {
        result = result.filter(r => (r.yearsOfExperience ?? 0) >= min)
      }
    }

    if (filters.maxExperience) {
      const max = parseFloat(filters.maxExperience)
      if (!isNaN(max)) {
        result = result.filter(r => (r.yearsOfExperience ?? 0) <= max)
      }
    }

    if (filters.skills.length > 0) {
      result = result.filter(r => {
        if (!r.skills || r.skills.length === 0) return false
        const resumeSkills = r.skills.map(s => s.toLowerCase())
        // Match if resume has ALL selected skills (AND logic)
        return filters.skills.every(filterSkill => 
          resumeSkills.some(rs => rs.includes(filterSkill.toLowerCase()))
        )
      })
    }

    if (filters.freeText) {
      const text = filters.freeText.toLowerCase()
      result = result.filter((r) => {
        const inSummary = r.summary?.toLowerCase().includes(text)
        const inName = r.name?.toLowerCase().includes(text)
        const inProfession = r.profession?.toLowerCase().includes(text)
        const inSkills = r.skills?.some((s) => s.toLowerCase().includes(text))
        const inSearchable = r.searchableText?.includes(text)
        return Boolean(inSummary || inName || inProfession || inSkills || inSearchable)
      })
    }

    return result
  }, [resumes, query, filters])

  const listContent = useMemo(() => {
    if (isLoading) {
      return <p className={styles.status}>Loading resumes...</p>
    }
    if (error) {
      return <p className={`${styles.status} ${styles.error}`}>{error}</p>
    }
    if (resumes.length === 0) {
      return (
        <div className={styles.emptyState}>
          <FaRegFolderOpen className={styles.emptyIcon} />
          <h3 className={styles.emptyTitle}>No resumes yet</h3>
          <p className={styles.emptyText}>Upload resumes to see them here</p>
        </div>
      )
    }
    if (filteredResumes.length === 0) {
      return <p className={styles.status}>No resumes found matching your search.</p>
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
        <ResumeFilters onFilterChange={setFilters} initialFilters={filters} />
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
