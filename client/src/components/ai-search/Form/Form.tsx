import type { ChangeEvent, FormEvent } from 'react'
import styles from './Form.module.css'
import type { ApiJob } from '../../../services/jobs'

type Props = {
  jobs: ApiJob[]
  selectedJobId: string
  desiredCandidates: number
  selectedJob?: ApiJob
  isLoadingJobs: boolean
  onJobChange: (e: ChangeEvent<HTMLSelectElement>) => void
  onCandidateChange: (e: ChangeEvent<HTMLInputElement>) => void
  onSubmit: (e: FormEvent<HTMLFormElement>) => void
}

export default function Form({
  jobs,
  selectedJobId,
  desiredCandidates,
  selectedJob,
  isLoadingJobs,
  onJobChange,
  onCandidateChange,
  onSubmit
}: Props) {
  const analysis = selectedJob?.analysis_json

  return (
    <section className={styles.wrapper}>
      <form className={styles.card} onSubmit={onSubmit}>
        <div className={styles.grid}>
          {/* Left sidebar - Form controls */}
          <div className={styles.left}>
            <div className={styles.formSection}>
              <h3 className={styles.sectionTitle}>Search Configuration</h3>
              
              <div className={styles.field}>
                <label htmlFor="jobSelect" className={styles.label}>Select a role</label>
                <select
                  id="jobSelect"
                  className={styles.control}
                  value={selectedJobId}
                  onChange={onJobChange}
                  disabled={isLoadingJobs}
                >
                  {isLoadingJobs ? (
                    <option>Loading jobs...</option>
                  ) : jobs.length === 0 ? (
                    <option>No jobs available</option>
                  ) : (
                    jobs.map((job) => (
                      <option key={job.id} value={job.id}>
                        {job.icon ? `${job.icon} ` : ''}{job.title}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div className={styles.field}>
                <label htmlFor="candidateCount" className={styles.label}>Number of candidates</label>
                <input
                  id="candidateCount"
                  className={styles.control}
                  type="number"
                  min={1}
                  max={20}
                  value={desiredCandidates}
                  onChange={onCandidateChange}
                />
              </div>

              <div className={styles.actions}>
                <button type="submit" className={styles.primary} disabled={!selectedJobId}>
                  Generate AI Shortlist
                </button>
              </div>
            </div>

            {/* Quick Stats */}
            {analysis && (
              <div className={styles.quickStats}>
                <h3 className={styles.sectionTitle}>Quick Stats</h3>
                <div className={styles.statsGrid}>
                  <div className={styles.statCard}>
                    <div className={styles.statValue}>{analysis.skills.must_have.length}</div>
                    <div className={styles.statLabel}>Required Skills</div>
                  </div>
                  <div className={styles.statCard}>
                    <div className={styles.statValue}>{analysis.skills.nice_to_have.length}</div>
                    <div className={styles.statLabel}>Nice to Have</div>
                  </div>
                  {analysis.experience.years_min && (
                    <div className={styles.statCard}>
                      <div className={styles.statValue}>
                        {analysis.experience.years_min}
                        {analysis.experience.years_max ? `-${analysis.experience.years_max}` : '+'}
                      </div>
                      <div className={styles.statLabel}>Years Exp.</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Right side - Job details */}
          <div className={styles.right}>
            {selectedJob ? (
              <>
                <div className={styles.jobHeader}>
                  <div className={styles.jobHeaderTop}>
                    {selectedJob.icon && <span className={styles.jobIcon}>{selectedJob.icon}</span>}
                    <h2 className={styles.title}>{selectedJob.title}</h2>
                  </div>
                  {analysis?.summary && (
                    <p className={styles.summary}>{analysis.summary}</p>
                  )}
                </div>

                {/* Required Skills */}
                {analysis?.skills.must_have && analysis.skills.must_have.length > 0 && (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>
                      <span className={styles.badge}>Must Have</span>
                      Required Skills
                    </h3>
                    <div className={styles.skillsGrid}>
                      {analysis.skills.must_have.map((skill) => (
                        <span key={skill} className={styles.skillTag}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Nice to Have Skills */}
                {analysis?.skills.nice_to_have && analysis.skills.nice_to_have.length > 0 && (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>
                      <span className={styles.badgeOptional}>Optional</span>
                      Nice to Have
                    </h3>
                    <div className={styles.skillsGrid}>
                      {analysis.skills.nice_to_have.map((skill) => (
                        <span key={skill} className={styles.skillTag}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tech Stack */}
                {analysis?.tech_stack && (
                  <>
                    {analysis.tech_stack.languages.length > 0 && (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeTech}>Languages</span>
                          Programming Languages
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.languages.map((lang) => (
                            <span key={lang} className={styles.skillTag}>💻 {lang}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {analysis.tech_stack.frameworks.length > 0 && (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeTech}>Tools</span>
                          Frameworks & Tools
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.frameworks.map((fw) => (
                            <span key={fw} className={styles.skillTag}>🔧 {fw}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {analysis.tech_stack.databases.length > 0 && (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeTech}>Data</span>
                          Databases
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.databases.map((db) => (
                            <span key={db} className={styles.skillTag}>🗄️ {db}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* Keywords */}
                {analysis?.keywords && analysis.keywords.length > 0 && (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Key Focus Areas</h3>
                    <div className={styles.keywordsList}>
                      {analysis.keywords.map((keyword) => (
                        <span key={keyword} className={styles.keyword}>
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Requirements */}
                {analysis?.requirements && analysis.requirements.length > 0 && (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Requirements</h3>
                    <ul className={styles.requirementsList}>
                      {analysis.requirements.map((req, idx) => (
                        <li key={idx} className={styles.requirementItem}>{req}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Job Description */}
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Full Description</h3>
                  <div className={styles.description}>
                    {selectedJob.job_description}
                  </div>
                </div>

                {/* Free Text */}
                {selectedJob.free_text && (
                  <div className={styles.section}>
                    <div className={styles.freeText}>
                      <h3 className={styles.sectionTitle}>Additional Notes</h3>
                      <p>{selectedJob.free_text}</p>
                    </div>
                  </div>
                )}

                {/* Locations */}
                {analysis?.locations && analysis.locations.length > 0 && (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>📍 Locations</h3>
                    <div className={styles.locationsList}>
                      {analysis.locations.map((loc) => (
                        <span key={loc} className={styles.location}>{loc}</span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>🔍</div>
                <h3>Select a Job Position</h3>
                <p>Choose a role from the dropdown to see detailed requirements and generate your AI-powered candidate shortlist.</p>
              </div>
            )}
          </div>
        </div>
      </form>
    </section>
  )
}
