import { useState } from 'react'
import styles from './Dashboard.module.css'
import type { MatchRunResponse } from '../../../types/match'
import type { ApiJob } from '../../../types/job'
import { FiUsers, FiTrendingUp, FiAward, FiChevronDown, FiChevronUp } from 'react-icons/fi'
import { localizeILPhone, formatILPhoneDisplay } from '../../../utils/phone'

type Props = {
  matchResults: MatchRunResponse
  selectedJob?: ApiJob
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Helper: score color based on percentage
function getScoreColor(score: number): string {
  if (score >= 85) return '#10b981' // green
  if (score >= 75) return '#3b82f6' // blue
  if (score >= 65) return '#f59e0b' // amber
  return '#ef4444' // red
}


export default function Dashboard({ matchResults, selectedJob }: Props) {
  const candidates = matchResults.candidates;
  const [expandedResumeId, setExpandedResumeId] = useState<string | null>(null);
  const avgScore =
    candidates.length > 0
      ? Math.round(candidates.reduce((sum, c) => sum + c.match, 0) / candidates.length)
      : 0;

  const toggleResume = (resumeId: string) => {
    setExpandedResumeId(expandedResumeId === resumeId ? null : resumeId);
  };

  return (
    <section className={styles.resultsSection}>
      {/* Job Title Header */}
      {selectedJob && (
        <div className={styles.header}>
          <h2 className={styles.jobTitle}>{selectedJob.title}</h2>
        </div>
      )}

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
                <th>💪 Strengths</th>
                <th>⚠️ Concerns</th>
                <th>📝 Recommendation</th>
                <th>✉️ Email</th>
                <th>📞 Phone</th>
                <th>📄 Resume</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <>
                  <tr key={candidate.resume_id} className={expandedResumeId === candidate.resume_id ? styles.expandedRow : ''}>
                    <td>
                      <div className={styles.scoreContainer}>
                        <div
                          className={styles.scoreBadge}
                          style={{ backgroundColor: getScoreColor(candidate.match) }}
                        >
                          {candidate.match}
                        </div>
                      </div>
                    </td>
                    <td className={styles.nameCell}>
                      <span className={styles.candidateName}>
                        {candidate.candidate || 'Unknown'}
                      </span>
                    </td>
                    <td>{candidate.experience || '—'}</td>
                    <td className={styles.aiInsightCell}>
                      {candidate.llm_strengths ? (
                        <div className={styles.aiInsight}>
                          {candidate.llm_strengths}
                        </div>
                      ) : (
                        <span style={{ color: '#999' }}>—</span>
                      )}
                    </td>
                    <td className={styles.aiInsightCell}>
                      {candidate.llm_concerns ? (
                        <div className={styles.aiInsight}>
                          {candidate.llm_concerns}
                        </div>
                      ) : (
                        <span style={{ color: '#999' }}>None</span>
                      )}
                    </td>
                    <td className={styles.recommendationCell}>
                      {candidate.llm_recommendation ? (
                        <span className={`${styles.recommendationBadge} ${styles[candidate.llm_recommendation]}`}>
                          {candidate.llm_recommendation === 'hire_immediately' && '🚀 Hire Immediately'}
                          {candidate.llm_recommendation === 'strong_interview' && '💼 Strong Interview'}
                          {candidate.llm_recommendation === 'interview' && '📞 Interview'}
                          {candidate.llm_recommendation === 'maybe' && '🤔 Maybe'}
                          {candidate.llm_recommendation === 'pass' && '❌ Pass'}
                        </span>
                      ) : (
                        <span style={{ color: '#999' }}>—</span>
                      )}
                    </td>
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
                        (() => {
                          const localized = localizeILPhone(candidate.phone);
                          const display = formatILPhoneDisplay(candidate.phone) ?? (localized ?? candidate.phone);
                          return (
                            <a href={`tel:${localized ?? candidate.phone}`} className={styles.contactLink}>
                              {display}
                            </a>
                          );
                        })()
                      ) : (
                        <span style={{ color: '#999' }}>—</span>
                      )}
                    </td>
                    <td>
                      {candidate.resume_url ? (
                        <button
                          onClick={() => toggleResume(candidate.resume_id)}
                          className={styles.resumeButton}
                        >
                          {expandedResumeId === candidate.resume_id ? (
                            <>
                              <FiChevronUp size={16} style={{ marginRight: '6px' }} />
                              Close Resume
                            </>
                          ) : (
                            <>
                              <FiChevronDown size={16} style={{ marginRight: '6px' }} />
                              View Resume
                            </>
                          )}
                        </button>
                      ) : (
                        <span style={{ color: '#999' }}>—</span>
                      )}
                    </td>
                  </tr>
                  {expandedResumeId === candidate.resume_id && candidate.resume_url && (
                    <tr key={`${candidate.resume_id}-resume`} className={styles.resumeRow}>
                      <td colSpan={9} className={styles.resumeCell}>
                        <div className={styles.resumeContainer}>
                          <iframe
                            src={`${API_URL}${candidate.resume_url}`}
                            className={styles.resumeIframe}
                            title={`Resume of ${candidate.candidate}`}
                          />
                        </div>
                      </td>
                    </tr>
                  )}
                </>
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

