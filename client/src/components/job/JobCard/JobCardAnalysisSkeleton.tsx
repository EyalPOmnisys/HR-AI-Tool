import { Skeleton, SkeletonText, SkeletonChipRow } from '../../common/Skeleton/Skeleton'
import styles from './JobCard.module.css'

export const JobCardAnalysisSkeleton = () => {
  return (
    <div className={styles.skeletonWrap}>
      {/* summary lines */}
      <SkeletonText lines={3} />
      {/* locations chips */}
      <SkeletonChipRow chips={2} style={{ marginTop: 8 }} />
      {/* requirements list */}
      <div style={{ marginTop: 8 }}>
        <div className={styles.sectionLabel}>Key Requirements:</div>
        <ul className={styles.requirementsList}>
          <li className={styles.requirementItem}><Skeleton width={80} height={10} /></li>
          <li className={styles.requirementItem}><Skeleton width={120} height={10} /></li>
          <li className={styles.requirementItem}><Skeleton width={100} height={10} /></li>
        </ul>
      </div>
      {/* skills rows */}
      <div className={styles.skills} style={{ marginTop: 8 }}>
        <div className={styles.sectionLabel}>Must Have:</div>
        <SkeletonChipRow chips={4} />
      </div>
      <div className={styles.skills} style={{ marginTop: 8 }}>
        <div className={styles.sectionLabel}>Nice to Have:</div>
        <SkeletonChipRow chips={3} />
      </div>
      {/* tech row */}
      <div className={styles.techStack} style={{ marginTop: 8 }}>
        <div className={styles.sectionLabel}>Tech Stack:</div>
        <SkeletonChipRow chips={5} />
      </div>
    </div>
  )
}
