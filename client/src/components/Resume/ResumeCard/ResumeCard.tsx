import type { KeyboardEvent, MouseEvent, ReactElement } from 'react'
import { FaUser, FaBriefcase, FaClock, FaExternalLinkAlt } from 'react-icons/fa'
import type { ResumeSummary } from '../../../types/resume'
import styles from './ResumeCard.module.css'

type ResumeCardProps = {
  resume: ResumeSummary
  onSelect?: (resume: ResumeSummary) => void
}

export const ResumeCard = ({ resume, onSelect }: ResumeCardProps): ReactElement => {
  const { name, profession, yearsOfExperience, resumeUrl } = resume
  const displayName = name ?? 'Unnamed candidate'
  // If profession is missing, show a neutral fallback
  const displayProfession = profession ?? 'Candidate'

  const yearsLabel =
    typeof yearsOfExperience === 'number' ? `${yearsOfExperience} years` : 'Not specified'
  const isInteractive = typeof onSelect === 'function'

  const handleSelect = () => {
    if (onSelect) {
      onSelect(resume)
    }
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!isInteractive) return
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      handleSelect()
    }
  }

  const handleLinkClick = (event: MouseEvent<HTMLAnchorElement>) => {
    event.stopPropagation()
  }

  return (
    <article
      className={`${styles.card} ${isInteractive ? styles.clickable : ''}`}
      role={isInteractive ? 'button' : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      onClick={isInteractive ? handleSelect : undefined}
      onKeyDown={handleKeyDown}
    >
      <div className={styles.avatarSection}>
        <div className={styles.avatar}>
          <FaUser className={styles.userIcon} />
        </div>
      </div>

      <div className={styles.content}>
        <div className={styles.header}>
          <h2 className={styles.name} title={displayName}>
            {displayName}
          </h2>
        </div>

        <div className={styles.meta}>
          <div className={`${styles.badge} ${styles.professionBadge}`}>
            <FaBriefcase className={styles.icon} />
            <span title={displayProfession}>{displayProfession}</span>
          </div>

          <div className={styles.badge}>
            <FaClock className={styles.icon} />
            <span>{yearsLabel}</span>
          </div>
        </div>
      </div>

      <div className={styles.footer}>
        <a
          className={styles.link}
          href={resumeUrl}
          target="_blank"
          rel="noreferrer"
          onClick={handleLinkClick}
          title="View resume"
        >
          <span>View CV</span>
          <FaExternalLinkAlt className={styles.linkIcon} />
        </a>
      </div>
    </article>
  )
}
