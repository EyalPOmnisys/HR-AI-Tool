import type { ReactElement } from 'react'
import styles from './JobCard.module.css'

export const JobCardSkeleton = (): ReactElement => {
  return (
    <div className={`${styles.card} ${styles.skeletonCard}`}>
      <div className={styles.header}>
        <div className={`${styles.icon} ${styles.skeletonBox}`} />
        <div style={{ flex: 1 }}>
          <div className={`${styles.skeletonText}`} style={{ width: '70%', height: '24px', marginBottom: '8px' }} />
          <div className={`${styles.skeletonText}`} style={{ width: '40%', height: '14px' }} />
        </div>
      </div>
      
      <div className={styles.body} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
        <div className={`${styles.skeletonText}`} style={{ width: '100%' }} />
        <div className={`${styles.skeletonText}`} style={{ width: '95%' }} />
        <div className={`${styles.skeletonText}`} style={{ width: '90%' }} />
        <div className={`${styles.skeletonText}`} style={{ width: '60%' }} />
      </div>

      <div className={styles.footer} style={{ marginTop: 'auto', display: 'flex', gap: '8px' }}>
        <div className={`${styles.skeletonBadge}`} />
        <div className={`${styles.skeletonBadge}`} />
        <div className={`${styles.skeletonBadge}`} />
      </div>
    </div>
  )
}
