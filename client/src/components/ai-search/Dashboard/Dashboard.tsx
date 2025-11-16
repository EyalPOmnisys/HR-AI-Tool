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

// Helper: Count number of bullet points in text
function countBullets(text: string | undefined | null): number {
  if (!text) return 0
  return text.split('•').filter(line => line.trim()).length
}

// Helper: Check if concerns text indicates no concerns
function hasNoConcerns(text: string | undefined | null): boolean {
  if (!text) return true
  const lower = text.toLowerCase().trim()
  return (
    lower === 'no significant concerns identified.' ||
    lower === 'no significant concerns identified' ||
    lower === 'no concerns' ||
    lower === 'none' ||
    lower.startsWith('no significant concerns')
  )
}

// Helper: Format AI insights with proper line breaks and structure
function formatAIInsight(text: string | undefined | null): React.ReactNode {
  if (!text) return ''
  
  // Split by bullet points and format each line
  const lines = text
    .split('•')
    .filter(line => line.trim())
    .map((line, index) => {
      const trimmed = line.trim()
      
      // Check if line starts with a category (ends with colon)
      const colonIndex = trimmed.indexOf(':')
      if (colonIndex > 0 && colonIndex < 40) {
        const category = trimmed.substring(0, colonIndex + 1)
        const content = trimmed.substring(colonIndex + 1).trim()
        
        return (
          <div key={index} style={{ marginBottom: '8px' }}>
            <span style={{ fontWeight: 600, color: '#1f2937' }}>• {category}</span>
            <span style={{ marginLeft: '4px' }}>{content}</span>
          </div>
        )
      }
      
      // No category, just format as regular bullet
      return (
        <div key={index} style={{ marginBottom: '8px' }}>
          • {trimmed}
        </div>
      )
    })
  
  return <>{lines}</>
}


export default function Dashboard({ matchResults, selectedJob }: Props) {
  const candidates = matchResults.candidates;
  const [expandedResumeId, setExpandedResumeId] = useState<string | null>(null);
  const [expandedStrengths, setExpandedStrengths] = useState<Set<string>>(new Set());
  const [expandedConcerns, setExpandedConcerns] = useState<Set<string>>(new Set());
  
  const avgScore =
    candidates.length > 0
      ? Math.round(candidates.reduce((sum, c) => sum + c.match, 0) / candidates.length)
      : 0;

  const toggleResume = (resumeId: string) => {
    setExpandedResumeId(expandedResumeId === resumeId ? null : resumeId);
  };

  const toggleStrengths = (resumeId: string) => {
    setExpandedStrengths(prev => {
      const newSet = new Set(prev);
      if (newSet.has(resumeId)) {
        newSet.delete(resumeId);
      } else {
        newSet.add(resumeId);
      }
      return newSet;
    });
  };

  const toggleConcerns = (resumeId: string) => {
    setExpandedConcerns(prev => {
      const newSet = new Set(prev);
      if (newSet.has(resumeId)) {
        newSet.delete(resumeId);
      } else {
        newSet.add(resumeId);
      }
      return newSet;
    });
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
                    <td className={`${styles.aiInsightCell} ${expandedStrengths.has(candidate.resume_id) ? styles.expanded : ''}`}>
                      {candidate.llm_strengths ? (
                        <div className={styles.aiInsightWrapper}>
                          <button
                            onClick={() => toggleStrengths(candidate.resume_id)}
                            className={styles.expandButton}
                          >
                            {expandedStrengths.has(candidate.resume_id) ? (
                              <>
                                <FiChevronUp size={14} style={{ marginRight: '4px' }} />
                                Hide
                              </>
                            ) : (
                              <>
                                <FiChevronDown size={14} style={{ marginRight: '4px' }} />
                                Show ({countBullets(candidate.llm_strengths)})
                              </>
                            )}
                          </button>
                          {expandedStrengths.has(candidate.resume_id) && (
                            <div className={`${styles.aiInsight} ${styles.strengthsInsight}`}>
                              {formatAIInsight(candidate.llm_strengths)}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: '#999' }}>—</span>
                      )}
                    </td>
                    <td className={`${styles.aiInsightCell} ${expandedConcerns.has(candidate.resume_id) ? styles.expanded : ''}`}>
                      {candidate.llm_concerns && !hasNoConcerns(candidate.llm_concerns) ? (
                        <div className={styles.aiInsightWrapper}>
                          <button
                            onClick={() => toggleConcerns(candidate.resume_id)}
                            className={styles.expandButton}
                          >
                            {expandedConcerns.has(candidate.resume_id) ? (
                              <>
                                <FiChevronUp size={14} style={{ marginRight: '4px' }} />
                                Hide
                              </>
                            ) : (
                              <>
                                <FiChevronDown size={14} style={{ marginRight: '4px' }} />
                                Show ({countBullets(candidate.llm_concerns)})
                              </>
                            )}
                          </button>
                          {expandedConcerns.has(candidate.resume_id) && (
                            <div className={`${styles.aiInsight} ${styles.concernsInsight}`}>
                              {formatAIInsight(candidate.llm_concerns)}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div style={{ color: '#10b981', fontStyle: 'italic', padding: '8px' }}>
                          ✓ No significant concerns
                        </div>
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

