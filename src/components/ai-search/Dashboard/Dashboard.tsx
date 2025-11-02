import styles from './Dashboard.module.css'
import type { JobAnalytics } from '../../../types/ai-search'

type Props = {
  analytics: JobAnalytics
  desiredCandidates: number
}

export default function Dashboard({ analytics, desiredCandidates }: Props) {
  const visibleCandidates = analytics.recommendedCandidates.slice(0, desiredCandidates)
  const availableRecommended = analytics.recommendedCandidates.length
  const totalMonitored = analytics.pipeline.reduce((acc, s) => acc + s.count, 0)

  return (
    <section className={styles.resultsSection}>
      <article className={styles.summaryCard}>
        <div>
          <h2 className={styles.summaryTitle}>{analytics.jobTitle}</h2>
          <p className={styles.summaryMeta}>
            {analytics.department} · {analytics.location}
          </p>
        </div>
        <p className={styles.summaryBody}>{analytics.summary}</p>
        <ul className={styles.summaryHighlights}>
          {analytics.highlights.map((highlight) => (
            <li key={highlight}>{highlight}</li>
          ))}
        </ul>
      </article>

      <div className={styles.metricGrid}>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Role Fit</span>
          <span className={styles.metricValue}>{analytics.metrics.suitability}%</span>
          <span className={styles.metricFootnote}>Benchmarked against top 5% performers</span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Culture Add</span>
          <span className={styles.metricValue}>{analytics.metrics.cultureAdd}%</span>
          <span className={styles.metricFootnote}>Signals from leadership interview calibration</span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Hiring Velocity</span>
          <span className={styles.metricValue}>{analytics.metrics.velocity}%</span>
          <span className={styles.metricFootnote}>Projected acceleration vs. last quarter</span>
        </div>
      </div>

      <div className={styles.analyticsGrid}>
        <article className={styles.pipelineCard}>
          <header className={styles.cardHeader}>
            <h3>Pipeline Status</h3>
            <span>{totalMonitored} profiles monitored</span>
          </header>
          <ul className={styles.pipelineList}>
            {analytics.pipeline.map((stage) => (
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
            {analytics.skillFocus.map((skill) => (
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
  )
}
