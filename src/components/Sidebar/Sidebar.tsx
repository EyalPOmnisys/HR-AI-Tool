import styles from './Sidebar.module.css'

type SidebarProps = {
  open: boolean
  onToggle: () => void
  activeItem: string
}

const navigationItems = [
  {
    id: 'job-board',
    icon: '📋',
    label: 'Job Board'
  }
]

export const Sidebar = ({ open, onToggle, activeItem }: SidebarProps) => {
  return (
    <aside className={`${styles.sidebar} ${open ? styles.open : styles.collapsed}`}>
      <div className={styles.inner}>
        <div className={styles.topSection}>
          <div className={styles.branding}>
            <div className={styles.logo} aria-hidden>
              AI
            </div>
            {open && (
              <div className={styles.brandText}>
                <span className={styles.projectName}>TalentPulse</span>
                <span className={styles.projectDescriptor}>Hiring Assistant</span>
              </div>
            )}
          </div>
          <button
            type="button"
            className={styles.toggle}
            onClick={onToggle}
            aria-label={open ? 'Collapse sidebar' : 'Expand sidebar'}
            aria-expanded={open}
          >
            <span aria-hidden>{open ? '‹' : '›'}</span>
          </button>
        </div>

        <nav className={styles.navigation} aria-label="Main navigation">
          {open && <p className={styles.navLabel}>Overview</p>}
          <ul className={styles.navList}>
            {navigationItems.map((item) => {
              const isActive = item.label === activeItem
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                    title={item.label}
                  >
                    <span className={styles.navIcon} aria-hidden>
                      {item.icon}
                    </span>
                    {open && <span className={styles.navText}>{item.label}</span>}
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        <div className={styles.bottomSection}>
          <div className={styles.accountCard}>
            <div className={styles.avatar} aria-hidden>
              LB
            </div>
            {open && (
              <div className={styles.accountText}>
                <span className={styles.accountName}>Liora Bergman</span>
                <span className={styles.accountRole}>Hiring Manager</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  )
}

