// src/components/Resume/ResumeDetail/ResumeDetailPanel.tsx
// -----------------------------------------------------------------------------
// Shows Primary years (if provided) and a per-category breakdown (chips).
// Falls back to legacy yearsOfExperience when primaryYears is null.
// -----------------------------------------------------------------------------
import { useMemo, type ReactElement, useEffect, useRef } from 'react';
import { renderAsync } from 'docx-preview';
import { localizeILPhone, formatILPhoneDisplay } from '../../../utils/phone';

import type { ResumeDetail, SkillItem } from '../../../types/resume';
import styles from './ResumeDetailPanel.module.css';

type ResumeDetailPanelProps = {
  resume: ResumeDetail | null;
  isOpen: boolean;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
  onRetry: () => void;
};

const contactIcon = (type: string): string => {
  const key = type.toLowerCase();
  if (key === 'email') return '✉️';
  if (key === 'phone') return '📞';
  return '🔗';
};


export const ResumeDetailPanel = ({
  resume,
  isOpen,
  isLoading,
  error,
  onClose,
  onRetry,
}: ResumeDetailPanelProps): ReactElement | null => {
  if (!isOpen) return null;

  const primaryTitle = resume?.name ?? 'Candidate';
  const secondaryTitle = resume?.profession ?? null;

  const srcForEmbed = useMemo(() => {
    if (!resume?.resumeUrl) return '';
    const stamp = resume.updatedAt ?? String(Date.now());
    const sep = resume.resumeUrl.includes('?') ? '&' : '?';
    
    // For PDF files, add PDF-specific viewer parameters
    const isPdf = resume.mimeType?.toLowerCase().includes('pdf') || 
                  resume.fileName?.toLowerCase().endsWith('.pdf');
    
    if (isPdf) {
      const hash = '#page=1&zoom=page-fit';
      return `${resume.resumeUrl}${sep}t=${encodeURIComponent(stamp)}${hash}`;
    }
    
    // For DOCX/TXT (now returned as HTML), just add cache buster
    return `${resume.resumeUrl}${sep}t=${encodeURIComponent(stamp)}`;
  }, [resume?.resumeUrl, resume?.updatedAt, resume?.mimeType, resume?.fileName]);

  const isDocx = useMemo(() => {
    return resume?.mimeType?.toLowerCase().includes('wordprocessingml') || 
           resume?.fileName?.toLowerCase().endsWith('.docx');
  }, [resume?.mimeType, resume?.fileName]);

  const docxContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isDocx && srcForEmbed && docxContainerRef.current) {
      const container = docxContainerRef.current;
      container.innerHTML = ''; // Clear previous content
      
      fetch(srcForEmbed)
        .then(res => {
          if (!res.ok) throw new Error('Failed to load DOCX file');
          return res.blob();
        })
        .then(blob => renderAsync(blob, container, container, {
          className: styles.docxWrapper,
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
          container.innerHTML = `<p class="${styles.error}">Failed to load document preview.</p>`;
        });
    }
  }, [isDocx, srcForEmbed]);

  const contactItems = useMemo(
    () => (resume?.contacts ?? []).filter((c) => c.type === 'email' || c.type === 'phone'),
    [resume?.contacts]
  );

  // NEW: pick primary years (domain-aware), fallback to legacy total
  const primaryYears = resume?.primaryYears ?? resume?.yearsOfExperience ?? null;

  // NEW: years by category chips (hide zeros)
  const categoryChips = useMemo(() => {
    const entries = Object.entries(resume?.yearsByCategory ?? {});
    return entries
      .filter(([, yrs]) => typeof yrs === 'number' && yrs > 0)
      .sort((a, b) => b[1] - a[1]); // largest first
  }, [resume?.yearsByCategory]);

  // Group skills by source
  const skillsBySource = useMemo(() => {
    const grouped = new Map<string, SkillItem[]>();
    
    resume?.skills.forEach((skill) => {
      const source = skill.source || 'other';
      if (!grouped.has(source)) {
        grouped.set(source, []);
      }
      grouped.get(source)!.push(skill);
    });

    // Define source order and display names
    const sourceOrder = ['work_experience', 'projects', 'education', 'skills_list', 'other'];
    const sourceLabels: Record<string, string> = {
      'work_experience': 'From Work Experience',
      'projects': 'From Projects',
      'education': 'From Education',
      'skills_list': 'From Skills List',
      'other': 'Other'
    };

    // Sort by predefined order
    const sortedEntries = Array.from(grouped.entries()).sort(([sourceA], [sourceB]) => {
      const indexA = sourceOrder.indexOf(sourceA);
      const indexB = sourceOrder.indexOf(sourceB);
      return (indexA === -1 ? 999 : indexA) - (indexB === -1 ? 999 : indexB);
    });

    return sortedEntries.map(([source, skills]) => [sourceLabels[source] || source, skills] as const);
  }, [resume?.skills]);

  return (
    <div className={styles.overlay} onClick={onClose}>
      <aside className={styles.panel} aria-label="Resume details" onClick={(e) => e.stopPropagation()}>
        {isLoading ? (
          <div className={styles.stateCard}>
            <span className={styles.loader} aria-hidden />
            <p>Loading resume...</p>
          </div>
        ) : error ? (
          <div className={styles.stateCard}>
            <p className={styles.error}>{error}</p>
            <button type="button" className={styles.retryButton} onClick={onRetry}>
              Try again
            </button>
          </div>
        ) : !resume ? (
          <div className={styles.stateCard}>
            <p>Select a resume to view its full details.</p>
          </div>
        ) : (
          <div className={styles.layout}>
            <div className={styles.infoColumn}>
              <header className={styles.header}>
                <div className={styles.headerLeft}>
                  <h2 className={styles.heading}>{primaryTitle}</h2>
                  {secondaryTitle && <p className={styles.subheading}>{secondaryTitle}</p>}
                </div>
                <div className={styles.headerActions}>
                  <button
                    type="button"
                    className={styles.closeButton}
                    onClick={onClose}
                    aria-label="Close resume panel"
                  >
                    ×
                  </button>
                </div>
              </header>

              {(primaryYears != null || categoryChips.length > 0) && (
                <section className={styles.section}>
                  <h3 className={styles.sectionTitle}>Overview</h3>
                  <ul className={styles.metaList}>
                    {primaryYears != null && (
                      <li>
                        <span className={styles.metaLabel}>Experience (primary)</span>
                        <span className={styles.metaValue}>{primaryYears} years</span>
                      </li>
                    )}
                  </ul>

                  {categoryChips.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                      {categoryChips.map(([cat, yrs]) => (
                        <span key={cat} className={styles.skillChip} title={`${cat}: ${yrs} years`}>
                          {cat}: {yrs}y
                        </span>
                      ))}
                    </div>
                  )}
                </section>
              )}

              {contactItems.length > 0 && (
                <section className={styles.section}>
                  <h3 className={styles.sectionTitle}>Contact</h3>
                  <ul className={styles.contactList}>
                    {contactItems.map((contact) => (
                      <li key={`${contact.type}-${contact.value}`} className={styles.contactItem}>
                        <span className={styles.contactIcon} aria-hidden>
                          {contactIcon(contact.type)}
                        </span>
                        <div>
                          <span className={styles.contactLabel}>
                            {contact.label ? contact.label : contact.type}
                          </span>
                          {contact.type === 'email' ? (
                            <a href={`mailto:${contact.value}`} className={styles.contactLink}>
                              {contact.value}
                            </a>
                          ) : (
                            (() => {
                              const localized = localizeILPhone(contact.value);
                              const display = formatILPhoneDisplay(contact.value) ?? (localized ?? contact.value);
                              return (
                                <a href={`tel:${localized ?? contact.value}`} className={styles.contactLink}>
                                  {display}
                                </a>
                              );
                            })()
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Skills */}
              {resume.skills.length > 0 && (
                <section className={styles.section}>
                  <h3 className={styles.sectionTitle}>Skills</h3>
                  {skillsBySource.map(([sourceLabel, skills]) => (
                    <div key={sourceLabel} style={{ marginBottom: 16 }}>
                      <h4 style={{ 
                        fontSize: '0.85rem', 
                        color: '#64748b', 
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        marginBottom: 8,
                        fontWeight: 600
                      }}>
                        {sourceLabel}
                      </h4>
                      <div className={styles.skillChips}>
                        {skills.map((skill, idx) => (
                          <span 
                            key={`${skill.name}-${idx}`} 
                            className={styles.skillChip}
                            title={skill.category ? `${skill.category} | Weight: ${skill.weight}` : `Weight: ${skill.weight}`}
                          >
                            {skill.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </section>
              )}

              {/* Experience */}
              {resume.experience.length > 0 && (
                <section className={styles.section}>
                  <h3 className={styles.sectionTitle}>Experience</h3>
                  <ul className={styles.timeline}>
                    {resume.experience.map((role, index) => (
                      <li key={`${role.title}-${role.company}-${index}`} className={styles.timelineItem}>
                        <div className={styles.timelineHeading}>
                          <h4 className={styles.roleTitle}>{role.title || 'Role'}</h4>
                          {role.company && <span className={styles.company}>{role.company}</span>}
                        </div>
                        <div className={styles.timelineMeta}>
                          {(role.startDate || role.endDate) && (
                            <span>
                              {role.startDate || 'Unknown'} &ndash; {role.endDate || 'Present'}
                            </span>
                          )}
                          {role.durationYears != null && <span>{role.durationYears} yrs</span>}
                          {role.location && <span>{role.location}</span>}
                        </div>
                        {role.tech.length > 0 && (
                          <div className={styles.techTags}>
                            {role.tech.map((tech) => (
                              <span key={tech} className={styles.techTag}>
                                {tech}
                              </span>
                            ))}
                          </div>
                        )}
                        {role.bullets.length > 0 && (
                          <ul className={styles.bulletList}>
                            {role.bullets.map((bullet, idx) => (
                              <li key={idx}>{bullet}</li>
                            ))}
                          </ul>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Education */}
              {resume.education.length > 0 && (
                <section className={styles.section}>
                  <h3 className={styles.sectionTitle}>Education</h3>
                  <ul className={styles.educationList}>
                    {resume.education.map((item, index) => (
                      <li key={`${item.institution}-${index}`} className={styles.educationItem}>
                        <div>
                          <h4 className={styles.educationInstitution}>{item.institution}</h4>
                          <p className={styles.educationDetails}>
                            {[item.degree, item.field].filter(Boolean).join(' · ')}
                          </p>
                        </div>
                        {(item.startDate || item.endDate) && (
                          <span className={styles.educationDates}>
                            {item.startDate || 'Unknown'} &ndash; {item.endDate || 'Present'}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Languages */}
              {resume.languages.length > 0 && (
                <section className={styles.section}>
                  <h3 className={styles.sectionTitle}>Languages</h3>
                  <p className={styles.metaValue}>{resume.languages.join(', ')}</p>
                </section>
              )}
            </div>

            <div className={styles.pdfWrapper}>
              {isDocx ? (
                <div 
                  ref={docxContainerRef} 
                  className={styles.docxContainer}
                  style={{ 
                    height: '100%', 
                    overflow: 'auto', 
                    backgroundColor: '#f8fafc',
                    padding: '20px' 
                  }} 
                />
              ) : (
                <iframe
                  key={srcForEmbed}
                  src={srcForEmbed}
                  className={styles.pdfFrame}
                  aria-label={resume.fileName ? `Resume preview - ${resume.fileName}` : 'Resume preview'}
                  title={resume.fileName ? `Resume preview - ${resume.fileName}` : 'Resume preview'}
                  allow="fullscreen"
                />
              )}
            </div>
          </div>
        )}
      </aside>
    </div>
  );
};
