import type { ReactElement } from 'react'
import { ResumeCard } from '../../components/Resume/ResumeCard/ResumeCard'
import type { ResumeSummary } from '../../types/resume'
import styles from './Resumes.module.css'

const resumes: ReadonlyArray<ResumeSummary> = [
  { id: 'noa-levy', name: 'Noa Levy', resumeUrl: 'https://example.com/cv/noa-levy.pdf' },
  { id: 'amir-rosen', name: 'Amir Rosen', resumeUrl: 'https://example.com/cv/amir-rosen.pdf' },
  { id: 'mira-klein', name: 'Mira Klein', resumeUrl: 'https://example.com/cv/mira-klein.pdf' },
  { id: 'david-cohen', name: 'David Cohen', resumeUrl: 'https://example.com/cv/david-cohen.pdf' },
  { id: 'lia-bar', name: 'Lia Bar', resumeUrl: 'https://example.com/cv/lia-bar.pdf' },
  { id: 'tomer-shai', name: 'Tomer Shai', resumeUrl: 'https://example.com/cv/tomer-shai.pdf' },
  { id: 'gal-oren', name: 'Gal Oren', resumeUrl: 'https://example.com/cv/gal-oren.pdf' },
  { id: 'adi-freeman', name: 'Adi Freeman', resumeUrl: 'https://example.com/cv/adi-freeman.pdf' },
  { id: 'rony-hazan', name: 'Rony Hazan', resumeUrl: 'https://example.com/cv/rony-hazan.pdf' },
  { id: 'matan-sela', name: 'Matan Sela', resumeUrl: 'https://example.com/cv/matan-sela.pdf' },
  { id: 'yael-karni', name: 'Yael Karni', resumeUrl: 'https://example.com/cv/yael-karni.pdf' },
  { id: 'shai-bendor', name: 'Shai Bendor', resumeUrl: 'https://example.com/cv/shai-bendor.pdf' },
  { id: 'daniela-ron', name: 'Daniela Ron', resumeUrl: 'https://example.com/cv/daniela-ron.pdf' },
  { id: 'itai-karp', name: 'Itai Karp', resumeUrl: 'https://example.com/cv/itai-karp.pdf' },
  { id: 'shir-ella', name: 'Shir Ella', resumeUrl: 'https://example.com/cv/shir-ella.pdf' },
  { id: 'yonatan-lev', name: 'Yonatan Lev', resumeUrl: 'https://example.com/cv/yonatan-lev.pdf' }
]

export const Resumes = (): ReactElement => {
  return (
    <section className={styles.page} aria-labelledby="resumes-title">
      <header className={styles.header}>
        <h1 id="resumes-title" className={styles.title}>
          Resumes
        </h1>
        <p className={styles.subtitle}>
          Browse a compact list of submitted CVs. Select a candidate to jump straight into their full resume.
        </p>
      </header>

      <ul className={styles.list}>
        {resumes.map((resume) => (
          <li key={resume.id}>
            <ResumeCard resume={resume} />
          </li>
        ))}
      </ul>
    </section>
  )
}
