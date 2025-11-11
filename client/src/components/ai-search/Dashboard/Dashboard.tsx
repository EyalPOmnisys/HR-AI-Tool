import styles from './Dashboard.module.css'
import type { MatchRunResponse } from '../../../types/match'
import type { ApiJob } from '../../../types/job'
import { FiDownload, FiUsers, FiTrendingUp, FiAward } from 'react-icons/fi'

type Props = {
  matchResults: MatchRunResponse
  selectedJob?: ApiJob
}

// Helper: score color based on percentage
function getScoreColor(score: number): string {
  if (score >= 85) return '#10b981' // green
  if (score >= 75) return '#3b82f6' // blue
  if (score >= 65) return '#f59e0b' // amber
  return '#ef4444' // red
}

export default function Dashboard({ matchResults, selectedJob }: Props) {
  const candidates = matchResults.candidates;
  const avgScore =
    candidates.length > 0
      ? Math.round(candidates.reduce((sum, c) => sum + c.match, 0) / candidates.length)
      : 0;

  return (
    <section className={styles.resultsSection}>
      {/* Candidates Table */}
      <div className={styles.tableSection}>
        {candidates.length === 0 ? (
          <div style={{ padding: '48px', textAlign: 'center', color: '#999' }}>
            <p style={{ fontSize: '1.2rem', margin: 0 }}>No candidates found matching the criteria</p>
          </div>
        ) : (
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
              {candidates.map((candidate) => (
                <tr key={candidate.resume_id}>
                  <td>
                    <div className={styles.scoreContainer}>
                      <div
                        className={styles.scoreBadge}
                        style={{ backgroundColor: getScoreColor(candidate.match) }}
                      >
                        {candidate.match}%
                      </div>
                      {candidate.llm_verdict && (
                        <span style={{ fontSize: '0.7rem', color: '#666', marginLeft: '8px' }}>
                          {candidate.llm_verdict === 'strong_fit' && '💪'}
                          {candidate.llm_verdict === 'partial_fit' && '🤔'}
                          {candidate.llm_verdict === 'weak_fit' && '⚠️'}
                          {candidate.llm_verdict === 'no_fit' && '❌'}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className={styles.nameCell}>
                    <span className={styles.candidateName}>
                      {candidate.candidate || 'Unknown'}
                    </span>
                  </td>
                  <td>{candidate.experience || '—'}</td>
                  <td>
                    {candidate.email ? (
                      <a href={`mailto:${candidate.email}`} className={styles.contactLink}>
                        {candidate.email}
                      </a>
                    ) : (
                      <span style={{ color: '#999' }}>—</span>
                    )}
                  </td>
                  <td>
                    {candidate.phone ? (
                      <a href={`tel:${candidate.phone}`} className={styles.contactLink}>
                        {candidate.phone}
                      </a>
                    ) : (
                      <span style={{ color: '#999' }}>—</span>
                    )}
                  </td>
                  <td>
                    {candidate.resume_url ? (
                      <a
                        href={candidate.resume_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.resumeLink}
                      >
                        <FiDownload size={16} style={{ marginRight: '6px' }} />
                        Resume
                      </a>
                    ) : (
                      <span style={{ color: '#999' }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Statistics Section */}
      {candidates.length > 0 && (
        <div className={styles.statsSection}>
          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <div className={styles.statIcon}>
                <FiUsers size={24} />
              </div>
              <div className={styles.statLabel}>Candidates Found</div>
              <div className={styles.statValue}>{matchResults.returned} / {matchResults.requested_top_n}</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statIcon}>
                <FiTrendingUp size={24} />
              </div>
              <div className={styles.statLabel}>Average Match</div>
              <div className={styles.statValue} style={{ color: getScoreColor(avgScore) }}>
                {avgScore}%
              </div>
            </div>
            {/* Placeholder for more stats */}
            <div className={styles.statCard}>
              <div className={styles.statIcon}>
                <FiAward size={24} />
              </div>
              <div className={styles.statLabel}>Top Score</div>
              <div className={styles.statValue}>
                {candidates.length > 0 ? `${Math.max(...candidates.map(c => c.match))}%` : '—'}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

