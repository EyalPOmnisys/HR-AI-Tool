import { useState, useEffect, useRef } from 'react'
import styles from './Dashboard.module.css'
import type { MatchRunResponse } from '../../../types/match'
import type { ApiJob } from '../../../types/job'
import { FiUsers, FiTrendingUp, FiAward, FiChevronDown, FiChevronUp, FiHelpCircle, FiX, FiCheckCircle, FiXCircle, FiEye, FiClock } from 'react-icons/fi'
import { localizeILPhone, formatILPhoneDisplay } from '../../../utils/phone'
import { renderAsync } from 'docx-preview'
import { updateCandidateStatus } from '../../../services/jobs'

type Props = {
  matchResults: MatchRunResponse
  selectedJob?: ApiJob
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Helper: Resume Preview Component
const ResumePreview = ({ url, fileName }: { url: string; fileName?: string | null }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const isDocx = fileName?.toLowerCase().endsWith('.docx');

  useEffect(() => {
    if (isDocx && url && containerRef.current) {
      const container = containerRef.current;
      container.innerHTML = ''; // Clear previous content
      
      fetch(url)
        .then(res => {
          if (!res.ok) throw new Error('Failed to load DOCX file');
          return res.blob();
        })
        .then(blob => renderAsync(blob, container, container, {
          inWrapper: true,
          ignoreWidth: false,
          ignoreHeight: false,
          ignoreFonts: false,
          breakPages: true,
          ignoreLastRenderedPageBreak: true,
          experimental: false,
          trimXmlDeclaration: true,
          useBase64URL: false,
          renderChanges: false,
          debug: false,
        }))
        .catch(err => {
          console.error("Failed to render DOCX", err);
          container.innerHTML = `<p style="color: #ef4444; padding: 20px; text-align: center;">Failed to load document preview.</p>`;
        });
    }
  }, [isDocx, url]);

  if (isDocx) {
    return (
      <div 
        ref={containerRef} 
        style={{ 
          height: '800px', 
          overflow: 'auto', 
          backgroundColor: '#f8fafc',
          padding: '40px',
          width: '100%',
          borderRadius: '8px',
          boxShadow: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)'
        }} 
      />
    );
  }

  return (
    <iframe
      src={url}
      className={styles.resumeIframe}
      title="Resume Preview"
      allow="fullscreen"
    />
  );
};

// Helper: Get stability badge configuration
function getStabilityBadge(score: number | undefined): { emoji: string; label: string; color: string; bgColor: string } {
  if (!score) {
    return { emoji: '❓', label: 'Unknown', color: '#6b7280', bgColor: '#f3f4f6' }
  }
  
  // Based on score ranges from employment_stability_scorer.py
  if (score >= 90) {
    return { emoji: '⭐', label: 'Excellent', color: '#059669', bgColor: '#d1fae5' } // Green
  } else if (score >= 80) {
    return { emoji: '✅', label: 'Good', color: '#0891b2', bgColor: '#cffafe' } // Cyan
  } else if (score >= 70) {
    return { emoji: '👍', label: 'OK', color: '#2563eb', bgColor: '#dbeafe' } // Blue
  } else if (score >= 60) {
    return { emoji: '⚠️', label: 'Moderate', color: '#d97706', bgColor: '#fef3c7' } // Amber
  } else if (score >= 50) {
    return { emoji: '⚡', label: 'Concern', color: '#dc2626', bgColor: '#fee2e2' } // Red
  } else {
    return { emoji: '🚩', label: 'High Risk', color: '#991b1b', bgColor: '#fecaca' } // Dark Red
  }
}

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
  const [candidates, setCandidates] = useState(matchResults.candidates);
  const [expandedResumeId, setExpandedResumeId] = useState<string | null>(null);
  const [expandedStrengths, setExpandedStrengths] = useState<Set<string>>(new Set());
  const [expandedConcerns, setExpandedConcerns] = useState<Set<string>>(new Set());
  const [showJobDescription, setShowJobDescription] = useState(false);
  
  // Update local state when props change
  useEffect(() => {
    setCandidates(matchResults.candidates);
  }, [matchResults]);

  const avgScore =
    candidates.length > 0
      ? Math.round(candidates.reduce((sum, c) => sum + c.match, 0) / candidates.length)
      : 0;

  const toggleResume = (resumeId: string) => {
    setExpandedResumeId(expandedResumeId === resumeId ? null : resumeId);
  };

  const handleStatusChange = async (resumeId: string, newStatus: string) => {
    if (!selectedJob) return;
    
    try {
      // Optimistic update
      setCandidates(prev => prev.map(c => 
        c.resume_id === resumeId ? { ...c, status: newStatus } : c
      ));
      
      await updateCandidateStatus(selectedJob.id, resumeId, newStatus);
    } catch (error) {
      console.error("Failed to update status:", error);
      // Revert on error (could be improved with better error handling)
    }
  };

  const getStatusBadge = (status: string | undefined) => {
    switch (status) {
      case 'shortlisted':
        return { icon: <FiCheckCircle />, label: 'Shortlisted', color: '#059669', bg: '#d1fae5' };
      case 'rejected':
        return { icon: <FiXCircle />, label: 'Rejected', color: '#dc2626', bg: '#fee2e2' };
      case 'reviewed':
        return { icon: <FiEye />, label: 'Reviewed', color: '#2563eb', bg: '#dbeafe' };
      default:
        return { icon: <FiClock />, label: 'New', color: '#4b5563', bg: '#f3f4f6' };
    }
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
          <h2 className={styles.jobTitle}>
            {selectedJob.title}
            {selectedJob.job_description && (
              <button
                className={styles.jobInfoButton}
                onClick={() => setShowJobDescription(!showJobDescription)}
                aria-label="Show job description"
              >
                <FiHelpCircle />
              </button>
            )}
          </h2>
          {showJobDescription && selectedJob.job_description && (
            <div className={styles.jobDescriptionModal} onClick={() => setShowJobDescription(false)}>
              <div className={styles.jobDescriptionContent} onClick={(e) => e.stopPropagation()}>
                <header className={styles.jobDescriptionHeader}>
                  <div className={styles.headerContent}>
                    <div className={styles.iconWrapper}>
                      <span>{selectedJob.icon || '💼'}</span>
                    </div>
                    <div className={styles.titleContent}>
                      <h3>{selectedJob.title}</h3>
                      {selectedJob.analysis_json?.organization && (
                        <p className={styles.organization}>{selectedJob.analysis_json.organization}</p>
                      )}
                      <p className={styles.meta}>Full Job Description</p>
                    </div>
                  </div>
                  <button
                    className={styles.closeButton}
                    onClick={() => setShowJobDescription(false)}
                    aria-label="Close"
                  >
                    <FiX />
                  </button>
                </header>
                <div className={styles.jobDescriptionBody}>
                  {selectedJob.analysis_json ? (
                    <>
                      {/* Summary */}
                      {selectedJob.analysis_json.summary && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Summary</h4>
                          <p className={styles.description}>{selectedJob.analysis_json.summary}</p>
                        </section>
                      )}

                      {/* Experience & Salary */}
                      {(selectedJob.analysis_json.experience || selectedJob.analysis_json.salary_range) && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Position Details</h4>
                          <div className={styles.metaInfo}>
                            {selectedJob.analysis_json.experience && (selectedJob.analysis_json.experience.years_min || selectedJob.analysis_json.experience.years_max) && (
                              <div className={styles.metaItem}>
                                <span className={styles.metaIcon}>💼</span>
                                <span className={styles.metaText}>
                                  Experience: {selectedJob.analysis_json.experience.years_min && selectedJob.analysis_json.experience.years_max
                                    ? `${selectedJob.analysis_json.experience.years_min}-${selectedJob.analysis_json.experience.years_max} years`
                                    : selectedJob.analysis_json.experience.years_min
                                    ? `${selectedJob.analysis_json.experience.years_min}+ years`
                                    : `Up to ${selectedJob.analysis_json.experience.years_max} years`
                                  }
                                </span>
                              </div>
                            )}
                            {selectedJob.analysis_json.salary_range && (selectedJob.analysis_json.salary_range.min || selectedJob.analysis_json.salary_range.max) && (
                              <div className={styles.metaItem}>
                                <span className={styles.metaIcon}>💰</span>
                                <span className={styles.metaText}>
                                  Salary: {selectedJob.analysis_json.salary_range.min && selectedJob.analysis_json.salary_range.max
                                    ? `${selectedJob.analysis_json.salary_range.currency} ${selectedJob.analysis_json.salary_range.min.toLocaleString()} - ${selectedJob.analysis_json.salary_range.max.toLocaleString()}`
                                    : selectedJob.analysis_json.salary_range.min
                                    ? `${selectedJob.analysis_json.salary_range.currency} ${selectedJob.analysis_json.salary_range.min.toLocaleString()}+`
                                    : `Up to ${selectedJob.analysis_json.salary_range.currency} ${selectedJob.analysis_json.salary_range.max?.toLocaleString()}`
                                  }
                                </span>
                              </div>
                            )}
                          </div>
                        </section>
                      )}

                      {/* Locations */}
                      {selectedJob.analysis_json.locations && selectedJob.analysis_json.locations.length > 0 && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Locations</h4>
                          <div className={styles.locations}>
                            {selectedJob.analysis_json.locations.map((loc, idx) => (
                              <span key={idx} className={styles.locationBadge}>
                                📍 {loc}
                              </span>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Requirements */}
                      {selectedJob.analysis_json.requirements && selectedJob.analysis_json.requirements.length > 0 && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Key Requirements</h4>
                          <ul className={styles.list}>
                            {selectedJob.analysis_json.requirements.map((req, idx) => (
                              <li key={idx} className={styles.listItem}>
                                {req}
                              </li>
                            ))}
                          </ul>
                        </section>
                      )}

                      {/* Responsibilities */}
                      {selectedJob.analysis_json.responsibilities && selectedJob.analysis_json.responsibilities.length > 0 && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Responsibilities</h4>
                          <ul className={styles.list}>
                            {selectedJob.analysis_json.responsibilities.map((resp, idx) => (
                              <li key={idx} className={styles.listItem}>
                                {resp}
                              </li>
                            ))}
                          </ul>
                        </section>
                      )}

                      {/* Must Have Skills */}
                      {selectedJob.analysis_json.skills?.must_have && selectedJob.analysis_json.skills.must_have.length > 0 && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Must Have Skills</h4>
                          <div className={styles.skillsList}>
                            {selectedJob.analysis_json.skills.must_have.map((skill, idx) => (
                              <span key={idx} className={styles.skillBadge}>
                                {skill}
                              </span>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Nice to Have Skills */}
                      {selectedJob.analysis_json.skills?.nice_to_have && selectedJob.analysis_json.skills.nice_to_have.length > 0 && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Nice to Have Skills</h4>
                          <div className={styles.skillsList}>
                            {selectedJob.analysis_json.skills.nice_to_have.map((skill, idx) => (
                              <span key={idx} className={styles.skillBadgeOptional}>
                                {skill}
                              </span>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Tech Stack */}
                      {selectedJob.analysis_json.tech_stack && (
                        (selectedJob.analysis_json.tech_stack.languages?.length > 0 ||
                         selectedJob.analysis_json.tech_stack.frameworks?.length > 0 ||
                         selectedJob.analysis_json.tech_stack.databases?.length > 0 ||
                         selectedJob.analysis_json.tech_stack.tools?.length > 0) && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Tech Stack</h4>
                          <div className={styles.techStackContainer}>
                            {selectedJob.analysis_json.tech_stack.languages && selectedJob.analysis_json.tech_stack.languages.length > 0 && (
                              <div className={styles.techCategory}>
                                <div className={styles.techCategoryLabel}>Languages</div>
                                <div className={styles.techList}>
                                  {selectedJob.analysis_json.tech_stack.languages.map((tech, idx) => (
                                    <span key={idx} className={styles.techBadge}>
                                      {tech}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {selectedJob.analysis_json.tech_stack.frameworks && selectedJob.analysis_json.tech_stack.frameworks.length > 0 && (
                              <div className={styles.techCategory}>
                                <div className={styles.techCategoryLabel}>Frameworks</div>
                                <div className={styles.techList}>
                                  {selectedJob.analysis_json.tech_stack.frameworks.map((tech, idx) => (
                                    <span key={idx} className={styles.techBadge}>
                                      {tech}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {selectedJob.analysis_json.tech_stack.databases && selectedJob.analysis_json.tech_stack.databases.length > 0 && (
                              <div className={styles.techCategory}>
                                <div className={styles.techCategoryLabel}>Databases</div>
                                <div className={styles.techList}>
                                  {selectedJob.analysis_json.tech_stack.databases.map((tech, idx) => (
                                    <span key={idx} className={styles.techBadge}>
                                      {tech}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {selectedJob.analysis_json.tech_stack.tools && selectedJob.analysis_json.tech_stack.tools.length > 0 && (
                              <div className={styles.techCategory}>
                                <div className={styles.techCategoryLabel}>Tools</div>
                                <div className={styles.techList}>
                                  {selectedJob.analysis_json.tech_stack.tools.map((tech, idx) => (
                                    <span key={idx} className={styles.techBadge}>
                                      {tech}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </section>
                        )
                      )}

                      {/* Education */}
                      {selectedJob.analysis_json.education && selectedJob.analysis_json.education.length > 0 && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Education Requirements</h4>
                          <ul className={styles.list}>
                            {selectedJob.analysis_json.education.map((edu, idx) => (
                              <li key={idx} className={styles.listItemBenefit}>
                                {edu}
                              </li>
                            ))}
                          </ul>
                        </section>
                      )}

                      {/* Human Languages */}
                      {selectedJob.analysis_json.languages && selectedJob.analysis_json.languages.length > 0 && (
                        <section className={styles.section}>
                          <h4 className={styles.sectionTitle}>Language Requirements</h4>
                          <div className={styles.languagesList}>
                            {selectedJob.analysis_json.languages.map((lang, idx) => (
                              <div key={idx} className={styles.languageItem}>
                                <span className={styles.languageName}>{lang.name}</span>
                                {lang.level && (
                                  <span className={styles.languageLevel}>
                                    {lang.level.charAt(0).toUpperCase() + lang.level.slice(1)}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Original Description */}
                      <section className={styles.section}>
                        <h4 className={styles.sectionTitle}>Original Description</h4>
                        <p className={styles.description}>{selectedJob.job_description}</p>
                      </section>
                    </>
                  ) : (
                    <section className={styles.section}>
                      <h4 className={styles.sectionTitle}>Description</h4>
                      <p className={styles.description}>{selectedJob.job_description}</p>
                    </section>
                  )}
                </div>
              </div>
            </div>
          )}
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
                <th>💼 Title</th>
                <th>📅 Experience</th>
                <th>🏢 Stability</th>
                <th>💪 Strengths</th>
                <th>⚠️ Concerns</th>
                <th>✉️ Email</th>
                <th>📞 Phone</th>
                <th>📄 Resume</th>
                <th>📊 Status</th>
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
                    <td>{candidate.title || '—'}</td>
                    <td>{candidate.experience || '0 yrs'}</td>
                    <td>
                      {candidate.stability_score !== undefined ? (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                          <div
                            className={styles.stabilityBadge}
                            style={{
                              backgroundColor: getStabilityBadge(candidate.stability_score).bgColor,
                              color: getStabilityBadge(candidate.stability_score).color,
                            }}
                            title={`Employment Stability: ${candidate.stability_score}%`}
                          >
                            {getStabilityBadge(candidate.stability_score).emoji}
                            <span style={{ marginLeft: '4px', fontSize: '11px', fontWeight: 600 }}>
                              {getStabilityBadge(candidate.stability_score).label}
                            </span>
                          </div>
                          <span style={{ fontSize: '11px', color: '#6b7280', fontWeight: 500 }}>
                            {candidate.stability_score}%
                          </span>
                        </div>
                      ) : (
                        <span style={{ color: '#999' }}>—</span>
                      )}
                    </td>
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
                          <div className={`${styles.aiInsight} ${styles.strengthsInsight} ${expandedStrengths.has(candidate.resume_id) ? styles.visible : ''}`}>
                              {formatAIInsight(candidate.llm_strengths)}
                          </div>
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
                          <div className={`${styles.aiInsight} ${styles.concernsInsight} ${expandedConcerns.has(candidate.resume_id) ? styles.visible : ''}`}>
                              {formatAIInsight(candidate.llm_concerns)}
                          </div>
                        </div>
                      ) : (
                        <div style={{ color: '#10b981', fontStyle: 'italic', padding: '8px' }}>
                          ✓ No significant concerns
                        </div>
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
                    <td>
                      <div className={styles.statusContainer}>
                        <select
                          className={styles.statusSelect}
                          value={candidate.status || 'new'}
                          onChange={(e) => handleStatusChange(candidate.resume_id, e.target.value)}
                          style={{
                            backgroundColor: getStatusBadge(candidate.status).bg,
                            color: getStatusBadge(candidate.status).color,
                          }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <option value="new">🕐 New</option>
                          <option value="reviewed">👁️ Reviewed</option>
                          <option value="shortlisted">✅ Shortlisted</option>
                          <option value="rejected">❌ Rejected</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                  {expandedResumeId === candidate.resume_id && candidate.resume_url && (
                    <tr key={`${candidate.resume_id}-resume`} className={styles.resumeRow}>
                      <td colSpan={11} className={styles.resumeCell}>
                        <div className={styles.resumeContainer}>
                          <ResumePreview 
                            url={`${API_URL}${candidate.resume_url}`} 
                            fileName={candidate.file_name} 
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

