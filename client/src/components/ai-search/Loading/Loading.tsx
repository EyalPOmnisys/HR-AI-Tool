import styles from './Loading.module.css'
import type { IconType } from 'react-icons'
import type { ReactElement } from 'react'
import { loadingIcons } from '../../../data/loadingMessages'

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
  const iconList = icons?.length ? icons : loadingIcons
  const Icon = iconList[activeIndex % iconList.length]
  
  // Calculate progress percentage (0-100) based on active message
  const progress = ((activeIndex + 1) / messages.length) * 100

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
            
            <div className={styles.progressContainer}>
              <div className={styles.progressBar}>
                <div 
                  className={styles.progressFill} 
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className={styles.progressText}>
                {Math.round(progress)}%
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
