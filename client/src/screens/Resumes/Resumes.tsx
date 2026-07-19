import { useCallback, useEffect, useMemo, useState, type ReactElement } from 'react'
import { FaRegFolderOpen, FaMagic, FaPaperPlane, FaSearch, FaBriefcase, FaChevronDown } from 'react-icons/fa'

import { ConfirmationModal } from '../../components/common/ConfirmationModal/ConfirmationModal'
import { ResumeDetailPanel } from '../../components/Resume/ResumeDetail'
import { ResumeFilters, type FilterState } from '../../components/Resume/ResumeFilters/ResumeFilters'
import { ResumeTable, type TimeFilter } from '../../components/Resume/ResumeTable/ResumeTable'
import { ResumeTableSkeleton } from '../../components/Resume/ResumeTable/ResumeTableSkeleton'
import { getResumeDetail, listResumes, deleteResume, analyzeSearchQuery, getResumesBulk, getRelatedTitles } from '../../services/resumes'
import { listJobs } from '../../services/jobs'
import type { ApiJob } from '../../types/job'
import type { ResumeDetail, ResumeSummary } from '../../types/resume'
import { deriveFiltersFromJob } from '../../utils/jobToFilters'
import styles from './Resumes.module.css'

// Split a filter chip into OR-alternatives. Supports "C++ OR C#", "C++ | C#",
// "C++, C#" and the Hebrew "C++ או C#". A chip with no separator is a single term.
function splitOrGroup(chip: string): string[] {
  return chip
    .split(/\s+OR\s+|\s+או\s+|\||,/i)
    .map(s => s.trim().toLowerCase())
    .filter(Boolean)
}

export const Resumes = (): ReactElement => {
  const [allResumes, setAllResumes] = useState<(ResumeSummary & { searchableText?: string })[]>([])
  const [query, setQuery] = useState<string>('')
  const [filters, setFilters] = useState<FilterState>({
    profession: [],
    minExperience: '',
    maxExperience: '',
    skills: [],
    skillsMatchMode: 'all',
    freeText: [],
    excludeKeywords: []
  })
  const [isAIMode, setIsAIMode] = useState<boolean>(false)
  const [aiPrompt, setAiPrompt] = useState<string>('')
  const [isAiLoading, setIsAiLoading] = useState<boolean>(false)
  const [jobs, setJobs] = useState<ApiJob[]>([])

  // Active job-based ranking (self-contained: title + skills relevance, no match
  // engine). Set when the user searches from a job. `titles` are AI-expanded
  // related titles; matching one strongly implies fit.
  const [jobRanking, setJobRanking] = useState<{
    jobId: string
    title: string
    titles: string[]
    skills: string[]
    loadingTitles: boolean
  } | null>(null)
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('all')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null)
  const [selectedResume, setSelectedResume] = useState<ResumeDetail | null>(null)
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailReloadKey, setDetailReloadKey] = useState<number>(0)
  const [resumeToDelete, setResumeToDelete] = useState<ResumeSummary | null>(null)

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [itemsPerPage] = useState<number>(30)

  // Load analyzed jobs once, for the "search from an existing job" picker.
  useEffect(() => {
    listJobs(0, 100)
      .then((res) => setJobs(res.items.filter((j) => j.analysis_json)))
      .catch((err) => console.error('Failed to load jobs for search:', err))
  }, [])

  const handleJobSelect = useCallback((jobId: string) => {
    const job = jobs.find((j) => j.id === jobId)
    if (!job) return
    const derived = deriveFiltersFromJob(job)
    // Title is the strongest narrower: pre-fill the Profession filter with the
    // role title first (instant), then swap in AI-expanded related titles.
    const roleTitle = job.analysis_json?.role_title || job.title || ''
    setFilters({ ...derived, profession: roleTitle ? [roleTitle] : [] })
    setIsAIMode(false) // reveal the pre-filled manual filters so the user can tweak
    setJobRanking({ jobId, title: job.title, titles: roleTitle ? [roleTitle] : [], skills: derived.skills, loadingTitles: true })

    getRelatedTitles(roleTitle)
      .then((titles) => {
        const list = titles.length ? titles : (roleTitle ? [roleTitle] : [])
        setFilters((prev) => ({ ...prev, profession: list }))
        setJobRanking((prev) =>
          prev && prev.jobId === jobId ? { ...prev, titles: list, loadingTitles: false } : prev
        )
      })
      .catch(() => setJobRanking((prev) => (prev && prev.jobId === jobId ? { ...prev, loadingTitles: false } : prev)))
  }, [jobs])

  // Self-contained relevance: how strongly a resume fits the selected job by
  // TITLE (dominant) and skills. No match engine involved.
  const relevanceScore = useCallback((r: ResumeSummary, ranking: NonNullable<typeof jobRanking>): number => {
    const prof = (r.profession || '').toLowerCase()
    let titleScore = 0
    for (const t of ranking.titles) {
      const tl = t.trim().toLowerCase()
      if (!tl) continue
      if (prof === tl) { titleScore = Math.max(titleScore, 100); break } // exact title
      if (prof.includes(tl) || tl.includes(prof)) titleScore = Math.max(titleScore, 60) // contains
    }
    const skills = (r.skills || []).map((s) => s.toLowerCase())
    let skillHits = 0
    for (const s of ranking.skills) {
      const t = s.toLowerCase()
      if (skills.some((rs) => rs.includes(t))) skillHits += 1
    }
    return titleScore + Math.min(skillHits, 10) * 2 // title dominates, skills refine
  }, [])

  const handleAiSubmit = useCallback(async () => {
    if (!aiPrompt.trim() || isAiLoading) return
    
    setIsAiLoading(true)
    try {
      const newFilters = await analyzeSearchQuery(aiPrompt)
      
      setFilters({
        profession: newFilters.profession || [],
        minExperience: newFilters.minExperience || '',
        maxExperience: newFilters.maxExperience || '',
        skills: newFilters.skills || [],
        skillsMatchMode: 'all',
        freeText: newFilters.freeText || [],
        excludeKeywords: newFilters.excludeKeywords || []
      })
      
      setIsAIMode(false)
    } catch (err) {
      console.error('AI Search failed:', err)
      setFilters(prev => ({
        ...prev,
        freeText: [aiPrompt]
      }))
      setIsAIMode(false)
    } finally {
      setIsAiLoading(false)
    }
  }, [aiPrompt, isAiLoading])

  // 1. Load all resumes at once
  useEffect(() => {
    let isMounted = true

    const fetchAllResumes = async () => {
      setIsLoading(true)
      try {
        // Fetch a large number to get everything
        const response = await listResumes(0, 10000)
        if (!isMounted) return

        setAllResumes(response.items)
        setError(null)
        setIsLoading(false)
      } catch (err) {
        if (isMounted) {
          const message = err instanceof Error ? err.message : 'Failed to load resumes'
          setError(message)
          setIsLoading(false)
        }
      }
    }

    fetchAllResumes()

    return () => {
      isMounted = false
    }
  }, [])

  const handleTimeFilterChange = useCallback((filter: TimeFilter) => {
    setTimeFilter(filter)
  }, [])

  const handleSelectResume = useCallback((resumeId: string) => {
    setSelectedResumeId((currentId) => (currentId === resumeId ? null : resumeId))
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

  const handleDeleteClick = useCallback((resume: ResumeSummary, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setResumeToDelete(resume)
  }, [])

  const handleConfirmDelete = useCallback(async () => {
    if (!resumeToDelete) return

    try {
      await deleteResume(resumeToDelete.id)
      setAllResumes((prev) => prev.filter((r) => r.id !== resumeToDelete.id))
      if (selectedResumeId === resumeToDelete.id) {
        handleClosePanel()
      }
      setResumeToDelete(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete resume'
      alert(message)
    }
  }, [resumeToDelete, selectedResumeId, handleClosePanel])

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

  // 2. Filtering logic - runs on allResumes
  const filteredResumes = useMemo(() => {
    let result = allResumes

    if (query.trim()) {
      const normalized = query.trim().toLowerCase()
      result = result.filter((resume) => {
        const nameMatch = resume.name?.toLowerCase().includes(normalized)
        const professionMatch = resume.profession?.toLowerCase().includes(normalized)
        return Boolean(nameMatch || professionMatch)
      })
    }

    if (filters.profession.length > 0) {
      result = result.filter(r => {
        if (!r.profession) return false
        return filters.profession.some(p => {
          const term = p.trim()
          if (!term) return false
          const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
          
          // Improved logic: Only apply word boundary (\b) if the term starts/ends with a word character.
          const startBoundary = /^\w/.test(term) ? '\\b' : ''
          const endBoundary = /\w$/.test(term) ? '\\b' : ''
          
          const regex = new RegExp(`${startBoundary}${escapedTerm}${endBoundary}`, 'i')
          return regex.test(r.profession || '')
        })
      })
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
        // A chip matches if the candidate has any of its OR-alternatives.
        const chipMatches = (filterSkill: string) => {
          const alternatives = splitOrGroup(filterSkill)
          return alternatives.some(alt => resumeSkills.some(rs => rs.includes(alt)))
        }
        // ANY (OR): candidate needs at least one chip. ALL (AND): needs every chip.
        return filters.skillsMatchMode === 'any'
          ? filters.skills.some(chipMatches)
          : filters.skills.every(chipMatches)
      })
    }

    if (filters.freeText.length > 0) {
      result = result.filter((r) => {
        // Construct a searchable text blob
        const searchableText = [
          r.summary,
          r.name,
          r.profession,
          ...(r.skills || []),
          r.searchableText
        ].filter(Boolean).join(' ').toLowerCase()

        // Each chip must match (AND); "OR"/"|"/","/"או" inside a chip is an OR-group.
        return filters.freeText.every(keyword => {
          const alternatives = splitOrGroup(keyword)
          if (alternatives.length === 0) return false
          return alternatives.some(alt => {
            const escaped = alt.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            const startBoundary = /^\w/.test(alt) ? '\\b' : ''
            const endBoundary = /\w$/.test(alt) ? '\\b' : ''
            return new RegExp(`${startBoundary}${escaped}${endBoundary}`, 'i').test(searchableText)
          })
        })
      })
    }

    if (filters.excludeKeywords.length > 0) {
      result = result.filter((r) => {
        // Construct a searchable text blob
        const searchableText = [
          r.summary,
          r.name,
          r.profession,
          ...(r.skills || []),
          r.searchableText
        ].filter(Boolean).join(' ').toLowerCase()

        // Return FALSE if ANY excluded keyword is found as a WHOLE WORD
        const hasExcludedWord = filters.excludeKeywords.some(keyword => {
          if (!keyword.trim()) return false
          
          // Escape special regex characters to prevent crashes
          const escapedKeyword = keyword.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
          
          // \b ensures word boundaries. 
          // "rea" matches "rea" but NOT "react" or "area"
          const regex = new RegExp(`\\b${escapedKeyword}\\b`, 'i')
          
          return regex.test(searchableText)
        })

        return !hasExcludedWord
      })
    }

    if (timeFilter !== 'all') {
      const now = new Date()
      result = result.filter((r) => {
        if (!r.createdAt) return false
        const date = new Date(r.createdAt)
        const diffTime = Math.abs(now.getTime() - date.getTime())
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

        if (timeFilter === 'today') return diffDays <= 1
        if (timeFilter === 'week') return diffDays <= 7
        if (timeFilter === 'month') return diffDays <= 30
        return true
      })
    }

    // Job-based ranking: best title/skills fit first, newest as tiebreak.
    if (jobRanking) {
      result = [...result].sort((a, b) => {
        const diff = relevanceScore(b, jobRanking) - relevanceScore(a, jobRanking)
        if (diff !== 0) return diff
        return new Date((b as { createdAt?: string }).createdAt || 0).getTime() -
               new Date((a as { createdAt?: string }).createdAt || 0).getTime()
      })
    }

    return result
  }, [allResumes, query, filters, timeFilter, jobRanking, relevanceScore])

  // 3. Reset page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [filters, query, timeFilter])

  // 4. Calculate current page data
  const paginatedResumes = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    return filteredResumes.slice(startIndex, startIndex + itemsPerPage)
  }, [filteredResumes, currentPage, itemsPerPage])

  // 5. Fetch details for visible page
  useEffect(() => {
    let isMounted = true
    
    if (paginatedResumes.length === 0) return

    const fetchDetailsForPage = async () => {
      const itemsToFetch = paginatedResumes.filter(r => r.searchableText === undefined)
      
      if (itemsToFetch.length === 0) return

      try {
        const ids = itemsToFetch.map(r => r.id)
        const details = await getResumesBulk(ids)

        if (!isMounted) return

        const updates = details.map(detail => {
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
              id: detail.id,
              skills: detail.skills.map((s) => s.name),
              summary: detail.summary,
              searchableText,
              createdAt: detail.createdAt,
              yearsByCategory: detail.yearsByCategory,
            }
        })

        setAllResumes((prev) => {
          const next = [...prev]
          updates.forEach((update) => {
            const idx = next.findIndex((r) => r.id === update.id)
            if (idx !== -1) {
              next[idx] = { ...next[idx], ...update }
            }
          })
          return next
        })
      } catch (err) {
        console.error("Bulk fetch failed", err)
        if (isMounted) {
             setAllResumes((prev) => {
                const next = [...prev]
                itemsToFetch.forEach((item) => {
                    const idx = next.findIndex((r) => r.id === item.id)
                    if (idx !== -1) {
                        next[idx] = { ...next[idx], searchableText: '' }
                    }
                })
                return next
            })
        }
      }
    }

    fetchDetailsForPage()

    return () => {
      isMounted = false
    }
  }, [paginatedResumes])

  const listContent = useMemo(() => {
    if (isLoading) {
      return <ResumeTableSkeleton />
    }
    if (error) {
      return <p className={`${styles.status} ${styles.error}`}>{error}</p>
    }
    if (allResumes.length === 0) {
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
      <ResumeTable
        resumes={paginatedResumes}
        selectedResumeId={selectedResumeId}
        onSelect={handleSelectResume}
        onDelete={handleDeleteClick}
        timeFilter={timeFilter}
        onTimeFilterChange={handleTimeFilterChange}
        currentPage={currentPage}
        totalPages={Math.ceil(filteredResumes.length / itemsPerPage)}
        onPageChange={setCurrentPage}
      />
    )
  }, [paginatedResumes, filteredResumes.length, handleSelectResume, handleDeleteClick, isLoading, error, selectedResumeId, timeFilter, handleTimeFilterChange, currentPage, itemsPerPage, allResumes.length])

  const isPanelOpen = Boolean(selectedResumeId)
  const isRTL = /[\u0590-\u05FF]/.test(aiPrompt)

  return (
    <section className={styles.page} aria-labelledby="resumes-title">
      <header className={styles.header}>
        <h1 id="resumes-title" className={styles.title}>
          Resumes
        </h1>
        
        <div className={styles.toolbarContainer}>
          <div className={styles.toolbar}>
            <div className={styles.modeToggle}>
              <button 
                className={`${styles.toggleButton} ${!isAIMode ? styles.active : ''}`}
                onClick={() => setIsAIMode(false)}
              >
                Manual
              </button>
              <button 
                className={`${styles.toggleButton} ${isAIMode ? styles.active : ''}`}
                onClick={() => setIsAIMode(true)}
              >
                <FaMagic /> AI Assistant
              </button>
            </div>

            {!isAIMode && (
              <>
                <div className={styles.divider} />
                <ResumeFilters 
                  onFilterChange={setFilters} 
                  initialFilters={filters} 
                />
                <div className={styles.divider} />
                <div className={styles.searchWrapper}>
                  <FaSearch className={styles.searchIcon} />
                  <input
                    type="text"
                    className={styles.searchInput}
                    placeholder="Search by name..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>

          {isAIMode && (
            <div className={styles.aiSection}>
              <div className={`${styles.aiInputWrapper} ${isRTL ? styles.rtl : ''}`}>
                <textarea
                  className={styles.aiInput}
                  placeholder="Describe the candidate you are looking for... (e.g. 'Senior React Developer with 5 years experience and leadership skills')"
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  disabled={isAiLoading}
                  dir="auto"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleAiSubmit()
                    }
                  }}
                />
                <button 
                  className={styles.aiSubmitButton}
                  onClick={handleAiSubmit}
                  disabled={!aiPrompt.trim() || isAiLoading}
                  aria-label="Submit AI Search"
                >
                  {isAiLoading ? <div className={styles.spinner} /> : <FaPaperPlane />}
                </button>
              </div>
              <div className={styles.aiHint}>
                <FaMagic className={styles.magicIcon} />
                AI will analyze your request and apply advanced filters automatically
              </div>

              <div className={styles.jobPickerDivider}>
                <span>or start from an existing job</span>
              </div>
              <div className={styles.jobPickerWrap}>
                <FaBriefcase className={styles.jobPickerIcon} />
                <select
                  className={styles.jobPickerSelect}
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) handleJobSelect(e.target.value)
                    e.target.value = ''
                  }}
                >
                  <option value="" disabled>
                    Select a job to auto-fill filters…
                  </option>
                  {jobs.map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.icon ? `${job.icon} ` : ''}{job.title}
                    </option>
                  ))}
                </select>
                <FaChevronDown className={styles.jobPickerChevron} />
              </div>
            </div>
          )}
        </div>
      </header>

      {jobRanking && (
        <div className={styles.rankingBar}>
          <span className={styles.rankingBadge}>
            <FaMagic size={11} />
            Ranked by fit to: <strong>{jobRanking.title}</strong>
            <span className={styles.rankingCount}>
              {jobRanking.loadingTitles
                ? 'expanding titles…'
                : `${jobRanking.titles.length} related titles`}
            </span>
          </span>
          <button
            type="button"
            className={styles.rankingClear}
            onClick={() => setJobRanking(null)}
            title="Remove ranking (back to newest first)"
          >
            ×
          </button>
        </div>
      )}

      <div className={styles.body}>
        <div className={styles.listWrapper}>{listContent}</div>
      </div>
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

      <ConfirmationModal
        isOpen={!!resumeToDelete}
        title="Delete Resume"
        message={`Are you sure you want to delete ${resumeToDelete?.name}? This action cannot be undone.`}
        onConfirm={handleConfirmDelete}
        onCancel={() => setResumeToDelete(null)}
        confirmLabel="Delete"
        isDangerous
      />
    </section>
  )
}
