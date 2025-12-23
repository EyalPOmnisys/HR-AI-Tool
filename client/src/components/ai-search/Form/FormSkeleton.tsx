import type { ReactElement } from 'react'
import styles from './Form.module.css'
import { JobDetailsSkeleton } from './JobDetailsSkeleton'

export const FormSkeleton = (): ReactElement => {
  return (
    <section className={styles.wrapper}>
      <div className={styles.card}>
        <div className={styles.grid}>
          {/* Left Side Skeleton */}
          <div className={styles.left}>
            <div className={styles.formSection}>
              <div className={styles.skeletonText} style={{ width: '60%', height: '20px', marginBottom: '20px' }} />
              
              <div className={styles.field}>
                <div className={styles.skeletonText} style={{ width: '40%', marginBottom: '8px' }} />
                <div className={styles.skeletonBox} style={{ width: '100%', height: '42px', borderRadius: '10px' }} />
              </div>

              <div className={styles.field}>
                <div className={styles.skeletonText} style={{ width: '50%', marginBottom: '8px' }} />
                <div className={styles.skeletonBox} style={{ width: '100%', height: '42px', borderRadius: '10px' }} />
              </div>

              <div className={styles.actions}>
                <div className={styles.skeletonBox} style={{ width: '100%', height: '42px', borderRadius: '10px' }} />
              </div>
            </div>

            <div className={styles.quickStats}>
               <div className={styles.skeletonText} style={{ width: '40%', height: '20px', marginBottom: '16px' }} />
               <div className={styles.statsGrid}>
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className={styles.statCard}>
                      <div className={styles.skeletonText} style={{ width: '40%', height: '24px', margin: '0 auto 8px' }} />
                      <div className={styles.skeletonText} style={{ width: '70%', height: '12px', margin: '0 auto' }} />
                    </div>
                  ))}
               </div>
            </div>
          </div>

          {/* Right Side Skeleton */}
          <JobDetailsSkeleton />
        </div>
      </div>
    </section>
  )
}
