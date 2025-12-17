import styles from './JobCard.module.css'
import type { KeyboardEvent, MouseEvent, ReactElement } from 'react'
import type { Job } from '../../../types/job'
import { JobCardAnalysisSkeleton } from './JobCardAnalysisSkeleton'

type JobCardProps = {
  job: Job
  onEdit: (job: Job) => void
  onDelete: (jobId: string) => void
  onOpen: (job: Job) => void
}

const EditIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
    <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
    <path d="M14.06 6.19l2.12-2.12a1.5 1.5 0 0 1 2.12 0l1.63 1.63a1.5 1.5 0 0 1 0 2.12l-2.12 2.12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const DeleteIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
    <path d="M5 7h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    <path d="M10 3h4a1 1 0 0 1 1 1v2H9V4a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M18 7v11a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
)

export const JobCard = ({ job, onEdit, onDelete, onOpen }: JobCardProps): ReactElement => {
  const handleOpen = () => onOpen(job)

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onOpen(job)
    }
  }

  const handleEdit = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    onEdit(job)
  }

  const handleDelete = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    onDelete(job.id)
  }

  const analysis = job.analysis
  const mustHaveSkills = analysis?.skills?.must_have?.slice(0, 4) ?? []
  const niceToHaveSkills = analysis?.skills?.nice_to_have?.slice(0, 3) ?? []
  const locations = analysis?.locations?.slice(0, 2) ?? []
  const techStack = [
    ...(analysis?.tech_stack?.languages ?? []),
    ...(analysis?.tech_stack?.frameworks ?? []),
    ...(analysis?.tech_stack?.databases ?? []),
  ].slice(0, 5)
  const requirements = analysis?.requirements?.slice(0, 3) ?? []

  // Check if AI analysis is complete (has summary or other AI-generated content)
  const hasAiAnalysis = analysis?.summary || analysis?.organization || 
                        (analysis?.skills?.must_have && analysis.skills.must_have.length > 0)

  // Use AI summary if available, otherwise fall back to original description
  const displayDescription = analysis?.summary || job.description

  return (
    <article
      className={styles.card}
      role="button"
      tabIndex={0}
      onClick={handleOpen}
      onKeyDown={handleKeyDown}
      aria-label={`Open job ${job.title}`}
    >
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <div className={styles.iconWrapper} aria-hidden>
            <span>{job.icon}</span>
          </div>
          <div className={styles.titleContent}>
            <h3 className={styles.title} title={job.title}>{job.title}</h3>
            {analysis?.organization ? (
              <p className={styles.organization} title={analysis.organization}>
                {analysis.organization}
              </p>
            ) : (
              // שומר על הגובה והאיזון גם כשאין ארגון (או עדין בטיפול)
              <span className={styles.organizationPlaceholder} />
            )}
          </div>
        </div>
        <div className={styles.actions}>
          <button type="button" className={styles.actionButton} onClick={handleEdit} aria-label="Edit job"><EditIcon /></button>
          <button type="button" className={styles.actionButton} onClick={handleDelete} aria-label="Delete job"><DeleteIcon /></button>
        </div>
      </header>

      <div className={styles.body}>
        {!hasAiAnalysis ? (
          <>
            {/* סקלטון יעודי עד שה-LLM מחזיר analysis_json */}
            <JobCardAnalysisSkeleton />
            
            {/* Show additional_skills even while loading AI analysis */}
            {job.additionalSkills && job.additionalSkills.length > 0 && (
              <div className={styles.skills} style={{ marginTop: '12px' }}>
                <div className={styles.sectionLabel}>Additional Skills:</div>
                <div className={styles.skillsList}>
                  {job.additionalSkills.map((skill, idx) => (
                    <span key={idx} className={styles.skillBadge} title={skill} style={{ background: '#f0f9ff', border: '1px solid #bfdbfe', color: '#1e40af' }}>
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <p className={styles.description} title={displayDescription}>{displayDescription}</p>

            {locations.length > 0 && (
              <div className={styles.locations}>
                {locations.map((loc, idx) => (
                  <span key={idx} className={styles.locationBadge} title={loc}>
                    📍 {loc}
                  </span>
                ))}
              </div>
            )}

            {requirements.length > 0 && (
              <div className={styles.requirements}>
                <div className={styles.sectionLabel}>Key Requirements:</div>
                <ul className={styles.requirementsList}>
                  {requirements.map((req, idx) => (
                    <li key={idx} className={styles.requirementItem} title={req}>
                      {req}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {mustHaveSkills.length > 0 && (
              <div className={styles.skills}>
                <div className={styles.sectionLabel}>Must Have:</div>
                <div className={styles.skillsList}>
                  {mustHaveSkills.map((skill, idx) => (
                    <span key={idx} className={styles.skillBadge} title={skill}>
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {niceToHaveSkills.length > 0 && (
              <div className={styles.skills}>
                <div className={styles.sectionLabel}>Nice to Have:</div>
                <div className={styles.skillsList}>
                  {niceToHaveSkills.map((skill, idx) => (
                    <span key={idx} className={styles.skillBadgeOptional} title={skill}>
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {techStack.length > 0 && (
              <div className={styles.techStack}>
                <div className={styles.sectionLabel}>Tech Stack:</div>
                <div className={styles.techList}>
                  {techStack.map((tech, idx) => (
                    <span key={idx} className={styles.techBadge} title={tech}>
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {job.additionalSkills && job.additionalSkills.length > 0 && (
              <div className={styles.skills}>
                <div className={styles.sectionLabel}>Additional Skills:</div>
                <div className={styles.skillsList}>
                  {job.additionalSkills.map((skill, idx) => (
                    <span key={idx} className={styles.skillBadge} title={skill} style={{ background: '#f0f9ff', border: '1px solid #bfdbfe', color: '#1e40af' }}>
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </article>
  )
}
