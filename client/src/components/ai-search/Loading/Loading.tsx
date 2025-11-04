import styles from './Loading.module.css'
import { 
  FiSearch, 
  FiCpu, 
  FiZap, 
  FiTrendingUp, 
  FiCheckCircle, 
  FiLayers,
  FiTarget,
  FiBarChart2,
  FiDatabase,
  FiFilter
} from 'react-icons/fi'
import type { IconType } from 'react-icons'
import type { ReactElement } from 'react'

type Props = {
  messages: readonly string[]
  activeIndex: number
  sublabel?: string
  icons?: readonly IconType[]
}

export default function Loading({
  messages,
  activeIndex,
  sublabel = 'Processing real-time information to generate insights',
  icons
}: Props): ReactElement {
  const defaultIcons: readonly IconType[] = [
    FiSearch,      // 0-2s: חיפוש
    FiDatabase,    // 2-4s: טעינת מאגר
    FiCpu,         // 4-6s: עיבוד AI
    FiFilter,      // 6-8s: סינון
    FiLayers,      // 8-10s: ניתוח שכבות
    FiTarget,      // 10-12s: התאמה
    FiBarChart2,   // 12-14s: אנליזה
    FiTrendingUp,  // 14-16s: דירוג
    FiZap,         // 16-18s: אופטימיזציה
    FiCheckCircle  // 18-20s: סיום
  ]
  const iconList = (icons?.length ? icons : defaultIcons) as readonly IconType[]
  const Icon = iconList[activeIndex % iconList.length]

  return (
    <section className={styles.wrap} aria-live="polite" aria-busy="true">
      <div className={styles.card}>
        <div className={styles.stack}>
          <div className={styles.iconShell} key={`icon-${activeIndex}`}>
            <span className={styles.ringOuter} />
            <span className={styles.ringInner} />
            <Icon className={styles.icon} aria-hidden />
          </div>

          <div className={styles.textBlock}>
            <p className={styles.title} key={`title-${activeIndex}`}>
              {messages[activeIndex] ?? messages[0]}
            </p>
            <p className={styles.subtitle}>{sublabel}</p>
            
            <div className={styles.dotsContainer}>
              <span className={styles.dot} />
              <span className={styles.dot} />
              <span className={styles.dot} />
              <span className={styles.dot} />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
