import styles from './Sidebar.module.css'
import type { ReactNode, ReactElement } from 'react'
import type { ScreenId } from '../../types/navigation'
import logo from '../../assets/logo.png'
import { IoFileTrayStackedSharp, IoSparklesSharp } from 'react-icons/io5'
import { MdOutlineWorkOutline } from 'react-icons/md'

type SidebarProps = {
  open: boolean
  onToggle: () => void
  onSelect: (itemId: ScreenId) => void
  activeItem: ScreenId
}

type NavItem = {
  id: ScreenId
  icon: ReactNode
  label: string
}

const navigationItems: readonly NavItem[] = [
  {
    id: 'ai-search',
    icon: <IoSparklesSharp size={18} />,
    label: 'AI Search'
  },
  {
    id: 'job-board',
    icon: <MdOutlineWorkOutline size={18} />,
    label: 'Jobs'
  },
  {
    id: 'resumes',
    icon: <IoFileTrayStackedSharp size={18} />,
    label: 'Resumes'
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

export const Sidebar = ({ open, onToggle, activeItem, onSelect }: SidebarProps): ReactElement => {
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
              const isActive = item.id === activeItem
              return (
                <li key={item.id}>
                  <button
                    type='button'
                    className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                    title={item.label}
                    onClick={() => onSelect(item.id)}
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
