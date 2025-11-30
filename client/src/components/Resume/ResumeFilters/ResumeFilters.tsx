import { useState, useRef, useEffect, type ReactElement, type KeyboardEvent } from 'react'
import { FaFilter, FaTimes } from 'react-icons/fa'
import styles from './ResumeFilters.module.css'

export interface FilterState {
  profession: string
  minExperience: string
  maxExperience: string
  skills: string[]
  freeText: string
}

interface ResumeFiltersProps {
  onFilterChange: (filters: FilterState) => void
  initialFilters?: FilterState
}

export const ResumeFilters = ({ onFilterChange, initialFilters }: ResumeFiltersProps): ReactElement => {
  const [isOpen, setIsOpen] = useState(false)
  const [filters, setFilters] = useState<FilterState>(initialFilters || {
    profession: '',
    minExperience: '',
    maxExperience: '',
    skills: [],
    freeText: ''
  })
  const [skillInput, setSkillInput] = useState('')

  const containerRef = useRef<HTMLDivElement>(null)

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleApply = () => {
    onFilterChange(filters)
    setIsOpen(false)
  }

  const handleClear = () => {
    const emptyFilters = {
      profession: '',
      minExperience: '',
      maxExperience: '',
      skills: [],
      freeText: ''
    }
    setFilters(emptyFilters)
    setSkillInput('')
    onFilterChange(emptyFilters)
    setIsOpen(false)
  }

  const handleAddSkill = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && skillInput.trim()) {
      e.preventDefault()
      if (!filters.skills.includes(skillInput.trim())) {
        setFilters(prev => ({
          ...prev,
          skills: [...prev.skills, skillInput.trim()]
        }))
      }
      setSkillInput('')
    }
  }

  const removeSkill = (skillToRemove: string) => {
    setFilters(prev => ({
      ...prev,
      skills: prev.skills.filter(s => s !== skillToRemove)
    }))
  }

  const hasActiveFilters = Boolean(
    filters.profession || 
    filters.minExperience || 
    filters.maxExperience || 
    filters.skills.length > 0 || 
    filters.freeText
  )

  return (
    <div className={styles.container} ref={containerRef}>
      <button 
        className={`${styles.filterButton} ${hasActiveFilters ? styles.active : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        <FaFilter />
        Filters
      </button>

      {isOpen && (
        <div className={styles.popover}>
          <div className={styles.section}>
            <label className={styles.label} htmlFor="profession">Profession</label>
            <input
              id="profession"
              type="text"
              className={styles.input}
              placeholder="e.g. Software Engineer"
              value={filters.profession}
              onChange={(e) => setFilters(prev => ({ ...prev, profession: e.target.value }))}
            />
          </div>

          <div className={styles.section}>
            <label className={styles.label}>Years of Experience</label>
            <div className={styles.row}>
              <input
                type="number"
                className={styles.input}
                placeholder="Min"
                min="0"
                value={filters.minExperience}
                onChange={(e) => setFilters(prev => ({ ...prev, minExperience: e.target.value }))}
              />
              <input
                type="number"
                className={styles.input}
                placeholder="Max"
                min="0"
                value={filters.maxExperience}
                onChange={(e) => setFilters(prev => ({ ...prev, maxExperience: e.target.value }))}
              />
            </div>
          </div>

          <div className={styles.section}>
            <label className={styles.label}>Skills</label>
            <input
              type="text"
              className={styles.input}
              placeholder="Type skill and press Enter"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={handleAddSkill}
            />
            {filters.skills.length > 0 && (
              <div className={styles.skillsContainer}>
                {filters.skills.map(skill => (
                  <span key={skill} className={styles.skillTag}>
                    {skill}
                    <button 
                      type="button" 
                      className={styles.removeSkill}
                      onClick={() => removeSkill(skill)}
                    >
                      <FaTimes size={10} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className={styles.section}>
            <label className={styles.label} htmlFor="freeText">Free Text Search</label>
            <input
              id="freeText"
              type="text"
              className={styles.input}
              placeholder="Search in resume content..."
              value={filters.freeText}
              onChange={(e) => setFilters(prev => ({ ...prev, freeText: e.target.value }))}
            />
          </div>

          <div className={styles.actions}>
            <button className={`${styles.button} ${styles.clearButton}`} onClick={handleClear}>
              Clear
            </button>
            <button className={`${styles.button} ${styles.applyButton}`} onClick={handleApply}>
              Apply Filters
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
