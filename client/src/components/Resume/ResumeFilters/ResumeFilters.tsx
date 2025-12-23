import { useState, useRef, useEffect, type ReactElement, type KeyboardEvent } from 'react'
import { FaChevronDown, FaTimes, FaPlus } from 'react-icons/fa'
import styles from './ResumeFilters.module.css'

export interface FilterState {
  profession: string[]
  minExperience: string
  maxExperience: string
  skills: string[]
  freeText: string[]
}

interface ResumeFiltersProps {
  onFilterChange: (filters: FilterState) => void
  initialFilters?: FilterState
  className?: string
}

export const ResumeFilters = ({ onFilterChange, initialFilters, className }: ResumeFiltersProps): ReactElement => {
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterState>(initialFilters || {
    profession: [],
    minExperience: '',
    maxExperience: '',
    skills: [],
    freeText: []
  })
  const [skillInput, setSkillInput] = useState('')
  const [professionInput, setProfessionInput] = useState('')
  const [keywordInput, setKeywordInput] = useState('')

  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setActiveDropdown(null)
      }
    }

    if (activeDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [activeDropdown])

  const updateFilters = (newFilters: FilterState) => {
    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  const toggleDropdown = (name: string) => {
    setActiveDropdown(prev => prev === name ? null : name)
  }

  const handleClear = () => {
    const emptyFilters: FilterState = {
      profession: [],
      minExperience: '',
      maxExperience: '',
      skills: [],
      freeText: []
    }
    updateFilters(emptyFilters)
    setActiveDropdown(null)
  }

  const addKeyword = () => {
    if (keywordInput.trim()) {
      if (!filters.freeText.includes(keywordInput.trim())) {
        const newFilters = {
          ...filters,
          freeText: [...filters.freeText, keywordInput.trim()]
        }
        updateFilters(newFilters)
      }
      setKeywordInput('')
    }
  }

  const handleAddKeyword = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addKeyword()
    }
  }

  const removeKeyword = (keywordToRemove: string) => {
    const newFilters = {
      ...filters,
      freeText: filters.freeText.filter(k => k !== keywordToRemove)
    }
    updateFilters(newFilters)
  }

  const addSkill = () => {
    if (skillInput.trim()) {
      if (!filters.skills.includes(skillInput.trim())) {
        const newFilters = {
          ...filters,
          skills: [...filters.skills, skillInput.trim()]
        }
        updateFilters(newFilters)
      }
      setSkillInput('')
    }
  }

  const handleAddSkill = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addSkill()
    }
  }

  const removeSkill = (skillToRemove: string) => {
    const newFilters = {
      ...filters,
      skills: filters.skills.filter(s => s !== skillToRemove)
    }
    updateFilters(newFilters)
  }

  const addProfession = () => {
    if (professionInput.trim()) {
      if (!filters.profession.includes(professionInput.trim())) {
        const newFilters = {
          ...filters,
          profession: [...filters.profession, professionInput.trim()]
        }
        updateFilters(newFilters)
      }
      setProfessionInput('')
    }
  }

  const handleAddProfession = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addProfession()
    }
  }

  const removeProfession = (professionToRemove: string) => {
    const newFilters = {
      ...filters,
      profession: filters.profession.filter(p => p !== professionToRemove)
    }
    updateFilters(newFilters)
  }

  const handleExperienceChange = (field: 'minExperience' | 'maxExperience', value: string) => {
    const newFilters = { ...filters, [field]: value }
    updateFilters(newFilters)
  }

  const hasActiveFilters = Boolean(
    filters.profession.length > 0 || 
    filters.minExperience || 
    filters.maxExperience || 
    filters.skills.length > 0 || 
    filters.freeText.length > 0
  )

  return (
    <div className={`${styles.container} ${className || ''}`} ref={containerRef}>
      {/* Profession Filter */}
      <div className={styles.filterGroup}>
        <button 
          className={`${styles.filterButton} ${activeDropdown === 'profession' ? styles.active : ''} ${filters.profession.length > 0 ? styles.hasValue : ''}`}
          onClick={() => toggleDropdown('profession')}
        >
          Profession {filters.profession.length > 0 && `(${filters.profession.length})`}
          <FaChevronDown size={10} />
        </button>
        {activeDropdown === 'profession' && (
          <div className={styles.popover}>
            <label className={styles.label}>Professions</label>
            <div className={styles.inputGroup}>
              <input
                type="text"
                className={styles.input}
                placeholder="Type & Enter..."
                value={professionInput}
                onChange={(e) => setProfessionInput(e.target.value)}
                onKeyDown={handleAddProfession}
                autoFocus
              />
              <button 
                className={styles.addButton} 
                onClick={addProfession}
                disabled={!professionInput.trim()}
              >
                <FaPlus />
              </button>
            </div>
            <div className={styles.skillsContainer}>
              {filters.profession.map(prof => (
                <span key={prof} className={styles.skillTag}>
                  {prof}
                  <button type="button" className={styles.removeSkill} onClick={() => removeProfession(prof)}>
                    <FaTimes size={10} />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Experience Filter */}
      <div className={styles.filterGroup}>
        <button 
          className={`${styles.filterButton} ${activeDropdown === 'experience' ? styles.active : ''} ${(filters.minExperience || filters.maxExperience) ? styles.hasValue : ''}`}
          onClick={() => toggleDropdown('experience')}
        >
          Experience
          <FaChevronDown size={10} />
        </button>
        {activeDropdown === 'experience' && (
          <div className={styles.popover}>
            <label className={styles.label}>Years of Experience</label>
            <div className={styles.row}>
              <input
                type="number"
                className={styles.input}
                placeholder="Min"
                min="0"
                value={filters.minExperience}
                onChange={(e) => handleExperienceChange('minExperience', e.target.value)}
              />
              <input
                type="number"
                className={styles.input}
                placeholder="Max"
                min="0"
                value={filters.maxExperience}
                onChange={(e) => handleExperienceChange('maxExperience', e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Skills Filter */}
      <div className={styles.filterGroup}>
        <button 
          className={`${styles.filterButton} ${activeDropdown === 'skills' ? styles.active : ''} ${filters.skills.length > 0 ? styles.hasValue : ''}`}
          onClick={() => toggleDropdown('skills')}
        >
          Skills {filters.skills.length > 0 && `(${filters.skills.length})`}
          <FaChevronDown size={10} />
        </button>
        {activeDropdown === 'skills' && (
          <div className={styles.popover}>
            <label className={styles.label}>Skills</label>
            <div className={styles.inputGroup}>
              <input
                type="text"
                className={styles.input}
                placeholder="Type & Enter..."
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={handleAddSkill}
                autoFocus
              />
              <button 
                className={styles.addButton} 
                onClick={addSkill}
                disabled={!skillInput.trim()}
              >
                <FaPlus />
              </button>
            </div>
            <div className={styles.skillsContainer}>
              {filters.skills.map(skill => (
                <span key={skill} className={styles.skillTag}>
                  {skill}
                  <button type="button" className={styles.removeSkill} onClick={() => removeSkill(skill)}>
                    <FaTimes size={10} />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Free Text Filter */}
      <div className={styles.filterGroup}>
        <button 
          className={`${styles.filterButton} ${activeDropdown === 'freeText' ? styles.active : ''} ${filters.freeText.length > 0 ? styles.hasValue : ''}`}
          onClick={() => toggleDropdown('freeText')}
        >
          Keywords {filters.freeText.length > 0 && `(${filters.freeText.length})`}
          <FaChevronDown size={10} />
        </button>
        {activeDropdown === 'freeText' && (
          <div className={styles.popover}>
            <label className={styles.label}>Keywords</label>
            <div className={styles.inputGroup}>
              <input
                type="text"
                className={styles.input}
                placeholder="Type & Enter..."
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyDown={handleAddKeyword}
                autoFocus
              />
              <button 
                className={styles.addButton} 
                onClick={addKeyword}
                disabled={!keywordInput.trim()}
              >
                <FaPlus />
              </button>
            </div>
            <div className={styles.skillsContainer}>
              {filters.freeText.map(keyword => (
                <span key={keyword} className={styles.skillTag}>
                  {keyword}
                  <button type="button" className={styles.removeSkill} onClick={() => removeKeyword(keyword)}>
                    <FaTimes size={10} />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {hasActiveFilters && (
        <button className={styles.clearButton} onClick={handleClear}>
          Clear filters
        </button>
      )}
    </div>
  )
}
