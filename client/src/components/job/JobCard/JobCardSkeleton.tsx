import type { ReactElement } from 'react'
import styles from './JobCard.module.css'

export const JobCardSkeleton = (): ReactElement => {
  return (
    <div className={`${styles.card} ${styles.skeletonCard}`}>
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <div className={styles.skeletonBox} style={{ width: 40, height: 40 }} />
          <div className={styles.titleContent} style={{ width: '100%' }}>
            <div className={styles.skeletonText} style={{ width: '70%', height: '20px', marginBottom: '4px' }} />
            <div className={styles.skeletonText} style={{ width: '40%', height: '14px' }} />
          </div>
        </div>
      </div>
      
      <div className={styles.body}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div className={styles.skeletonText} style={{ width: '100%' }} />
          <div className={styles.skeletonText} style={{ width: '95%' }} />
          <div className={styles.skeletonText} style={{ width: '90%' }} />
          <div className={styles.skeletonText} style={{ width: '60%' }} />
        </div>

        <div style={{ marginTop: 'auto', display: 'flex', gap: '8px', paddingTop: '12px' }}>
          <div className={styles.skeletonBadge} />
          <div className={styles.skeletonBadge} />
          <div className={styles.skeletonBadge} />
        </div>
      </div>
    </div>
  )
}
