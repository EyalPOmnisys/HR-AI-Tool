import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent, ReactElement } from 'react'
import styles from './AISearch.module.css'
import { analyticsByJobId, jobOptions } from '../../data/aiSearchData'
import type { JobAnalytics } from '../../types/ai-search'
import Form from '../../components/ai-search/Form/Form'
import Loading from '../../components/ai-search/Loading/Loading'
import Dashboard from '../../components/ai-search/Dashboard/Dashboard'

type ViewState = 'form' | 'loading' | 'results'

const loadingMessages = [
  'Synthesising calibrated success profiles…',
  'Mapping real-world achievements against hiring signals…',
  'Scoring candidate resonance with leadership expectations…',
  'Stress-testing culture add indicators…'
] as const

export default function AISearch(): ReactElement {
  const [selectedJobId, setSelectedJobId] = useState(jobOptions[0]?.id ?? '')
  const [desiredCandidates, setDesiredCandidates] = useState(3)
  const [view, setView] = useState<ViewState>('form')
  const [activeAnalytics, setActiveAnalytics] = useState<JobAnalytics | null>(
    analyticsByJobId[jobOptions[0]?.id ?? ''] ?? null
  )
  const [activeLoadingMessage, setActiveLoadingMessage] = useState(0)
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const loadingTickerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current)
      if (loadingTickerRef.current) clearInterval(loadingTickerRef.current)
    }
  }, [])

  const selectedJobOption = useMemo(
    () => jobOptions.find((option) => option.id === selectedJobId),
    [selectedJobId]
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
    setDesiredCandidates(Math.min(Math.max(nextValue, 1), 8))
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
    }, 1600)
    loadingTimerRef.current = setTimeout(() => {
      resetTimers()
      const analytics = analyticsByJobId[selectedJobId]
      setActiveAnalytics(analytics)
      setView('results')
    }, 3400)
  }

  const handleRunAnotherSearch = () => {
    resetTimers()
    setActiveLoadingMessage(0)
    setView('form')
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>AI Talent Search</h1>
          <p className={styles.subtitle}>
            Curate ready-to-run hiring shortlists with calibrated analytics, leveraging live talent signals.
          </p>
        </div>
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
          jobOptions={jobOptions}
          selectedJobId={selectedJobId}
          desiredCandidates={desiredCandidates}
          selectedJobOption={selectedJobOption}
          previewHighlights={
            selectedJobOption ? (analyticsByJobId[selectedJobOption.id]?.highlights ?? []) : []
          }
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
