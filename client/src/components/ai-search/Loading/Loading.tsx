import styles from './Loading.module.css'
import { FiShield, FiBarChart2, FiTrendingUp, FiZap } from 'react-icons/fi'
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
  const defaultIcons: readonly IconType[] = [FiShield, FiBarChart2, FiTrendingUp, FiZap]
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
          </div>
        </div>
      </div>
    </section>
  )
}
