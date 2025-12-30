import { useState, useRef, useEffect, type ReactElement, type KeyboardEvent } from 'react'
import { FaChevronDown, FaTimes, FaPlus } from 'react-icons/fa'
import styles from './ResumeFilters.module.css'

const COMMON_PROFESSIONS = [
  "Software Engineer", "Product Manager", "Data Scientist", "DevOps Engineer", "QA Engineer", 
  "Full Stack Developer", "Frontend Developer", "Backend Developer"
]

const COMMON_SKILLS = [
  "Python", "JavaScript", "React", "Node.js", "SQL", 
  "Docker", "AWS", "TypeScript", "Java", "C++"
]

export interface FilterState {
  profession: string[]
  minExperience: string
  maxExperience: string
  skills: string[]
  freeText: string[]
  excludeKeywords: string[]
}

interface ResumeFiltersProps {
  onFilterChange: (filters: FilterState) => void
  initialFilters?: FilterState
  className?: string
  availableOptions?: {
    skills?: string[]
    professions?: string[]
  }
}

export const ResumeFilters = ({ onFilterChange, initialFilters, className, availableOptions }: ResumeFiltersProps): ReactElement => {
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterState>(initialFilters || {
    profession: [],
    minExperience: '',
    maxExperience: '',
    skills: [],
    freeText: [],
    excludeKeywords: []
  })
  const [skillInput, setSkillInput] = useState('')
  const [professionInput, setProfessionInput] = useState('')
  const [keywordInput, setKeywordInput] = useState('')
  const [excludeInput, setExcludeInput] = useState('')

  const allProfessions = availableOptions?.professions || COMMON_PROFESSIONS
  const allSkills = availableOptions?.skills || COMMON_SKILLS

  const containerRef = useRef<HTMLDivElement>(null)

  const getSuggestions = (list: string[], input: string, currentSelected: string[]) => {
    const normalizedInput = input.toLowerCase().trim()
    
    // Filter out already selected items
    const candidates = list.filter(item => !currentSelected.includes(item))

    if (!normalizedInput) {
      // If no input, return top 5 common items
      return candidates.slice(0, 5)
    }

    // If input exists, filter by input
    return candidates.filter(item => 
      item.toLowerCase().includes(normalizedInput)
    )
  }

  const renderSuggestions = (
    list: string[], 
    input: string, 
    selected: string[], 
    onSelect: (val: string) => void
  ) => {
    const suggestions = getSuggestions(list, input, selected)
    
    if (suggestions.length === 0) return null

    return (
      <>
        <span className={styles.suggestionLabel}>
          {input ? 'Suggestions' : 'Common'}
        </span>
        <div className={styles.suggestionsList}>
          {suggestions.map(item => (
            <div 
              key={item} 
              className={styles.suggestionItem}
              onClick={() => onSelect(item)}
            >
              {item}
              {input && <FaPlus size={10} style={{ opacity: 0.5 }} />}
            </div>
          ))}
        </div>
      </>
    )
  }

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
      freeText: [],
      excludeKeywords: []
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

  const addExcludeKeyword = () => {
    if (excludeInput.trim()) {
      if (!filters.excludeKeywords.includes(excludeInput.trim())) {
        const newFilters = {
          ...filters,
          excludeKeywords: [...filters.excludeKeywords, excludeInput.trim()]
        }
        updateFilters(newFilters)
      }
      setExcludeInput('')
    }
  }

  const handleAddExcludeKeyword = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addExcludeKeyword()
    }
  }

  const removeExcludeKeyword = (keywordToRemove: string) => {
    const newFilters = {
      ...filters,
      excludeKeywords: filters.excludeKeywords.filter(k => k !== keywordToRemove)
    }
    updateFilters(newFilters)
  }

  const addSkill = (skillToAdd?: string) => {
    let val = skillToAdd || skillInput.trim()
    if (val) {
      // Normalize skill to Title Case (e.g. "python" -> "Python") to match DB
      val = val.charAt(0).toUpperCase() + val.slice(1);

      if (!filters.skills.includes(val)) {
        const newFilters = {
          ...filters,
          skills: [...filters.skills, val]
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

  const addProfession = (profToAdd?: string) => {
    const val = profToAdd || professionInput.trim()
    if (val) {
      if (!filters.profession.includes(val)) {
        const newFilters = {
          ...filters,
          profession: [...filters.profession, val]
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
    filters.freeText.length > 0 ||
    filters.excludeKeywords.length > 0
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
                onClick={() => addProfession()}
                disabled={!professionInput.trim()}
              >
                <FaPlus />
              </button>
            </div>
            
            {/* Suggestions Area */}
            {renderSuggestions(allProfessions, professionInput, filters.profession, addProfession)}

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
                onClick={() => addSkill()}
                disabled={!skillInput.trim()}
              >
                <FaPlus />
              </button>
            </div>

            {/* Suggestions Area */}
            {renderSuggestions(allSkills, skillInput, filters.skills, addSkill)}

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
            <label className={styles.label}>Must Include</label>
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

      {/* Exclude Filter */}
      <div className={styles.filterGroup}>
        <button 
          className={`${styles.filterButton} ${activeDropdown === 'exclude' ? styles.active : ''} ${filters.excludeKeywords.length > 0 ? styles.hasValue : ''}`}
          onClick={() => toggleDropdown('exclude')}
          style={filters.excludeKeywords.length > 0 ? { color: '#de350b', backgroundColor: '#ffebe6' } : {}}
        >
          Exclude {filters.excludeKeywords.length > 0 && `(${filters.excludeKeywords.length})`}
          <FaChevronDown size={10} />
        </button>
        {activeDropdown === 'exclude' && (
          <div className={styles.popover}>
            <label className={styles.label} style={{ color: '#de350b' }}>Must NOT Include</label>
            <div className={styles.inputGroup}>
              <input
                type="text"
                className={styles.input}
                placeholder="Word to exclude..."
                value={excludeInput}
                onChange={(e) => setExcludeInput(e.target.value)}
                onKeyDown={handleAddExcludeKeyword}
                autoFocus
              />
              <button 
                className={styles.addButton} 
                onClick={addExcludeKeyword}
                disabled={!excludeInput.trim()}
              >
                <FaPlus />
              </button>
            </div>
            <div className={styles.skillsContainer}>
              {filters.excludeKeywords.map(keyword => (
                <span key={keyword} className={styles.skillTag} style={{ color: '#de350b', backgroundColor: '#ffebe6' }}>
                  {keyword}
                  <button type="button" className={styles.removeSkill} onClick={() => removeExcludeKeyword(keyword)} style={{ color: '#de350b' }}>
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
