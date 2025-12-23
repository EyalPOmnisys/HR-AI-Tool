import type { ReactElement } from 'react'
import tableStyles from './ResumeTable.module.css'
import skeletonStyles from './ResumeTableSkeleton.module.css'
import { FaChevronDown } from 'react-icons/fa'

export const ResumeTableSkeleton = (): ReactElement => {
  return (
    <div className={tableStyles.tableContainer}>
      <table className={tableStyles.table}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Profession</th>
            <th>Experience</th>
            <th>
              <div className={tableStyles.dateHeader}>
                <span>Date</span>
                <FaChevronDown className={tableStyles.filterIcon} />
              </div>
            </th>
            <th className={tableStyles.actionsHeader}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 20 }).map((_, index) => (
            <tr key={index} className={tableStyles.row}>
              <td className={tableStyles.nameCell}>
                <div className={`${skeletonStyles.skeletonCell} ${skeletonStyles.skeletonName} ${skeletonStyles.skeletonRow}`} />
              </td>
              <td>
                <div className={`${skeletonStyles.skeletonCell} ${skeletonStyles.skeletonProfession} ${skeletonStyles.skeletonRow}`} />
              </td>
              <td>
                <div className={`${skeletonStyles.skeletonCell} ${skeletonStyles.skeletonExperience} ${skeletonStyles.skeletonRow}`} />
              </td>
              <td>
                <div className={`${skeletonStyles.skeletonCell} ${skeletonStyles.skeletonDate} ${skeletonStyles.skeletonRow}`} />
              </td>
              <td className={tableStyles.actionsCell}>
                <div className={`${skeletonStyles.skeletonCell} ${skeletonStyles.skeletonActions} ${skeletonStyles.skeletonRow}`} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
