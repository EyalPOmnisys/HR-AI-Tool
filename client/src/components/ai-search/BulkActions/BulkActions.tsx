import { FiCheck } from 'react-icons/fi'
import styles from './BulkActions.module.css'

type Props = {
  selectedCount: number
  bulkStatusValue: string
  onStatusChange: (status: string) => void
  onApply: () => void
  onClear: () => void
}

export default function BulkActions({ 
  selectedCount, 
  bulkStatusValue, 
  onStatusChange, 
  onApply, 
  onClear 
}: Props) {
  if (selectedCount === 0) return null

  // Get background gradient based on selected status
  const getStatusBackground = () => {
    switch (bulkStatusValue) {
      case 'new':
        return 'linear-gradient(to right, #f1f5f9 0%, #ffffff 100%)'
      case 'reviewed':
        return 'linear-gradient(to right, #dbeafe 0%, #ffffff 100%)'
      case 'shortlisted':
        return 'linear-gradient(to right, #d1fae5 0%, #ffffff 100%)'
      case 'rejected':
        return 'linear-gradient(to right, #fee2e2 0%, #ffffff 100%)'
      default:
        return 'linear-gradient(to right, #f8fafc 0%, #ffffff 100%)'
    }
  }

  return (
    <div className={styles.bulkActionsBar} style={{ background: getStatusBackground() }}>
      <div className={styles.bulkInfo}>
        <FiCheck size={16} />
        <span>{selectedCount} selected</span>
      </div>
      <div className={styles.bulkControls}>
        <select
          value={bulkStatusValue}
          onChange={(e) => onStatusChange(e.target.value)}
          className={styles.bulkStatusSelect}
        >
          <option value="new">🕐 New</option>
          <option value="reviewed">👁️ Reviewed</option>
          <option value="shortlisted">✅ Shortlisted</option>
          <option value="rejected">❌ Rejected</option>
        </select>
        <button
          onClick={onApply}
          className={styles.bulkApplyButton}
        >
          Apply to Selected
        </button>
        <button
          onClick={onClear}
          className={styles.bulkClearButton}
        >
          Clear Selection
        </button>
      </div>
    </div>
  )
}
