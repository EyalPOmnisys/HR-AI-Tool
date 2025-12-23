import { useState, useRef, useEffect, type ReactElement, type MouseEvent } from 'react'
import { FaTrash, FaEye, FaChevronDown, FaSpinner, FaChevronLeft, FaChevronRight } from 'react-icons/fa'
import type { ResumeSummary, ResumeScore } from '../../../types/resume'
import styles from './ResumeTable.module.css'

export type TimeFilter = 'all' | 'today' | 'week' | 'month'

interface ResumeTableProps {
  resumes: (ResumeSummary & { createdAt?: string })[]
  scores?: Record<string, ResumeScore>
  isScoring?: boolean
  selectedResumeId: string | null
  onSelect: (resumeId: string) => void
  onDelete: (resume: ResumeSummary, e: MouseEvent) => void
  timeFilter: TimeFilter
  onTimeFilterChange: (filter: TimeFilter) => void
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export const ResumeTable = ({
  resumes,
  scores,
  isScoring,
  selectedResumeId,
  onSelect,
  onDelete,
  timeFilter,
  onTimeFilterChange,
  currentPage,
  totalPages,
  onPageChange,
}: ResumeTableProps): ReactElement => {
  const [isFilterOpen, setIsFilterOpen] = useState(false)
  const filterRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: globalThis.MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
        setIsFilterOpen(false)
      }
    }

    if (isFilterOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isFilterOpen])

  const handleFilterClick = (e: MouseEvent) => {
    e.stopPropagation()
    setIsFilterOpen(!isFilterOpen)
  }

  const handleFilterSelect = (filter: TimeFilter) => {
    onTimeFilterChange(filter)
    setIsFilterOpen(false)
  }

  const getFilterLabel = (filter: TimeFilter) => {
    switch (filter) {
      case 'today': return 'Added Today'
      case 'week': return 'Added This Week'
      case 'month': return 'Added This Month'
      default: return 'Date'
    }
  }

  const renderExperience = (resume: ResumeSummary) => {
    if (resume.yearsByCategory && Object.keys(resume.yearsByCategory).length > 0) {
      const validCategories = Object.entries(resume.yearsByCategory)
        .filter(([, years]) => typeof years === 'number' && years > 0)
        .sort((a, b) => b[1] - a[1])
      
      if (validCategories.length > 0) {
        return (
          <div className={styles.experienceCell}>
            {validCategories.map(([category, years]) => (
              <span key={category} className={styles.experienceTag}>
                {category}: {years}y
              </span>
            ))}
          </div>
        )
      }
    }
    return resume.yearsOfExperience ? `${resume.yearsOfExperience} years` : '-'
  }

  const showScoring = isScoring || (scores && Object.keys(scores).length > 0)

  const getPageNumbers = () => {
    const pages = []
    let start = Math.max(1, currentPage - 2)
    let end = Math.min(totalPages, start + 4)
    
    if (end - start < 4) {
      start = Math.max(1, end - 4)
    }

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
    return pages
  }

  return (
    <div className={styles.tableContainer}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Name</th>
            {showScoring && (
              <>
                <th>Score</th>
                <th>Reason</th>
              </>
            )}
            <th>Profession</th>
            <th>Experience</th>
            <th>
              <div 
                className={`${styles.dateHeader} ${timeFilter !== 'all' ? styles.activeFilter : ''}`}
                onClick={handleFilterClick}
                ref={filterRef}
              >
                <span>{getFilterLabel(timeFilter)}</span>
                <FaChevronDown className={styles.filterIcon} />
                
                {isFilterOpen && (
                  <div className={styles.filterMenu}>
                    <button 
                      className={`${styles.filterOption} ${timeFilter === 'all' ? styles.activeOption : ''}`}
                      onClick={(e) => { e.stopPropagation(); handleFilterSelect('all'); }}
                    >
                      All Time
                    </button>
                    <button 
                      className={`${styles.filterOption} ${timeFilter === 'today' ? styles.activeOption : ''}`}
                      onClick={(e) => { e.stopPropagation(); handleFilterSelect('today'); }}
                    >
                      Added Today
                    </button>
                    <button 
                      className={`${styles.filterOption} ${timeFilter === 'week' ? styles.activeOption : ''}`}
                      onClick={(e) => { e.stopPropagation(); handleFilterSelect('week'); }}
                    >
                      Added This Week
                    </button>
                    <button 
                      className={`${styles.filterOption} ${timeFilter === 'month' ? styles.activeOption : ''}`}
                      onClick={(e) => { e.stopPropagation(); handleFilterSelect('month'); }}
                    >
                      Added This Month
                    </button>
                  </div>
                )}
              </div>
            </th>
            <th className={styles.actionsHeader}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {resumes.map((resume) => {
            const isActive = resume.id === selectedResumeId
            const date = resume.createdAt 
              ? new Date(resume.createdAt).toLocaleString('he-IL', { 
                  year: 'numeric', 
                  month: 'numeric', 
                  day: 'numeric', 
                  hour: '2-digit', 
                  minute: '2-digit',
                  timeZone: 'Asia/Jerusalem'
                }) 
              : '-'
            
            return (
              <tr 
                key={resume.id} 
                className={`${styles.row} ${isActive ? styles.selectedRow : ''}`}
                onClick={() => onSelect(resume.id)}
              >
                <td className={styles.nameCell}>
                  <div className={styles.nameWrapper}>
                    <span className={styles.nameText}>{resume.name || 'Unnamed'}</span>
                  </div>
                </td>
                {showScoring && (
                  <>
                    <td>
                      {scores && scores[resume.id] ? (
                        <div 
                          title={scores[resume.id].reason}
                          style={{
                            backgroundColor: scores[resume.id].score >= 80 ? '#e6fffa' : scores[resume.id].score >= 50 ? '#fffaf0' : '#fff5f5',
                            color: scores[resume.id].score >= 80 ? '#2c7a7b' : scores[resume.id].score >= 50 ? '#c05621' : '#c53030',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontWeight: 'bold',
                            display: 'inline-block',
                            fontSize: '0.85rem'
                          }}
                        >
                          {scores[resume.id].score}%
                        </div>
                      ) : isScoring ? (
                        <FaSpinner className={styles.spinner} title="Calculating score..." />
                      ) : '-'}
                    </td>
                    <td className={styles.reasonCell}>
                      {scores && scores[resume.id] ? (
                        <span title={scores[resume.id].reason}>
                          {scores[resume.id].reason}
                        </span>
                      ) : isScoring ? (
                        <FaSpinner className={styles.spinner} title="Analyzing..." />
                      ) : '-'}
                    </td>
                  </>
                )}
                <td>{resume.profession || '-'}</td>
                <td>{renderExperience(resume)}</td>
                <td>{date}</td>
                <td className={styles.actionsCell}>
                  <button 
                    className={styles.actionButton}
                    onClick={(e) => {
                      e.stopPropagation()
                      onSelect(resume.id)
                    }}
                    title="View Details"
                  >
                    <FaEye />
                  </button>
                  <button 
                    className={`${styles.actionButton} ${styles.deleteButton}`}
                    onClick={(e) => onDelete(resume, e)}
                    title="Delete Resume"
                  >
                    <FaTrash />
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button 
            className={styles.pageButton} 
            disabled={currentPage === 1}
            onClick={() => onPageChange(currentPage - 1)}
          >
            <FaChevronLeft />
          </button>
          
          {getPageNumbers().map(pageNum => (
            <button
              key={pageNum}
              className={`${styles.pageButton} ${currentPage === pageNum ? styles.activePage : ''}`}
              onClick={() => onPageChange(pageNum)}
            >
              {pageNum}
            </button>
          ))}

          <button 
            className={styles.pageButton} 
            disabled={currentPage === totalPages}
            onClick={() => onPageChange(currentPage + 1)}
          >
            <FaChevronRight />
          </button>
        </div>
      )}
    </div>
  )
}
