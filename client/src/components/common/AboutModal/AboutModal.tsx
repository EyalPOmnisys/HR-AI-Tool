import { createPortal } from 'react-dom'
import type { ReactElement } from 'react'
import styles from './AboutModal.module.css'
import logo from '../../../assets/logo.png'
import { APP_VERSION, CHANGELOG } from '../../../data/changelog'

interface AboutModalProps {
  isOpen: boolean
  onClose: () => void
}

export const AboutModal = ({ isOpen, onClose }: AboutModalProps): ReactElement | null => {
  if (!isOpen) return null

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.logo} aria-hidden>
            <img src={logo} alt="OmniAI HR logo" />
          </div>
          <div className={styles.headerText}>
            <h3 className={styles.title}>OmniAI HR</h3>
            <span className={styles.subtitle}>AI-Powered Hiring Platform</span>
          </div>
          <span className={styles.versionBadge}>v{APP_VERSION}</span>
        </div>

        <div className={styles.divider} />

        <h4 className={styles.sectionTitle}>What&apos;s New</h4>
        <div className={styles.changelog}>
          {CHANGELOG.map((entry) => (
            <div key={entry.version} className={styles.entry}>
              <div className={styles.entryHeader}>
                <span className={styles.entryVersion}>v{entry.version}</span>
                <span className={styles.entryDate}>{entry.date}</span>
              </div>
              <ul className={styles.highlights}>
                {entry.highlights.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className={styles.actions}>
          <button className={styles.closeButton} onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
