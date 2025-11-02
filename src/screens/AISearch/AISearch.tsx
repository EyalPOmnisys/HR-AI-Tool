import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent, ReactElement } from 'react'
import styles from './AISearch.module.css'
import { analyticsByJobId, jobOptions } from '../../data/aiSearchData'
import type { JobAnalytics } from '../../types/ai-search'

type ViewState = 'form' | 'loading' | 'results'

const loadingMessages = [
  'Synthesising calibrated success profiles…',
  'Mapping real-world achievements against hiring signals…',
  'Scoring candidate resonance with leadership expectations…',
  'Stress-testing culture add indicators…'
] as const

export const AISearch = (): ReactElement => {
  const [selectedJobId, setSelectedJobId] = useState(jobOptions[0]?.id ?? '')
  const [desiredCandidates, setDesiredCandidates] = useState(3)
  const [view, setView] = useState<ViewState>('form')
  const [activeAnalytics, setActiveAnalytics] = useState<JobAnalytics | null>(
    analyticsByJobId[jobOptions[0]?.id ?? '']
  )
  const [activeLoadingMessage, setActiveLoadingMessage] = useState(0)
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const loadingTickerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current)
      }
      if (loadingTickerRef.current) {
        clearInterval(loadingTickerRef.current)
      }
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
    if (loadingTimerRef.current) {
      clearTimeout(loadingTimerRef.current)
    }
    if (loadingTickerRef.current) {
      clearInterval(loadingTickerRef.current)
    }
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

  const visibleCandidates = useMemo(() => {
    if (!activeAnalytics) return []
    return activeAnalytics.recommendedCandidates.slice(0, desiredCandidates)
  }, [activeAnalytics, desiredCandidates])

  const availableRecommended = activeAnalytics?.recommendedCandidates.length ?? 0

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
        <section className={styles.formSection}>
          <form className={styles.form} onSubmit={handleGenerate}>
            <div className={styles.formField}>
              <label htmlFor='jobSelect'>Select a role</label>
              <div className={styles.fieldShell}>
                <select
                  id='jobSelect'
                  className={styles.select}
                  value={selectedJobId}
                  onChange={handleJobChange}
                >
                  {jobOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className={styles.formField}>
              <label htmlFor='candidateCount'>Number of candidates</label>
              <div className={styles.fieldShell}>
                <input
                  id='candidateCount'
                  className={styles.input}
                  type='number'
                  min={1}
                  max={8}
                  value={desiredCandidates}
                  onChange={handleCandidateChange}
                />
              </div>
              <span className={styles.hint}>Up to {selectedJobOption?.openings === 1 ? 'three' : 'six'} curated profiles available</span>
            </div>
            <div className={styles.formActions}>
              <button type='submit' className={styles.primaryButton}>
                Generate
              </button>
            </div>
          </form>

          {selectedJobOption && (
            <aside className={styles.preview}>
              <span className={styles.previewBadge}>Live snapshot</span>
              <h2 className={styles.previewTitle}>{selectedJobOption.label}</h2>
              <p className={styles.previewMeta}>
                Openings · {selectedJobOption.openings} &nbsp;|&nbsp; Top candidates ready in under 72 hours
              </p>
              <ul className={styles.previewHighlights}>
                {analyticsByJobId[selectedJobOption.id]?.highlights.map((highlight) => (
                  <li key={highlight}>{highlight}</li>
                ))}
              </ul>
            </aside>
          )}
        </section>
      )}

      {view === 'loading' && (
        <section className={styles.loadingSection}>
          <div className={styles.loadingCard}>
            <div className={styles.loadingPulse} aria-hidden />
            <p className={styles.loadingLabel}>Generating your shortlists</p>
            <p className={styles.loadingMessage}>{loadingMessages[activeLoadingMessage]}</p>
            <div className={styles.loadingBar} aria-hidden>
              <span className={styles.loadingBarFill} />
            </div>
          </div>
        </section>
      )}

      {view === 'results' && activeAnalytics && (
        <section className={styles.resultsSection}>
          <article className={styles.summaryCard}>
            <div>
              <h2 className={styles.summaryTitle}>{activeAnalytics.jobTitle}</h2>
              <p className={styles.summaryMeta}>
                {activeAnalytics.department} · {activeAnalytics.location}
              </p>
            </div>
            <p className={styles.summaryBody}>{activeAnalytics.summary}</p>
            <ul className={styles.summaryHighlights}>
              {activeAnalytics.highlights.map((highlight) => (
                <li key={highlight}>{highlight}</li>
              ))}
            </ul>
          </article>

          <div className={styles.metricGrid}>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Role Fit</span>
              <span className={styles.metricValue}>{activeAnalytics.metrics.suitability}%</span>
              <span className={styles.metricFootnote}>Benchmarked against top 5% performers</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Culture Add</span>
              <span className={styles.metricValue}>{activeAnalytics.metrics.cultureAdd}%</span>
              <span className={styles.metricFootnote}>Signals from leadership interview calibration</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Hiring Velocity</span>
              <span className={styles.metricValue}>{activeAnalytics.metrics.velocity}%</span>
              <span className={styles.metricFootnote}>Projected acceleration vs. last quarter</span>
            </div>
          </div>

          <div className={styles.analyticsGrid}>
            <article className={styles.pipelineCard}>
              <header className={styles.cardHeader}>
                <h3>Pipeline Status</h3>
                <span>{activeAnalytics.pipeline.reduce((accumulator, stage) => accumulator + stage.count, 0)} profiles monitored</span>
              </header>
              <ul className={styles.pipelineList}>
                {activeAnalytics.pipeline.map((stage) => (
                  <li key={stage.label} className={styles.pipelineItem}>
                    <div className={styles.pipelineInfo}>
                      <span className={styles.pipelineLabel}>{stage.label}</span>
                      <span className={styles.pipelineCount}>{stage.count}</span>
                    </div>
                    <span className={`${styles.pipelineTrend} ${styles[`trend${stage.trend}`]}`}>
                      {stage.trend === 'up' && '↗'}
                      {stage.trend === 'down' && '↘'}
                      {stage.trend === 'steady' && '→'}
                    </span>
                  </li>
                ))}
              </ul>
            </article>

            <article className={styles.skillsCard}>
              <header className={styles.cardHeader}>
                <h3>Skill Focus</h3>
                <span>Share of calibrated excellence</span>
              </header>
              <ul className={styles.skillList}>
                {activeAnalytics.skillFocus.map((skill) => (
                  <li key={skill.skill}>
                    <div className={styles.skillHeader}>
                      <span>{skill.skill}</span>
                      <span>{skill.percentage}%</span>
                    </div>
                    <div className={styles.skillBar}>
                      <span style={{ width: `${skill.percentage}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          </div>

          <section className={styles.candidatesSection}>
            <header className={styles.cardHeader}>
              <div>
                <h3>Curated Candidates</h3>
                <span>
                  Showing {visibleCandidates.length} of {availableRecommended} calibrated matches
                </span>
              </div>
              <span className={styles.candidateHint}>Prioritised for advanced interview loop readiness</span>
            </header>

            <div className={styles.candidateGrid}>
              {visibleCandidates.map((candidate) => (
                <article key={candidate.id} className={styles.candidateCard}>
                  <div className={styles.candidateScore}>
                    <span>{candidate.score}</span>
                  </div>
                  <div className={styles.candidateContent}>
                    <h4>{candidate.name}</h4>
                    <p className={styles.candidateMeta}>{candidate.currentRole}</p>
                    <p className={styles.candidateMeta}>{candidate.experience}</p>
                    <ul className={styles.candidateHighlights}>
                      {candidate.strengths.map((strength) => (
                        <li key={strength}>{strength}</li>
                      ))}
                    </ul>
                    <p className={styles.candidateNotes}>{candidate.notes}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </section>
      )}
    </div>
  )
}

export default AISearch
