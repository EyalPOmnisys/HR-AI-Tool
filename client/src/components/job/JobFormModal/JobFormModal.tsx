import { useEffect, useState } from 'react'
import type { FormEvent, MouseEvent, ReactElement } from 'react'
import type { Job, JobDraft } from '../../../types/job'
import styles from './JobFormModal.module.css'

type JobFormModalProps = {
  open: boolean
  mode: 'create' | 'edit'
  job?: Job | null
  onCancel: () => void
  onSubmit: (draft: JobDraft) => void
}

const iconOptions = [
  '🖥️',
  '⌨️',
  '📱',
  '🌐',
  '☁️',
  '💾',
  '🔒',
  '🤖',
  '🚀',
  '⚙️',
  '🔧',
  '📊',
  '📡'
]

const CloseIcon = () => (
  <svg
    width='18'
    height='18'
    viewBox='0 0 24 24'
    fill='none'
    xmlns='http://www.w3.org/2000/svg'
    aria-hidden
  >
    <path d='M6 6l12 12M18 6 6 18' stroke='currentColor' strokeWidth='1.8' strokeLinecap='round' />
  </svg>
)

// Helper component for tags
const SkillTag = ({ label, onRemove, color = 'blue' }: { label: string, onRemove: () => void, color?: 'blue' | 'green' }) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '6px 12px',
      background: color === 'blue' ? '#f0f9ff' : '#f0fdf4',
      border: `1px solid ${color === 'blue' ? '#bfdbfe' : '#bbf7d0'}`,
      borderRadius: '999px',
      fontSize: '0.875rem',
      color: color === 'blue' ? '#1e40af' : '#166534'
    }}
  >
    {label}
    <button
      type='button'
      onClick={onRemove}
      style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'inherit', padding: 0, display: 'flex', alignItems: 'center' }}
    >
      <svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'>
        <line x1='18' y1='6' x2='6' y2='18'></line>
        <line x1='6' y1='6' x2='18' y2='18'></line>
      </svg>
    </button>
  </span>
)

export const JobFormModal = ({ open, mode, job, onCancel, onSubmit }: JobFormModalProps): ReactElement | null => {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [icon, setIcon] = useState(iconOptions[0])
  
  // Advanced Editing State
  const [isAnalyzed, setIsAnalyzed] = useState(false)
  const [mustHaveSkills, setMustHaveSkills] = useState<string[]>([])
  const [niceToHaveSkills, setNiceToHaveSkills] = useState<string[]>([])
  const [expMin, setExpMin] = useState<number | ''>('')
  const [expMax, setExpMax] = useState<number | ''>('')
  
  // Tech Stack State
  const [techLanguages, setTechLanguages] = useState<string[]>([])
  const [techFrameworks, setTechFrameworks] = useState<string[]>([])
  const [techDatabases, setTechDatabases] = useState<string[]>([])
  const [techCloud, setTechCloud] = useState<string[]>([])
  const [techTools, setTechTools] = useState<string[]>([])

  // Inputs for skills
  const [newMustHave, setNewMustHave] = useState('')
  const [newNiceToHave, setNewNiceToHave] = useState('')
  
  // Inputs for Tech Stack
  const [newTechLanguage, setNewTechLanguage] = useState('')
  const [newTechFramework, setNewTechFramework] = useState('')
  const [newTechDatabase, setNewTechDatabase] = useState('')
  const [newTechCloud, setNewTechCloud] = useState('')
  const [newTechTool, setNewTechTool] = useState('')

  useEffect(() => {
    if (job) {
      setTitle(job.title)
      setDescription(job.description)
      const jobIcon = job.icon || iconOptions[Math.floor(Math.random() * iconOptions.length)]
      setIcon(jobIcon)
      
      // Check if we have advanced analysis data
      if (job.analysis && job.analysis.skills) {
        setIsAnalyzed(true)
        setMustHaveSkills(job.analysis.skills.must_have || [])
        setNiceToHaveSkills(job.analysis.skills.nice_to_have || [])
        
        if (job.analysis.experience) {
          setExpMin(job.analysis.experience.years_min ?? '')
          setExpMax(job.analysis.experience.years_max ?? '')
        } else {
          setExpMin('')
          setExpMax('')
        }

        // Populate Tech Stack
        if (job.analysis.tech_stack) {
          setTechLanguages(job.analysis.tech_stack.languages || [])
          setTechFrameworks(job.analysis.tech_stack.frameworks || [])
          setTechDatabases(job.analysis.tech_stack.databases || [])
          setTechCloud(job.analysis.tech_stack.cloud || [])
          setTechTools(job.analysis.tech_stack.tools || [])
        } else {
          setTechLanguages([])
          setTechFrameworks([])
          setTechDatabases([])
          setTechCloud([])
          setTechTools([])
        }
      } else {
        setIsAnalyzed(false)
        setMustHaveSkills(job.additionalSkills || [])
        setNiceToHaveSkills([])
        setExpMin('')
        setExpMax('')
        
        setTechLanguages([])
        setTechFrameworks([])
        setTechDatabases([])
        setTechCloud([])
        setTechTools([])
      }
    } else {
      // Reset all
      setTitle('')
      setDescription('')
      setIcon(iconOptions[Math.floor(Math.random() * iconOptions.length)])
      setIsAnalyzed(false)
      setMustHaveSkills([])
      setNiceToHaveSkills([])
      setExpMin('')
      setExpMax('')
      
      setTechLanguages([])
      setTechFrameworks([])
      setTechDatabases([])
      setTechCloud([])
      setTechTools([])
    }
  }, [job])

  if (!open) return null

  const handleBackdropInteraction = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) onCancel()
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    
    const draft: any = { title, description, icon }
    
    // If we are in advanced mode, we construct the full analysis object
    if (isAnalyzed && job?.analysis) {
      draft.analysis_json = {
        ...job.analysis,
        skills: {
          ...job.analysis.skills,
          must_have: mustHaveSkills,
          nice_to_have: niceToHaveSkills
        },
        tech_stack: {
          ...job.analysis.tech_stack,
          languages: techLanguages,
          frameworks: techFrameworks,
          databases: techDatabases,
          cloud: techCloud,
          tools: techTools,
          business: job.analysis.tech_stack?.business || []
        },
        experience: {
          years_min: expMin === '' ? null : Number(expMin),
          years_max: expMax === '' ? null : Number(expMax)
        }
      }
      // We also set additionalSkills to mustHaveSkills for backward compatibility/display in list if needed
      draft.additionalSkills = mustHaveSkills
    } else {
      // Fallback for legacy/simple mode
      draft.additionalSkills = mustHaveSkills // In simple mode we just treat must have as additional
    }

    onSubmit(draft)
  }

  const addSkill = (
    value: string, 
    setter: (val: string) => void, 
    list: string[], 
    listSetter: (val: string[]) => void
  ) => {
    const trimmed = value.trim()
    if (trimmed && !list.includes(trimmed)) {
      listSetter([...list, trimmed])
      setter('')
    }
  }

  return (
    <div
      className={styles.backdrop}
      role='dialog'
      aria-modal='true'
      onMouseDown={handleBackdropInteraction}
    >
      <form className={styles.modal} onSubmit={handleSubmit}>
        <header className={styles.header}>
          <div>
            <h2>{mode === 'create' ? 'Create a new job' : 'Edit Job Details'}</h2>
            <p>{isAnalyzed ? 'Refine the AI analysis manually.' : 'Define the basics for the AI.'}</p>
          </div>
          <button type='button' className={styles.closeButton} onClick={onCancel}>
            <CloseIcon />
          </button>
        </header>

        <div className={styles.body}>
          {/* Basic Info Section */}
          <div className={styles.fieldGroup}>
            <label>
              Job title
              <input value={title} onChange={(e) => setTitle(e.target.value)} required />
            </label>
            
            {!isAnalyzed && (
              <label>
                Description (Source for AI)
                <textarea 
                  value={description} 
                  onChange={(e) => setDescription(e.target.value)} 
                  rows={5} 
                  required 
                  style={{ fontSize: '0.9rem' }}
                />
              </label>
            )}
          </div>

          {/* Advanced Skills Editor - Only shows if job is analyzed */}
          {isAnalyzed && (
            <div style={{ 
              borderTop: '1px solid #e2e8f0', 
              paddingTop: '20px', 
              marginTop: '10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px'
            }}>
              
              {/* Experience Editor */}
              <div className={styles.fieldGroup}>
                <label style={{ color: '#334155' }}>Experience (Years)</label>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Min</span>
                        <input
                            type='number'
                            min='0'
                            value={expMin}
                            onChange={e => setExpMin(e.target.value === '' ? '' : Number(e.target.value))}
                            style={{ width: '80px' }}
                        />
                    </div>
                    <span style={{ marginTop: '20px', color: '#64748b' }}>to</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Max</span>
                        <input
                            type='number'
                            min='0'
                            value={expMax}
                            onChange={e => setExpMax(e.target.value === '' ? '' : Number(e.target.value))}
                            style={{ width: '80px' }}
                        />
                    </div>
                </div>
              </div>

              {/* Must Have Skills */}
              <div className={styles.fieldGroup} style={{ gap: '10px' }}>
                <label style={{ color: '#1e40af' }}>Must Have Skills</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    value={newMustHave}
                    onChange={(e) => setNewMustHave(e.target.value)}
                    placeholder='Add a critical skill (e.g. React, Python)'
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addSkill(newMustHave, setNewMustHave, mustHaveSkills, setMustHaveSkills)
                      }
                    }}
                    style={{ flex: 1 }}
                  />
                  <button 
                    type='button' 
                    onClick={() => addSkill(newMustHave, setNewMustHave, mustHaveSkills, setMustHaveSkills)}
                    className={styles.secondary}
                    style={{ padding: '0 16px' }}
                  >Add</button>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {mustHaveSkills.map(skill => (
                    <SkillTag 
                      key={skill} 
                      label={skill} 
                      onRemove={() => setMustHaveSkills(mustHaveSkills.filter(s => s !== skill))} 
                      color='blue'
                    />
                  ))}
                </div>
              </div>

              {/* Nice to Have Skills */}
              <div className={styles.fieldGroup} style={{ gap: '10px' }}>
                <label style={{ color: '#166534' }}>Nice to Have Skills</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    value={newNiceToHave}
                    onChange={(e) => setNewNiceToHave(e.target.value)}
                    placeholder='Add a bonus skill (e.g. AWS, Docker)'
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addSkill(newNiceToHave, setNewNiceToHave, niceToHaveSkills, setNiceToHaveSkills)
                      }
                    }}
                    style={{ flex: 1 }}
                  />
                  <button 
                    type='button' 
                    onClick={() => addSkill(newNiceToHave, setNewNiceToHave, niceToHaveSkills, setNiceToHaveSkills)}
                    className={styles.secondary}
                    style={{ padding: '0 16px' }}
                  >Add</button>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {niceToHaveSkills.map(skill => (
                    <SkillTag 
                      key={skill} 
                      label={skill} 
                      onRemove={() => setNiceToHaveSkills(niceToHaveSkills.filter(s => s !== skill))} 
                      color='green'
                    />
                  ))}
                </div>
              </div>

              {/* Tech Stack Section */}
              <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '20px', marginTop: '10px' }}>
                <h4 style={{ margin: '0 0 15px 0', color: '#334155' }}>Tech Stack</h4>
                
                {/* Languages */}
                <div className={styles.fieldGroup} style={{ gap: '10px', marginBottom: '15px' }}>
                  <label style={{ fontSize: '0.9rem', color: '#475569' }}>Languages</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      value={newTechLanguage}
                      onChange={(e) => setNewTechLanguage(e.target.value)}
                      placeholder='e.g. TypeScript, Python'
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(newTechLanguage, setNewTechLanguage, techLanguages, setTechLanguages); } }}
                      style={{ flex: 1 }}
                    />
                    <button type='button' onClick={() => addSkill(newTechLanguage, setNewTechLanguage, techLanguages, setTechLanguages)} className={styles.secondary} style={{ padding: '0 16px' }}>Add</button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {techLanguages.map(skill => <SkillTag key={skill} label={skill} onRemove={() => setTechLanguages(techLanguages.filter(s => s !== skill))} color='blue' />)}
                  </div>
                </div>

                {/* Frameworks */}
                <div className={styles.fieldGroup} style={{ gap: '10px', marginBottom: '15px' }}>
                  <label style={{ fontSize: '0.9rem', color: '#475569' }}>Frameworks</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      value={newTechFramework}
                      onChange={(e) => setNewTechFramework(e.target.value)}
                      placeholder='e.g. React, Django'
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(newTechFramework, setNewTechFramework, techFrameworks, setTechFrameworks); } }}
                      style={{ flex: 1 }}
                    />
                    <button type='button' onClick={() => addSkill(newTechFramework, setNewTechFramework, techFrameworks, setTechFrameworks)} className={styles.secondary} style={{ padding: '0 16px' }}>Add</button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {techFrameworks.map(skill => <SkillTag key={skill} label={skill} onRemove={() => setTechFrameworks(techFrameworks.filter(s => s !== skill))} color='blue' />)}
                  </div>
                </div>

                {/* Databases */}
                <div className={styles.fieldGroup} style={{ gap: '10px', marginBottom: '15px' }}>
                  <label style={{ fontSize: '0.9rem', color: '#475569' }}>Databases</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      value={newTechDatabase}
                      onChange={(e) => setNewTechDatabase(e.target.value)}
                      placeholder='e.g. PostgreSQL, MongoDB'
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(newTechDatabase, setNewTechDatabase, techDatabases, setTechDatabases); } }}
                      style={{ flex: 1 }}
                    />
                    <button type='button' onClick={() => addSkill(newTechDatabase, setNewTechDatabase, techDatabases, setTechDatabases)} className={styles.secondary} style={{ padding: '0 16px' }}>Add</button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {techDatabases.map(skill => <SkillTag key={skill} label={skill} onRemove={() => setTechDatabases(techDatabases.filter(s => s !== skill))} color='blue' />)}
                  </div>
                </div>

                 {/* Cloud */}
                <div className={styles.fieldGroup} style={{ gap: '10px', marginBottom: '15px' }}>
                  <label style={{ fontSize: '0.9rem', color: '#475569' }}>Cloud & DevOps</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      value={newTechCloud}
                      onChange={(e) => setNewTechCloud(e.target.value)}
                      placeholder='e.g. AWS, Docker'
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(newTechCloud, setNewTechCloud, techCloud, setTechCloud); } }}
                      style={{ flex: 1 }}
                    />
                    <button type='button' onClick={() => addSkill(newTechCloud, setNewTechCloud, techCloud, setTechCloud)} className={styles.secondary} style={{ padding: '0 16px' }}>Add</button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {techCloud.map(skill => <SkillTag key={skill} label={skill} onRemove={() => setTechCloud(techCloud.filter(s => s !== skill))} color='blue' />)}
                  </div>
                </div>

                 {/* Tools */}
                <div className={styles.fieldGroup} style={{ gap: '10px' }}>
                  <label style={{ fontSize: '0.9rem', color: '#475569' }}>Tools</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      value={newTechTool}
                      onChange={(e) => setNewTechTool(e.target.value)}
                      placeholder='e.g. Git, Jira'
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(newTechTool, setNewTechTool, techTools, setTechTools); } }}
                      style={{ flex: 1 }}
                    />
                    <button type='button' onClick={() => addSkill(newTechTool, setNewTechTool, techTools, setTechTools)} className={styles.secondary} style={{ padding: '0 16px' }}>Add</button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {techTools.map(skill => <SkillTag key={skill} label={skill} onRemove={() => setTechTools(techTools.filter(s => s !== skill))} color='blue' />)}
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* Legacy/Simple Additional Skills - Only show if NOT analyzed */}
          {!isAnalyzed && (
             <div className={styles.fieldGroup}>
                <label>Additional Skills (Initial Hint)</label>
                <span style={{ fontSize: '0.85rem', color: '#64748b', marginLeft: '0.5rem' }}>Add specific skills the AI might not identify</span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    value={newMustHave}
                    onChange={(e) => setNewMustHave(e.target.value)}
                    placeholder='e.g., Python, Leadership'
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addSkill(newMustHave, setNewMustHave, mustHaveSkills, setMustHaveSkills)
                      }
                    }}
                    style={{ flex: 1 }}
                  />
                  <button
                    type='button'
                    onClick={() => addSkill(newMustHave, setNewMustHave, mustHaveSkills, setMustHaveSkills)}
                    className={styles.secondary}
                  >Add</button>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {mustHaveSkills.map(skill => (
                    <SkillTag key={skill} label={skill} onRemove={() => setMustHaveSkills(mustHaveSkills.filter(s => s !== skill))} />
                  ))}
                </div>
             </div>
          )}
        </div>

        <footer className={styles.footer}>
          <button type='button' className={styles.secondary} onClick={onCancel}>Cancel</button>
          <button type='submit' className={styles.primary}>
            {isAnalyzed ? 'Save Manual Changes' : (mode === 'create' ? 'Publish Job' : 'Save Changes')}
          </button>
        </footer>
      </form>
    </div>
  )
}

