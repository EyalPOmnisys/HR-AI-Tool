import type { ReactElement } from 'react'
import styles from './Form.module.css'

export const JobDetailsSkeleton = (): ReactElement => {
  return (
    <div className={styles.right} style={{ height: '100%' }}>
      <div className={styles.jobHeader}>
        <div className={styles.jobHeaderTop}>
          <div className={`${styles.jobIcon} ${styles.skeletonBox}`} style={{ width: '32px', height: '32px' }} />
          <div className={`${styles.skeletonText}`} style={{ width: '40%', height: '32px' }} />
        </div>

        <div className={styles.jobMetaRow}>
          <div className={styles.skeletonPill} style={{ width: '120px' }} />
          <div className={styles.skeletonPill} style={{ width: '100px' }} />
          <div className={styles.skeletonPill} style={{ width: '140px' }} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
          <div className={`${styles.skeletonText}`} style={{ width: '100%' }} />
          <div className={`${styles.skeletonText}`} style={{ width: '95%' }} />
          <div className={`${styles.skeletonText}`} style={{ width: '90%' }} />
        </div>
      </div>

      <div className={styles.section}>
        <div className={`${styles.skeletonText}`} style={{ width: '30%', height: '20px', marginBottom: '12px' }} />
        <div className={styles.metaRow} style={{ display: 'flex', gap: '8px' }}>
          <div className={styles.skeletonPill} style={{ width: '150px' }} />
          <div className={styles.skeletonPill} style={{ width: '120px' }} />
        </div>
      </div>

      <div className={styles.section}>
        <div className={`${styles.skeletonText}`} style={{ width: '25%', height: '20px', marginBottom: '12px' }} />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          <div className={styles.skeletonPill} style={{ width: '80px' }} />
          <div className={styles.skeletonPill} style={{ width: '100px' }} />
          <div className={styles.skeletonPill} style={{ width: '90px' }} />
          <div className={styles.skeletonPill} style={{ width: '110px' }} />
          <div className={styles.skeletonPill} style={{ width: '70px' }} />
        </div>
      </div>

      <div className={styles.section}>
        <div className={`${styles.skeletonText}`} style={{ width: '25%', height: '20px', marginBottom: '12px' }} />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          <div className={styles.skeletonPill} style={{ width: '90px' }} />
          <div className={styles.skeletonPill} style={{ width: '120px' }} />
          <div className={styles.skeletonPill} style={{ width: '80px' }} />
        </div>
      </div>
    </div>
  )
}
