// src/pages/ai-search/AISearch.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, FormEvent, ReactElement } from 'react';
import styles from './AISearch.module.css';
import Form from '../../components/ai-search/Form/Form';
import Loading from '../../components/ai-search/Loading/Loading';
import Dashboard from '../../components/ai-search/Dashboard/Dashboard';
import { listJobs } from '../../services/jobs';
import type { ApiJob } from '../../types/job';
import ProgressSteps from '../../components/ai-search/ProgressSteps/ProgressSteps';
import { runMatch } from '../../services/match';
import type { MatchRunResponse } from '../../types/match';
import { loadingMessages, loadingIcons } from '../../data/loadingMessages';

type ViewState = 'form' | 'loading' | 'results';

export default function AISearch(): ReactElement {
  // Jobs and selection
  const [jobs, setJobs] = useState<ApiJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState('');

  // Form state
  const [desiredCandidates, setDesiredCandidates] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string[]>(['new']);

  // View state
  const [view, setView] = useState<ViewState>('form');

  // Match results from backend
  const [matchResults, setMatchResults] = useState<MatchRunResponse | null>(null);
  const [matchError, setMatchError] = useState<string | null>(null);

  // Loading sequence control
  const [activeLoadingMessage, setActiveLoadingMessage] = useState(0);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadingTickerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Jobs fetching indicator
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);

  // Fetch jobs on mount
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setIsLoadingJobs(true);
        const response = await listJobs();
        setJobs(response.items);
        if (response.items.length > 0) {
          setSelectedJobId(response.items[0].id);
        }
      } catch (error) {
        console.error('Failed to fetch jobs:', error);
      } finally {
        setIsLoadingJobs(false);
      }
    };
    fetchJobs();
  }, []);

  // Clear timers on unmount
  useEffect(() => {
    return () => {
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
      if (loadingTickerRef.current) clearInterval(loadingTickerRef.current);
    };
  }, []);

  // Selected job object
  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId),
    [jobs, selectedJobId]
  );

  // Progress steps: map view → active step index
  const activeStepIndex = view === 'form' ? 0 : view === 'loading' ? 1 : 2;

  // Build steps model for ProgressSteps (labels + per-step status)
  const steps = useMemo(() => {
    const labels = ['Select Criteria', 'Processing', 'Candidates'];
    return labels.map((title, idx) => {
      let statusLabel: string | undefined;
      if (idx < activeStepIndex) statusLabel = 'Completed';
      else if (idx === activeStepIndex)
        statusLabel = view === 'loading' ? 'In Progress' : 'Active';
      else statusLabel = 'Pending';
      return { title, statusLabel };
    });
  }, [activeStepIndex, view]);

  // Handlers
  const handleJobChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedJobId(event.target.value);
  };

  const handleCandidateChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextValue = Number.parseInt(event.target.value, 10);
    if (Number.isNaN(nextValue)) {
      setDesiredCandidates(1);
      return;
    }
    setDesiredCandidates(Math.min(Math.max(nextValue, 1), 20));
  };

  const handleStatusFilterChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const options = event.target.options;
    const value: string[] = [];
    for (let i = 0, l = options.length; i < l; i++) {
      if (options[i].selected) {
        value.push(options[i].value);
      }
    }
    setStatusFilter(value);
  };

  const resetTimers = useCallback(() => {
    if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
    if (loadingTickerRef.current) clearInterval(loadingTickerRef.current);
  }, []);

  const handleGenerate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedJobId) return;

    // Reset and go to loading
    resetTimers();
    setActiveLoadingMessage(0);
    setMatchError(null);
    setView('loading');

    // Cycle through loading messages every 2s
    loadingTickerRef.current = setInterval(() => {
      setActiveLoadingMessage((prev) => (prev + 1) % loadingMessages.length);
    }, 2000);

    try {
      // Call the real API with user-selected number of candidates
      // If statusFilter is empty, default to ['new']
      const effectiveStatusFilter = statusFilter.length > 0 ? statusFilter : ['new'];
      
      const result = await runMatch({
        job_id: selectedJobId,
        top_n: desiredCandidates,
        status_filter: effectiveStatusFilter,
        min_threshold: 0,
      });

      resetTimers();
      setMatchResults(result);
      setView('results');
    } catch (error) {
      resetTimers();
      setMatchError(error instanceof Error ? error.message : 'Failed to run match');
      setView('form');
      console.error('Match error:', error);
    }
  };

  const handleRunAnotherSearch = () => {
    resetTimers();
    setActiveLoadingMessage(0);
    setMatchResults(null);
    setMatchError(null);
    setView('form');
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>AI Talent Search</h1>

        <div className={styles.headerRight}>
          <ProgressSteps
            steps={steps}
            activeIndex={activeStepIndex}
            isLoading={view === 'loading'}
            loadingDurationMs={30000}
          />
          {view === 'results' && (
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={handleRunAnotherSearch}
            >
              New Search
            </button>
          )}
        </div>
      </header>

      {view === 'form' && (
        <Form
          jobs={jobs}
          selectedJobId={selectedJobId}
          desiredCandidates={desiredCandidates}
          statusFilter={statusFilter}
          selectedJob={selectedJob}
          isLoadingJobs={isLoadingJobs}
          error={matchError}
          onJobChange={handleJobChange}
          onCandidateChange={handleCandidateChange}
          onStatusFilterChange={handleStatusFilterChange}
          onSubmit={handleGenerate}
        />
      )}

      {view === 'loading' && (
        <Loading messages={loadingMessages} activeIndex={activeLoadingMessage} icons={loadingIcons} />
      )}

      {view === 'results' && matchResults && (
        <Dashboard matchResults={matchResults} selectedJob={selectedJob} />
      )}
    </div>
  );
}
