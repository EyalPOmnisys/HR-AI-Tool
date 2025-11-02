import type { ResumeSummary } from '../../../types/resume'
import type { ReactElement } from 'react'
import styles from './ResumeCard.module.css'

type ResumeCardProps = {
  resume: ResumeSummary
}

const ExternalLinkIcon = () => (
  <svg
    className={styles.linkIcon}
    viewBox="0 0 20 20"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path
      d="M11.25 3.75H16.25V8.75"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M8.75 11.25L16.25 3.75"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M9.99998 5H5.83331C4.45259 5 3.33331 6.11929 3.33331 7.5V14.1667C3.33331 15.5474 4.45259 16.6667 5.83331 16.6667H12.5C13.8807 16.6667 15 15.5474 15 14.1667V10"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const ResumeCard = ({ resume }: ResumeCardProps): ReactElement => {
  const { name, resumeUrl } = resume

  return (
    <article className={styles.card}>
      <h2 className={styles.name} title={name}>
        {name}
      </h2>
      <a className={styles.link} href={resumeUrl} target="_blank" rel="noreferrer">
        View CV
        <ExternalLinkIcon />
      </a>
    </article>
  )
}
