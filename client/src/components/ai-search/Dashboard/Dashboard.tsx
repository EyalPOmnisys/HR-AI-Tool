import styles from './Dashboard.module.css'
import type { JobAnalytics } from '../../../types/ai-search'
import { FiDownload, FiBriefcase, FiTarget, FiTrendingUp, FiUsers } from 'react-icons/fi'
import { HiCheckCircle } from 'react-icons/hi2'

type Props = {
  analytics: JobAnalytics
  desiredCandidates: number
}

// Helper: score color based on percentage
function getScoreColor(score: number): string {
  if (score >= 85) return '#10b981' // green
  if (score >= 75) return '#3b82f6' // blue
  if (score >= 65) return '#f59e0b' // amber
  return '#ef4444' // red
}

export default function Dashboard({ analytics, desiredCandidates }: Props) {
  const visibleCandidates = analytics.recommendedCandidates
    .slice(0, desiredCandidates)
    .sort((a, b) => b.score - a.score) // Sort from highest to lowest score
  const avgScore =
    visibleCandidates.length > 0
      ? Math.round(visibleCandidates.reduce((sum, c) => sum + c.score, 0) / visibleCandidates.length)
      : 0
  const pipelineTotal = analytics.pipeline.reduce((sum, s) => sum + s.count, 0)

  return (
    <section className={styles.resultsSection}>
      {/* Candidates Table */}
      <div className={styles.tableSection}>
        <table className={styles.candidateTable}>
          <thead>
            <tr>
              <th>🎯 Match</th>
              <th>👤 Candidate</th>
              <th>📅 Experience</th>
              <th>✉️ Email</th>
              <th>📞 Phone</th>
              <th>📄 Resume</th>
            </tr>
          </thead>
          <tbody>
            {visibleCandidates.map((candidate) => (
              <tr key={candidate.id}>
                <td>
                  <div className={styles.scoreContainer}>
                    <div
                      className={styles.scoreBadge}
                      style={{ backgroundColor: getScoreColor(candidate.score) }}
                    >
                      {candidate.score}%
                    </div>
                  </div>
                </td>
                <td className={styles.nameCell}>
                  <span className={styles.candidateName}>{candidate.name}</span>
                  <span className={styles.roleSpan}>{candidate.currentRole}</span>
                </td>
                <td>{candidate.experience}</td>
                <td>
                  <a href={`mailto:${candidate.email}`} className={styles.contactLink}>
                    {candidate.email}
                  </a>
                </td>
                <td>
                  <a href={`tel:${candidate.phone}`} className={styles.contactLink}>
                    {candidate.phone}
                  </a>
                </td>
                <td>
                  <a href={candidate.resumeUrl} target="_blank" rel="noopener noreferrer" className={styles.resumeLink}>
                    <FiDownload size={16} style={{ marginRight: '6px' }} />
                    Resume
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Analytics Section */}
      <div className={styles.analyticsSection}>
        {/* Key Metrics */}
        <div className={styles.metricsRow}>
          <div className={styles.metricBox}>
            <div className={styles.metricIcon}>
              <FiTarget size={24} />
            </div>
            <p className={styles.metricLabel}>Average Match Score</p>
            <p className={styles.metricBigValue}>{avgScore}%</p>
          </div>
          <div className={styles.metricBox}>
            <div className={styles.metricIcon}>
              <FiUsers size={24} />
            </div>
            <p className={styles.metricLabel}>Pipeline Candidates</p>
            <p className={styles.metricBigValue}>{pipelineTotal}</p>
          </div>
          <div className={styles.metricBox}>
            <div className={styles.metricIcon}>
              <HiCheckCircle size={24} />
            </div>
            <p className={styles.metricLabel}>Avg Culture Add</p>
            <p className={styles.metricBigValue}>{analytics.metrics.cultureAdd}%</p>
          </div>
          <div className={styles.metricBox}>
            <div className={styles.metricIcon}>
              <FiTrendingUp size={24} />
            </div>
            <p className={styles.metricLabel}>Hiring Velocity</p>
            <p className={styles.metricBigValue}>{analytics.metrics.velocity}%</p>
          </div>
        </div>

        {/* Pipeline + Skills */}
        <div className={styles.chartsGrid}>
          <div className={styles.chartBox}>
            <h3>
              <FiBriefcase size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: '#8b5cf6' }} />
              Pipeline Distribution
            </h3>
            <ul className={styles.pipelineList}>
              {analytics.pipeline.map((stage) => (
                <li key={stage.label} className={styles.pipelineRow}>
                  <span className={styles.pipelineLabel}>{stage.label}</span>
                  <div className={styles.pipelineBar}>
                    <div
                      className={styles.pipelineFill}
                      style={{ width: `${Math.min((stage.count / pipelineTotal) * 100, 100)}%` }}
                    ></div>
                  </div>
                  <span className={styles.pipelineCount}>{stage.count}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className={styles.chartBox}>
            <h3>
              <FiTarget size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: '#06b6d4' }} />
              Top Skills
            </h3>
            <ul className={styles.skillsList}>
              {analytics.skillFocus.slice(0, 5).map((skill) => (
                <li key={skill.skill} className={styles.skillRow}>
                  <span className={styles.skillName}>{skill.skill}</span>
                  <div className={styles.skillBar}>
                    <div className={styles.skillFill} style={{ width: `${skill.percentage}%` }}></div>
                  </div>
                  <span className={styles.skillPercent}>{skill.percentage}%</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
