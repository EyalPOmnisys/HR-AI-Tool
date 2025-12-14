import { useState, useEffect } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import { getJob, getJobCandidates } from '../../services/jobs';
import type { ApiJob, JobAnalysis, TechStack } from '../../types/job';
import type { CandidateRow, MatchRunResponse } from '../../types/match';
import Dashboard from '../../components/ai-search/Dashboard/Dashboard';
import MatchStatsPanel from '../../components/ai-search/Stats/MatchStatsPanel';
import { FiArrowLeft, FiChevronDown } from 'react-icons/fi';

type Props = {
  jobId: string;
  onBack: () => void;
};

export default function JobDetails({ jobId, onBack }: Props) {
  const [job, setJob] = useState<ApiJob | null>(null);
  const [candidates, setCandidates] = useState<CandidateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [descriptionExpanded, setDescriptionExpanded] = useState(false);

  useEffect(() => {
    async function loadData() {
      if (!jobId) return;
      try {
        setLoading(true);
        // Load job details and candidates in parallel
        const [jobData, candidatesData] = await Promise.all([
          getJob(jobId),
          getJobCandidates(jobId)
        ]);
        
        // Filter candidates to only show those who have completed the full process (have LLM score)
        // This hides candidates who only have a RAG score (Stage 1) but haven't been processed by LLM (Stage 2)
        const fullyProcessedCandidates = candidatesData.filter(c => c.llm_score !== undefined && c.llm_score !== null);

        setJob(jobData);
        setCandidates(fullyProcessedCandidates);
        
        // If no candidates found, open description by default
        if (fullyProcessedCandidates.length === 0) {
          setDescriptionExpanded(true);
        }
      } catch (err) {
        console.error("Failed to load job details:", err);
        setError("Failed to load job details.");
      } finally {
        setLoading(false);
      }
    }
    
    loadData();
  }, [jobId]);

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading job details...</div>;
  if (error) return <div style={{ padding: '2rem', textAlign: 'center', color: '#ef4444' }}>{error}</div>;
  if (!job) return <div style={{ padding: '2rem', textAlign: 'center' }}>Job not found</div>;

  // Adapt data for the Dashboard component
  // In JobDetails, all candidates are existing (from DB), so they should be in previousCandidates, not new_candidates
  const matchResponse: MatchRunResponse = {
    job_id: job.id,
    requested_top_n: candidates.length,
    min_threshold: 0,
    new_candidates: [], // No new candidates in JobDetails view - all are existing
    new_count: 0,
    previously_reviewed_count: candidates.length,
    all_candidates_already_reviewed: true
  };

  type LegacyJobAnalysis = JobAnalysis & { years_of_experience?: number | null };
  const jobMeta = (job.analysis_json ?? null) as LegacyJobAnalysis | null;
  const experienceRange = jobMeta?.experience;
  let experienceLabel: string | null = null;
  if (experienceRange && (experienceRange.years_min || experienceRange.years_max)) {
    const min = experienceRange.years_min;
    const max = experienceRange.years_max;
    if (min && max) {
      experienceLabel = `${min}-${max} yrs`;
    } else if (min) {
      experienceLabel = `${min}+ yrs`;
    } else if (max) {
      experienceLabel = `Up to ${max} yrs`;
    }
  } else if (typeof jobMeta?.years_of_experience === 'number') {
    experienceLabel = `${jobMeta.years_of_experience} yrs`;
  }

  const salaryRange = jobMeta?.salary_range;
  let salaryLabel: string | null = null;
  if (salaryRange && (salaryRange.min || salaryRange.max)) {
    const currency = salaryRange.currency ?? '';
    if (salaryRange.min && salaryRange.max) {
      salaryLabel = `${currency} ${salaryRange.min.toLocaleString()} - ${salaryRange.max.toLocaleString()}`;
    } else if (salaryRange.min) {
      salaryLabel = `${currency} ${salaryRange.min.toLocaleString()}+`;
    } else if (salaryRange.max) {
      salaryLabel = `Up to ${currency} ${salaryRange.max.toLocaleString()}`;
    }
  }

  const hasDescriptionContent = Boolean(job.job_description || job.analysis_json);

  const headerCardStyle: CSSProperties = {
    background: '#f0f9ff',
    borderRadius: '12px',
    padding: '20px 24px',
    border: '1px solid #e0f2fe',
    marginBottom: '16px',
    boxShadow: '0 1px 3px rgba(59, 130, 246, 0.08)'
  };

  const metaBadgeStyle: CSSProperties = {
    display: 'inline-flex',
    flexDirection: 'column',
    padding: '10px 14px',
    borderRadius: '8px',
    background: '#ffffff',
    border: '1px solid #e0f2fe',
    minWidth: '130px',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.03)'
  };

  const metaItems = [
    { label: 'Experience', value: experienceLabel },
    { label: 'Salary Range', value: salaryLabel },
    { label: 'Candidates', value: `${candidates.length}` },
  ].filter((item) => Boolean(item.value));

  return (
    <div style={{ padding: '2rem clamp(1.5rem, 4vw, 3.5rem)', width: '100%' }}>
      <button 
        onClick={onBack}
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem',
          color: '#4b5563',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          marginBottom: '1.5rem',
          fontSize: '1rem'
        }}
      >
        <FiArrowLeft /> Back to Jobs
      </button>

      <div style={headerCardStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
              display: 'grid',
              placeItems: 'center',
              fontSize: '24px',
              boxShadow: '0 2px 4px rgba(59, 130, 246, 0.1)'
            }}>
              {job.icon || '💼'}
            </div>
            <div>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', margin: 0, letterSpacing: '-0.01em' }}>{job.title}</h1>
              {jobMeta?.organization && (
                <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '0.9rem', fontWeight: 500 }}>{jobMeta.organization}</p>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {metaItems.map((item) => (
              <div key={item.label} style={metaBadgeStyle}>
                <span style={{ fontSize: '0.7rem', color: '#64748b', letterSpacing: '0.04em', textTransform: 'uppercase', fontWeight: 600 }}>{item.label}</span>
                <strong style={{ fontSize: '0.95rem', color: '#0f172a', marginTop: '4px', fontWeight: 600 }}>{item.value}</strong>
              </div>
            ))}
          </div>
        </div>

        {hasDescriptionContent && (
          <div style={{ marginTop: '20px', borderTop: '1px solid #bfdbfe', paddingTop: '12px' }}>
            <button
              type="button"
              onClick={() => setDescriptionExpanded((prev) => !prev)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#0f172a',
                padding: '8px 0',
                width: '100%'
              }}
            >
              <span>View Job Description</span>
              <FiChevronDown
                style={{
                  transition: 'transform 0.25s ease',
                  transform: descriptionExpanded ? 'rotate(180deg)' : 'rotate(0deg)'
                }}
              />
            </button>
            
            <div style={{
                maxHeight: descriptionExpanded ? '2000px' : '0px',
                opacity: descriptionExpanded ? 1 : 0,
                overflow: 'hidden',
                transition: 'all 0.4s ease',
                marginTop: descriptionExpanded ? '16px' : '0'
            }}>
                <JobDescriptionSections job={job} />
            </div>
          </div>
        )}
      </div>

      <Dashboard matchResults={matchResponse} selectedJob={job} showJobHeader={false} previousCandidates={candidates} />
      <MatchStatsPanel candidates={candidates} variant="minimal" />
    </div>
  );
}

const sectionContainerStyle: CSSProperties = {
  display: 'grid',
  gap: '14px',
  marginBottom: '0'
};

const sectionStyle: CSSProperties = {
  background: '#fafafa',
  borderRadius: '12px',
  padding: '18px 22px',
  border: '1px solid #e5e7eb'
};

const sectionTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: '1rem',
  fontWeight: 600,
  color: '#111827'
};

const badgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '5px 11px',
  borderRadius: '999px',
  background: '#f3f4f6',
  color: '#1f2937',
  fontSize: '0.82rem',
  fontWeight: 500,
  marginRight: '7px',
  marginBottom: '7px',
  border: '1px solid #e5e7eb'
};

const listStyle: CSSProperties = {
  margin: '10px 0 0',
  paddingLeft: '18px',
  color: '#374151',
  lineHeight: 1.6
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={sectionStyle}>
      <h3 style={sectionTitleStyle}>{title}</h3>
      <div style={{ marginTop: '10px', color: '#1f2937' }}>{children}</div>
    </section>
  );
}

function JobDescriptionSections({ job }: { job: ApiJob }) {
  const data = job.analysis_json;
  if (!data && !job.job_description) {
    return null;
  }

  const sections: ReactNode[] = [];

  if (data?.summary) {
    sections.push(
      <Section key="summary" title="Summary">
        <p style={{ margin: 0, lineHeight: 1.7 }}>{data.summary}</p>
      </Section>
    );
  }

  if (data?.experience || data?.salary_range) {
    const experience = data.experience;
    const salary = data.salary_range;
    sections.push(
      <Section key="details" title="Position Details">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
          {experience && (experience.years_min || experience.years_max) && (
            <span style={badgeStyle}>
              💼 Experience: {experience.years_min && experience.years_max
                ? `${experience.years_min}-${experience.years_max} yrs`
                : experience.years_min
                ? `${experience.years_min}+ yrs`
                : `Up to ${experience.years_max} yrs`}
            </span>
          )}
          {salary && (salary.min || salary.max) && (
            <span style={badgeStyle}>
              💰 Salary: {salary.min && salary.max
                ? `${salary.currency ?? ''} ${salary.min.toLocaleString()} - ${salary.max.toLocaleString()}`
                : salary.min
                ? `${salary.currency ?? ''} ${salary.min.toLocaleString()}+`
                : `Up to ${salary.currency ?? ''} ${salary.max?.toLocaleString()}`}
            </span>
          )}
        </div>
      </Section>
    );
  }

  if (Array.isArray(data?.locations) && data.locations.length) {
    sections.push(
      <Section key="locations" title="Locations">
        <div>
          {data.locations.map((loc: string, idx: number) => (
            <span key={`${loc}-${idx}`} style={badgeStyle}>📍 {loc}</span>
          ))}
        </div>
      </Section>
    );
  }

  if (Array.isArray(data?.requirements) && data.requirements.length) {
    sections.push(
      <Section key="requirements" title="Key Requirements">
        <ul style={listStyle}>
          {data.requirements.map((req: string, idx: number) => (
            <li key={idx}>{req}</li>
          ))}
        </ul>
      </Section>
    );
  }

  if (Array.isArray(data?.responsibilities) && data.responsibilities.length) {
    sections.push(
      <Section key="responsibilities" title="Responsibilities">
        <ul style={listStyle}>
          {data.responsibilities.map((item: string, idx: number) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </Section>
    );
  }

  const skills = data?.skills;
  if (Array.isArray(skills?.must_have) && skills.must_have.length) {
    sections.push(
      <Section key="must-have" title="Must Have Skills">
        <div>
          {skills.must_have.map((skill: string, idx: number) => (
            <span key={`${skill}-${idx}`} style={badgeStyle}>{skill}</span>
          ))}
        </div>
      </Section>
    );
  }

  if (Array.isArray(skills?.nice_to_have) && skills.nice_to_have.length) {
    sections.push(
      <Section key="nice-to-have" title="Nice to Have Skills">
        <div>
          {skills.nice_to_have.map((skill: string, idx: number) => (
            <span key={`${skill}-${idx}`} style={{ ...badgeStyle, background: '#fef3c7', color: '#92400e' }}>{skill}</span>
          ))}
        </div>
      </Section>
    );
  }

  const tech = data?.tech_stack;
  const techCategories: Array<keyof TechStack> = ['languages', 'frameworks', 'databases', 'cloud', 'tools', 'business'];
  if (
    tech &&
    techCategories.some((category) => Array.isArray(tech[category]) && tech[category].length)
  ) {
    sections.push(
      <Section key="tech" title="Tech Stack">
        <div style={{ display: 'grid', gap: '8px' }}>
          {techCategories.map((category) => {
            const items = tech[category];
            if (!Array.isArray(items) || items.length === 0) return null;
            return (
              <div key={category}>
                <strong style={{ textTransform: 'capitalize', color: '#475569' }}>{category}</strong>
                <div style={{ marginTop: '6px' }}>
                  {items.map((item: string, idx: number) => (
                    <span key={`${category}-${item}-${idx}`} style={badgeStyle}>{item}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </Section>
    );
  }

  if (Array.isArray(data?.education) && data.education.length) {
    sections.push(
      <Section key="education" title="Education Requirements">
        <ul style={listStyle}>
          {data.education.map((edu: string, idx: number) => (
            <li key={idx}>{edu}</li>
          ))}
        </ul>
      </Section>
    );
  }

  if (Array.isArray(data?.languages) && data.languages.length) {
    sections.push(
      <Section key="languages" title="Language Requirements">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {data.languages.map((lang: any, idx: number) => (
            <span key={idx} style={badgeStyle}>
              {lang.name || lang}
              {lang.level && <span style={{ marginLeft: '6px', color: '#475569' }}>{lang.level}</span>}
            </span>
          ))}
        </div>
      </Section>
    );
  }

  if (job.job_description) {
    sections.push(
      <Section key="original" title="Original Description">
        <p style={{ margin: 0, lineHeight: 1.7 }}>{job.job_description}</p>
      </Section>
    );
  }

  if (!sections.length) {
    return null;
  }

  return <div style={sectionContainerStyle}>{sections}</div>;
}
