import styles from './Sidebar.module.css'
import type { ReactNode } from 'react'
import logo from '../../assets/logo.png'

type SidebarProps = {
  open: boolean
  onToggle: () => void
  activeItem: string
}

const DocIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    <path d="M14 3v5h5" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    <path d="M9 13h6M9 17h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </svg>
)

type NavItem = {
  id: string
  icon: ReactNode
  label: string
}

const navigationItems: NavItem[] = [
  {
    id: 'job-board',
    icon: <DocIcon />,
    label: 'Job Board'
  }
]

const ChevronIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path
      d="M10 7l5 5-5 5"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const Sidebar = ({ open, onToggle, activeItem }: SidebarProps) => {
  return (
    <aside className={`${styles.sidebar} ${open ? styles.open : styles.collapsed}`}>
      <div className={styles.inner}>
        <div className={styles.topSection}>
          <div className={styles.branding}>
            <div className={styles.logo} aria-hidden>
              <img src={logo} alt='TalentPulse logo' />
            </div>
            <div className={styles.brandText}>
              <span className={styles.projectName}>TalentPulse</span>
              <span className={styles.projectDescriptor}>Hiring Assistant</span>
            </div>
          </div>
        </div>

        <nav className={styles.navigation} aria-label='Main navigation'>
          <ul className={styles.navList}>
            {navigationItems.map((item) => {
              const isActive = item.label === activeItem
              return (
                <li key={item.id}>
                  <button
                    type='button'
                    className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                    title={item.label}
                  >
                    <span className={styles.navIcon} aria-hidden>
                      {item.icon}
                    </span>
                    <span className={styles.navText}>{item.label}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        <div className={styles.bottomSection}>
          <button
            type='button'
            className={styles.toggle}
            onClick={onToggle}
            aria-label={open ? 'Collapse sidebar' : 'Expand sidebar'}
            aria-expanded={open}
          >
            <span className={`${styles.toggleIcon} ${open ? styles.toggleIconOpen : ''}`} aria-hidden>
              <ChevronIcon />
            </span>
          </button>
        </div>
      </div>
    </aside>
  )
}
