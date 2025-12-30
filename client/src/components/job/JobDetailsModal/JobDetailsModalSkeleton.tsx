import type { ReactElement } from 'react'
import { Skeleton, SkeletonText, SkeletonChipRow } from '../../common/Skeleton/Skeleton'
import styles from './JobDetailsModal.module.css'

export const JobDetailsModalSkeleton = (): ReactElement => {
  return (
    <>
      {/* Summary Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Summary</h3>
        <div style={{ marginTop: 12 }}>
          <SkeletonText lines={4} lineHeight={16} gap={8} />
        </div>
      </section>

      {/* Position Details Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Position Details</h3>
        <div className={styles.metaInfo} style={{ marginTop: 12 }}>
          <div className={styles.metaItem}>
            <Skeleton width={20} height={20} radius={4} />
            <Skeleton width={120} height={16} />
          </div>
          <div className={styles.metaItem}>
            <Skeleton width={20} height={20} radius={4} />
            <Skeleton width={150} height={16} />
          </div>
        </div>
      </section>

      {/* Locations Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Locations</h3>
        <div style={{ marginTop: 12 }}>
          <SkeletonChipRow chips={2} chipWidth={90} chipHeight={28} gap={8} />
        </div>
      </section>

      {/* Requirements Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Key Requirements</h3>
        <ul className={styles.list} style={{ marginTop: 12 }}>
          <li className={styles.listItem}>
            <Skeleton width="85%" height={14} />
          </li>
          <li className={styles.listItem}>
            <Skeleton width="92%" height={14} />
          </li>
          <li className={styles.listItem}>
            <Skeleton width="78%" height={14} />
          </li>
          <li className={styles.listItem}>
            <Skeleton width="88%" height={14} />
          </li>
        </ul>
      </section>

      {/* Responsibilities Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Responsibilities</h3>
        <ul className={styles.list} style={{ marginTop: 12 }}>
          <li className={styles.listItem}>
            <Skeleton width="90%" height={14} />
          </li>
          <li className={styles.listItem}>
            <Skeleton width="83%" height={14} />
          </li>
          <li className={styles.listItem}>
            <Skeleton width="95%" height={14} />
          </li>
        </ul>
      </section>

      {/* Must Have Skills Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Must Have Skills</h3>
        <div style={{ marginTop: 12 }}>
          <SkeletonChipRow chips={5} chipWidth={80} chipHeight={26} gap={8} />
        </div>
      </section>

      {/* Nice to Have Skills Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Nice to Have Skills</h3>
        <div style={{ marginTop: 12 }}>
          <SkeletonChipRow chips={4} chipWidth={75} chipHeight={26} gap={8} />
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Tech Stack</h3>
        <div className={styles.techStackContainer} style={{ marginTop: 12 }}>
          <div className={styles.techCategory}>
            <div className={styles.techCategoryLabel}>Languages</div>
            <SkeletonChipRow chips={3} chipWidth={70} chipHeight={26} gap={8} />
          </div>
          <div className={styles.techCategory}>
            <div className={styles.techCategoryLabel}>Frameworks</div>
            <SkeletonChipRow chips={4} chipWidth={85} chipHeight={26} gap={8} />
          </div>
          <div className={styles.techCategory}>
            <div className={styles.techCategoryLabel}>Databases</div>
            <SkeletonChipRow chips={2} chipWidth={95} chipHeight={26} gap={8} />
          </div>
          <div className={styles.techCategory}>
            <div className={styles.techCategoryLabel}>Tools</div>
            <SkeletonChipRow chips={3} chipWidth={80} chipHeight={26} gap={8} />
          </div>
        </div>
      </section>

      {/* Education Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Education Requirements</h3>
        <ul className={styles.list} style={{ marginTop: 12 }}>
          <li className={styles.listItemBenefit}>
            <Skeleton width="75%" height={14} />
          </li>
          <li className={styles.listItemBenefit}>
            <Skeleton width="82%" height={14} />
          </li>
        </ul>
      </section>

      {/* Language Requirements Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Language Requirements</h3>
        <div style={{ marginTop: 12 }}>
          <div className={styles.languagesList}>
            <div className={styles.languageItem}>
              <Skeleton width={60} height={14} />
              <Skeleton width={40} height={12} radius={4} />
            </div>
            <div className={styles.languageItem}>
              <Skeleton width={55} height={14} />
              <Skeleton width={35} height={12} radius={4} />
            </div>
          </div>
        </div>
      </section>
    </>
  )
}