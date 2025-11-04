import type { ChangeEvent, FormEvent } from 'react'
import styles from './Form.module.css'
import type { JobOption } from '../../../types/ai-search'

type Props = {
  jobOptions: readonly JobOption[]
  selectedJobId: string
  desiredCandidates: number
  selectedJobOption?: JobOption
  previewHighlights: string[]
  onJobChange: (e: ChangeEvent<HTMLSelectElement>) => void
  onCandidateChange: (e: ChangeEvent<HTMLInputElement>) => void
  onSubmit: (e: FormEvent<HTMLFormElement>) => void
}

export default function Form({
  jobOptions,
  selectedJobId,
  desiredCandidates,
  selectedJobOption,
  previewHighlights,
  onJobChange,
  onCandidateChange,
  onSubmit
}: Props) {
  return (
    <section className={styles.wrapper}>
      <form className={styles.card} onSubmit={onSubmit}>
        <div className={styles.grid}>
          <div className={styles.left}>
            <div className={styles.field}>
              <label htmlFor="jobSelect" className={styles.label}>Select a role</label>
              <select
                id="jobSelect"
                className={styles.control}
                value={selectedJobId}
                onChange={onJobChange}
              >
                {jobOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <label htmlFor="candidateCount" className={styles.label}>Number of candidates</label>
              <input
                id="candidateCount"
                className={styles.control}
                type="number"
                min={1}
                max={8}
                value={desiredCandidates}
                onChange={onCandidateChange}
              />
              <span className={styles.hint}>
                Up to {selectedJobOption?.openings === 1 ? 'three' : 'six'} curated profiles available
              </span>
            </div>

            <div className={styles.actions}>
              <button type="submit" className={styles.primary}>Generate</button>
            </div>
          </div>

          <aside className={styles.right}>
            {selectedJobOption && (
              <>
                <h2 className={styles.title}>{selectedJobOption.label}</h2>
                <p className={styles.meta}>
                  Openings · {selectedJobOption.openings} · Top candidates ready in under 72 hours
                </p>
              </>
            )}
            <ul className={styles.list}>
              {previewHighlights.map((h) => (
                <li key={h} className={styles.item}>{h}</li>
              ))}
            </ul>
          </aside>
        </div>
      </form>
    </section>
  )
}
