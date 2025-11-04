import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent, ReactElement } from 'react'
import styles from './AISearch.module.css'
import { analyticsByJobId } from '../../data/aiSearchData'
import type { JobAnalytics } from '../../types/ai-search'
import Form from '../../components/ai-search/Form/Form'
import Loading from '../../components/ai-search/Loading/Loading'
import Dashboard from '../../components/ai-search/Dashboard/Dashboard'
import { listJobs, type ApiJob } from '../../services/jobs'

type ViewState = 'form' | 'loading' | 'results'

const loadingMessages = [
  'Initiating deep search across candidate database…',
  'Loading job requirements and company culture parameters…',
  'Processing AI analysis on skills and experience patterns…',
  'Filtering candidates based on qualification criteria…',
  'Analyzing multi-layer compatibility factors…',
  'Matching candidates to role-specific requirements…',
  'Running comprehensive analytics on top performers…',
  'Ranking candidates by relevance and potential fit…',
  'Optimizing recommendations with machine learning…',
  'Finalizing results and preparing insights dashboard…'
] as const

export default function AISearch(): ReactElement {
  const [jobs, setJobs] = useState<ApiJob[]>([])
  const [selectedJobId, setSelectedJobId] = useState('')
  const [desiredCandidates, setDesiredCandidates] = useState(3)
  const [view, setView] = useState<ViewState>('form')
  const [activeAnalytics, setActiveAnalytics] = useState<JobAnalytics | null>(null)
  const [activeLoadingMessage, setActiveLoadingMessage] = useState(0)
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const loadingTickerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [isLoadingJobs, setIsLoadingJobs] = useState(true)

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setIsLoadingJobs(true)
        const response = await listJobs()
        setJobs(response.items)
        if (response.items.length > 0) {
          setSelectedJobId(response.items[0].id)
        }
      } catch (error) {
        console.error('Failed to fetch jobs:', error)
      } finally {
        setIsLoadingJobs(false)
      }
    }
    fetchJobs()
  }, [])

  useEffect(() => {
    return () => {
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current)
      if (loadingTickerRef.current) clearInterval(loadingTickerRef.current)
    }
  }, [])

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId),
    [jobs, selectedJobId]
  )

  const handleJobChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedJobId(event.target.value)
  }

  const handleCandidateChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextValue = Number.parseInt(event.target.value, 10)
    if (Number.isNaN(nextValue)) {
      setDesiredCandidates(1)
      return
    }
    setDesiredCandidates(Math.min(Math.max(nextValue, 1), 20))
  }

  const resetTimers = useCallback(() => {
    if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current)
    if (loadingTickerRef.current) clearInterval(loadingTickerRef.current)
  }, [])

  const handleGenerate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedJobId) return
    resetTimers()
    setActiveLoadingMessage(0)
    setView('loading')
    loadingTickerRef.current = setInterval(() => {
      setActiveLoadingMessage((previous) => (previous + 1) % loadingMessages.length)
    }, 2000)
    loadingTimerRef.current = setTimeout(() => {
      resetTimers()
      const analytics = analyticsByJobId[selectedJobId]
      setActiveAnalytics(analytics)
      setView('results')
    }, 10000)
  }

  const handleRunAnotherSearch = () => {
    resetTimers()
    setActiveLoadingMessage(0)
    setView('form')
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>AI Talent Search</h1>
        {view === 'results' && (
          <button
            type='button'
            className={styles.secondaryButton}
            onClick={handleRunAnotherSearch}
          >
            New Search
          </button>
        )}
      </header>

      {view === 'form' && (
        <Form
          jobs={jobs}
          selectedJobId={selectedJobId}
          desiredCandidates={desiredCandidates}
          selectedJob={selectedJob}
          isLoadingJobs={isLoadingJobs}
          onJobChange={handleJobChange}
          onCandidateChange={handleCandidateChange}
          onSubmit={handleGenerate}
        />
      )}

      {view === 'loading' && (
        <Loading messages={loadingMessages} activeIndex={activeLoadingMessage} />
      )}

      {view === 'results' && activeAnalytics && (
        <Dashboard analytics={activeAnalytics} desiredCandidates={desiredCandidates} />
      )}
    </div>
  )
}
