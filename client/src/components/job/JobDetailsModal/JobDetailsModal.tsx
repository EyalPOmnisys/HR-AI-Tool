import styles from './JobDetailsModal.module.css'
import type { MouseEvent, ReactElement } from 'react'
import type { Job } from '../../../types/job'
import { JobDetailsModalSkeleton } from './JobDetailsModalSkeleton'

type JobDetailsModalProps = {
  open: boolean
  job: Job | null
  onClose: () => void
  onEdit: (job: Job) => void
  onDelete: (jobId: string) => void
}

const CloseIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path
      d="M6 6l12 12M18 6 6 18"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
  </svg>
)

const formatDate = (value: string): string => {
  const date = new Date(value)
  return date.toLocaleDateString('en-US', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

export const JobDetailsModal = ({ open, job, onClose, onEdit, onDelete }: JobDetailsModalProps): ReactElement | null => {
  if (!open || !job) {
    return null
  }

  const handleBackdropClick = () => {
    onClose()
  }

  const handleContentClick = (event: MouseEvent<HTMLDivElement>) => {
    event.stopPropagation()
  }

  const handleEdit = () => {
    onEdit(job)
    onClose()
  }

  const handleDelete = () => {
    onDelete(job.id)
    onClose()
  }

  const analysis = job.analysis
  const mustHaveSkills = analysis?.skills?.must_have ?? []
  const niceToHaveSkills = analysis?.skills?.nice_to_have ?? []
  const locations = analysis?.locations ?? []
  const languages = analysis?.tech_stack?.languages ?? []
  const frameworks = analysis?.tech_stack?.frameworks ?? []
  const databases = analysis?.tech_stack?.databases ?? []
  const tools = analysis?.tech_stack?.tools ?? []
  const requirements = analysis?.requirements ?? []
  const responsibilities = analysis?.responsibilities ?? []
  const education = analysis?.education ?? []
  const humanLanguages = analysis?.languages ?? []
  const experience = analysis?.experience
  const salaryRange = analysis?.salary_range

  // Use AI summary if available, otherwise fall back to original description
  const displayDescription = analysis?.summary || job.description

  // Format experience string
  const experienceText = experience
    ? experience.years_min && experience.years_max
      ? `${experience.years_min}-${experience.years_max} years`
      : experience.years_min
      ? `${experience.years_min}+ years`
      : null
    : null

  // Format salary string
  const salaryText = salaryRange
    ? salaryRange.min && salaryRange.max && salaryRange.currency
      ? `${salaryRange.currency} ${salaryRange.min.toLocaleString()} - ${salaryRange.max.toLocaleString()}`
      : salaryRange.min && salaryRange.currency
      ? `${salaryRange.currency} ${salaryRange.min.toLocaleString()}+`
      : null
    : null

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" onClick={handleBackdropClick}>
      <div className={styles.modal} onClick={handleContentClick}>
        <header className={styles.header}>
          <div className={styles.jobHeader}>
            <div className={styles.iconWrapper} aria-hidden>
              <span>{job.icon}</span>
            </div>
            <div className={styles.titleContent}>
              <h2>{job.title}</h2>
              {analysis?.organization && (
                <p className={styles.organization}>{analysis.organization}</p>
              )}
              <p className={styles.meta}>Posted on {formatDate(job.postedAt)}</p>
            </div>
          </div>
          <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close dialog">
            <CloseIcon />
          </button>
        </header>

        <div className={styles.body}>
          {!analysis ? (
            // Show skeleton while analysis is being generated
            <JobDetailsModalSkeleton />
          ) : (
            <>
              {/* Summary Section */}
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>Summary</h3>
                <p className={styles.description}>{displayDescription}</p>
              </section>

          {/* Experience & Salary Info */}
          {(experienceText || salaryText) && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Position Details</h3>
              <div className={styles.metaInfo}>
                {experienceText && (
                  <div className={styles.metaItem}>
                    <span className={styles.metaIcon}>💼</span>
                    <span className={styles.metaText}>Experience: {experienceText}</span>
                  </div>
                )}
                {salaryText && (
                  <div className={styles.metaItem}>
                    <span className={styles.metaIcon}>💰</span>
                    <span className={styles.metaText}>Salary: {salaryText}</span>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Locations */}
          {locations.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Locations</h3>
              <div className={styles.locations}>
                {locations.map((loc, idx) => (
                  <span key={idx} className={styles.locationBadge}>
                    📍 {loc}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Requirements */}
          {requirements.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Key Requirements</h3>
              <ul className={styles.list}>
                {requirements.map((req, idx) => (
                  <li key={idx} className={styles.listItem}>
                    {req}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Responsibilities */}
          {responsibilities.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Responsibilities</h3>
              <ul className={styles.list}>
                {responsibilities.map((resp, idx) => (
                  <li key={idx} className={styles.listItem}>
                    {resp}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Must Have Skills */}
          {mustHaveSkills.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Must Have Skills</h3>
              <div className={styles.skillsList}>
                {mustHaveSkills.map((skill, idx) => (
                  <span key={idx} className={styles.skillBadge}>
                    {skill}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Nice to Have Skills */}
          {niceToHaveSkills.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Nice to Have Skills</h3>
              <div className={styles.skillsList}>
                {niceToHaveSkills.map((skill, idx) => (
                  <span key={idx} className={styles.skillBadgeOptional}>
                    {skill}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Tech Stack */}
          {(languages.length > 0 || frameworks.length > 0 || databases.length > 0 || tools.length > 0) && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Tech Stack</h3>
              <div className={styles.techStackContainer}>
                {languages.length > 0 && (
                  <div className={styles.techCategory}>
                    <div className={styles.techCategoryLabel}>Languages</div>
                    <div className={styles.techList}>
                      {languages.map((tech, idx) => (
                        <span key={idx} className={styles.techBadge}>
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {frameworks.length > 0 && (
                  <div className={styles.techCategory}>
                    <div className={styles.techCategoryLabel}>Frameworks</div>
                    <div className={styles.techList}>
                      {frameworks.map((tech, idx) => (
                        <span key={idx} className={styles.techBadge}>
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {databases.length > 0 && (
                  <div className={styles.techCategory}>
                    <div className={styles.techCategoryLabel}>Databases</div>
                    <div className={styles.techList}>
                      {databases.map((tech, idx) => (
                        <span key={idx} className={styles.techBadge}>
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {tools.length > 0 && (
                  <div className={styles.techCategory}>
                    <div className={styles.techCategoryLabel}>Tools</div>
                    <div className={styles.techList}>
                      {tools.map((tech, idx) => (
                        <span key={idx} className={styles.techBadge}>
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Education */}
          {education.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Education Requirements</h3>
              <ul className={styles.list}>
                {education.map((edu, idx) => (
                  <li key={idx} className={styles.listItemBenefit}>
                    {edu}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Human Languages */}
          {humanLanguages.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Language Requirements</h3>
              <div className={styles.languagesList}>
                {humanLanguages.map((lang, idx) => (
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

          {/* Candidate Message */}
          {job.freeText && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Additional Notes</h3>
              <p className={styles.freeText}>{job.freeText}</p>
            </section>
          )}
            </>
          )}
        </div>

        <footer className={styles.footer}>
          <button type="button" className={styles.secondary} onClick={handleDelete}>
            Delete
          </button>
          <button type="button" className={styles.primary} onClick={handleEdit}>
            Edit job
          </button>
        </footer>
      </div>
    </div>
  )
}
