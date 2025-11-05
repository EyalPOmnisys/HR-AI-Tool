// src/components/ai-search/Form/Form.tsx
import type { ChangeEvent, FormEvent } from 'react';
import styles from './Form.module.css';
import type { ApiJob, JobAnalysis, LanguageLevel } from '../../../types/job';

type Props = {
  jobs: ApiJob[];
  selectedJobId: string;
  desiredCandidates: number;
  selectedJob?: ApiJob;
  isLoadingJobs: boolean;
  onJobChange: (e: ChangeEvent<HTMLSelectElement>) => void;
  onCandidateChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
};

function levelLabel(level: LanguageLevel): string {
  if (!level) return '';
  const map: Record<Exclude<LanguageLevel, null>, string> = {
    basic: 'Basic',
    conversational: 'Conversational',
    fluent: 'Fluent',
    native: 'Native',
  };
  return map[level];
}

function optionLabel(job: ApiJob): string {
  const a = job.analysis_json;
  const org = a?.organization ? ` — ${a.organization}` : '';
  const loc = a?.locations?.[0] ? ` • ${a.locations[0]}` : '';
  const icon = job.icon ? `${job.icon} ` : '';
  return `${icon}${job.title}${org}${loc}`;
}

export default function Form({
  jobs,
  selectedJobId,
  desiredCandidates,
  selectedJob,
  isLoadingJobs,
  onJobChange,
  onCandidateChange,
  onSubmit,
}: Props) {
  const analysis: JobAnalysis | undefined = selectedJob?.analysis_json ?? undefined;

  const exp = analysis?.experience;
  const yearsDisplay =
    exp && (exp.years_min != null || exp.years_max != null)
      ? exp.years_min != null && exp.years_max != null
        ? `${exp.years_min}–${exp.years_max}`
        : exp.years_min != null
          ? `${exp.years_min}+`
          : `up to ${exp.years_max}`
      : null;

  return (
    <section className={styles.wrapper}>
      <form className={styles.card} onSubmit={onSubmit}>
        <div className={styles.grid}>
          {/* Left sidebar - Form controls */}
          <div className={styles.left}>
            <div className={styles.formSection}>
              <h3 className={styles.sectionTitle}>Search Configuration</h3>

              <div className={styles.field}>
                <label htmlFor="jobSelect" className={styles.label}>
                  Select a role
                </label>
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
                        {optionLabel(job)}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div className={styles.field}>
                <label htmlFor="candidateCount" className={styles.label}>
                  Number of candidates
                </label>
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
                <button
                  type="submit"
                  className={styles.primary}
                  disabled={!selectedJobId}
                >
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
                    <div className={styles.statValue}>
                      {analysis.skills.must_have.length}
                    </div>
                    <div className={styles.statLabel}>Required Skills</div>
                  </div>
                  <div className={styles.statCard}>
                    <div className={styles.statValue}>
                      {analysis.skills.nice_to_have.length}
                    </div>
                    <div className={styles.statLabel}>Nice to Have</div>
                  </div>
                  {yearsDisplay && (
                    <div className={styles.statCard}>
                      <div className={styles.statValue}>{yearsDisplay}</div>
                      <div className={styles.statLabel}>Years Exp.</div>
                    </div>
                  )}
                  {analysis.responsibilities?.length > 0 && (
                    <div className={styles.statCard}>
                      <div className={styles.statValue}>
                        {analysis.responsibilities.length}
                      </div>
                      <div className={styles.statLabel}>Responsibilities</div>
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
                    {selectedJob.icon && (
                      <span className={styles.jobIcon}>{selectedJob.icon}</span>
                    )}
                    <h2 className={styles.title}>{selectedJob.title}</h2>
                  </div>

                  {/* Meta row: organization, role title, updated */}
                  <div className={styles.jobMetaRow}>
                    {analysis?.organization && (
                      <span className={styles.metaPill}>🏢 {analysis.organization}</span>
                    )}
                    {analysis?.role_title && (
                      <span className={styles.metaPill}>🎯 {analysis.role_title}</span>
                    )}
                    {selectedJob.updated_at && (
                      <span className={styles.metaPill}>
                        Updated: {new Date(selectedJob.updated_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  {analysis?.summary && (
                    <p className={styles.summary}>{analysis.summary}</p>
                  )}
                </div>

                {/* Experience & Education */}
                {(yearsDisplay || analysis?.education?.length) && (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Experience & Education</h3>
                    <div className={styles.metaRow}>
                      {yearsDisplay && (
                        <span className={`${styles.metaPill} ${styles.pillInfo}`}>
                          📈 Experience: {yearsDisplay} years
                        </span>
                      )}
                      {analysis?.education?.length ? (
                        <div className={styles.inlineList}>
                          <span className={styles.badgeSecondary}>🎓 Education</span>
                          <div className={styles.skillsGrid}>
                            {analysis.education.map((ed) => (
                              <span key={ed} className={styles.skillTagSecondary}>
                                {ed}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                )}

                {/* Spoken Languages */}
                {analysis?.languages?.length ? (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Languages</h3>
                    <div className={styles.languagesList}>
                      {analysis.languages.map((l) => (
                        <span key={`${l.name}-${l.level ?? 'na'}`} className={styles.langChip}>
                          🗣️ {l.name}
                          {l.level && <span className={styles.langLevel}>{levelLabel(l.level)}</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {/* Skills - Must Have */}
                {analysis?.skills.must_have?.length ? (
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
                ) : null}

                {/* Skills - Nice to Have */}
                {analysis?.skills.nice_to_have?.length ? (
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
                ) : null}

                {/* Responsibilities */}
                {analysis?.responsibilities?.length ? (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Responsibilities</h3>
                    <ul className={styles.requirementsList}>
                      {analysis.responsibilities.map((item, idx) => (
                        <li key={idx} className={styles.requirementItem}>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {/* Requirements */}
                {analysis?.requirements?.length ? (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Requirements</h3>
                    <ul className={styles.requirementsList}>
                      {analysis.requirements.map((req, idx) => (
                        <li key={idx} className={styles.requirementItem}>
                          {req}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {/* Tech Stack */}
                {analysis?.tech_stack && (
                  <>
                    {analysis.tech_stack.languages?.length ? (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeTech}>Languages</span>
                          Programming Languages
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.languages.map((lang) => (
                            <span key={lang} className={styles.skillTag}>
                              💻 {lang}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {analysis.tech_stack.frameworks?.length ? (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeTech}>Frameworks</span>
                          Frameworks & Libraries
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.frameworks.map((fw) => (
                            <span key={fw} className={styles.skillTag}>
                              🔧 {fw}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {analysis.tech_stack.databases?.length ? (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeTech}>Data</span>
                          Databases
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.databases.map((db) => (
                            <span key={db} className={styles.skillTag}>
                              🗄️ {db}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {analysis.tech_stack.cloud?.length ? (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeCloud}>Cloud</span>
                          Cloud Providers & Services
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.cloud.map((c) => (
                            <span key={c} className={styles.skillTag}>
                              ☁️ {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {analysis.tech_stack.tools?.length ? (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeTools}>Tools</span>
                          Developer & Product Tools
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.tools.map((t) => (
                            <span key={t} className={styles.skillTag}>
                              🧰 {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {analysis.tech_stack.business?.length ? (
                      <div className={styles.section}>
                        <h3 className={styles.sectionTitle}>
                          <span className={styles.badgeBusiness}>Business</span>
                          Business & Domain Terms
                        </h3>
                        <div className={styles.skillsGrid}>
                          {analysis.tech_stack.business.map((b) => (
                            <span key={b} className={styles.skillTagSecondary}>
                              📈 {b}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </>
                )}

                {/* Keywords */}
                {analysis?.keywords?.length ? (
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
                ) : null}

                {/* Evidence (collapsible) */}
                {analysis?.evidence?.length ? (
                  <div className={styles.section}>
                    <details className={styles.evidence}>
                      <summary>Evidence (from job text)</summary>
                      <ul className={styles.evidenceList}>
                        {analysis.evidence.map((ev, idx) => (
                          <li key={idx}>{ev}</li>
                        ))}
                      </ul>
                    </details>
                  </div>
                ) : null}

                {/* Job Description */}
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Full Description</h3>
                  <div className={styles.description}>{selectedJob.job_description}</div>
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
                {analysis?.locations?.length ? (
                  <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>📍 Locations</h3>
                    <div className={styles.locationsList}>
                      {analysis.locations.map((loc) => (
                        <span key={loc} className={styles.location}>
                          {loc}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            ) : (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>🔍</div>
                <h3>Select a Job Position</h3>
                <p>
                  Choose a role from the dropdown to see detailed requirements and
                  generate your AI-powered candidate shortlist.
                </p>
              </div>
            )}
          </div>
        </div>
      </form>
    </section>
  );
}
