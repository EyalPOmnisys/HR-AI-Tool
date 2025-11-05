import type { ReactElement } from 'react';
import styles from './ProgressSteps.module.css';
import { FiCheckCircle, FiRadio } from 'react-icons/fi';

type Step = {
  title: string;
  // Optional sub label under the title (e.g., "Completed", "In Progress", "Pending")
  statusLabel?: string;
};

type Props = {
  steps: Step[];
  activeIndex: number;           // 0-based index of the current step
  isLoading?: boolean;           // when true, animate the connector towards the current step
  loadingDurationMs?: number;    // duration for the connector fill animation
};

export default function ProgressSteps({
  steps,
  activeIndex,
  isLoading = false,
  loadingDurationMs = 15000,
}: Props): ReactElement {
  return (
    <nav className={styles.wrapper} aria-label="Progress">
      <ol className={styles.list}>
        {steps.map((step, idx) => {
          const state: 'completed' | 'current' | 'upcoming' =
            idx < activeIndex ? 'completed' : idx === activeIndex ? 'current' : 'upcoming';

          return (
            <li key={step.title} className={styles.item}>
              {/* Connector BEFORE each item except the first */}
              {idx > 0 && (
                <div className={styles.connector} aria-hidden>
                  {/* Inner bar handles color + fill animation */}
                  <span
                    className={[
                      styles.connectorBar,
                      // Full green when the previous step is completed
                      idx < activeIndex ? styles.barFull : '',
                      // Animate towards the current step while loading
                      idx === activeIndex && isLoading ? styles.barAnim : '',
                      // Keep zero width for upcoming connectors
                      idx > activeIndex ? styles.barZero : '',
                    ].join(' ').trim()}
                    style={
                      idx === activeIndex && isLoading
                        ? ({ ['--connector-duration' as any]: `${loadingDurationMs}ms` } as React.CSSProperties)
                        : undefined
                    }
                  />
                </div>
              )}

              <div className={styles.step}>
                <div
                  className={`${styles.iconWrap} ${
                    state === 'completed'
                      ? styles.iconCompleted
                      : state === 'current'
                      ? styles.iconCurrent
                      : styles.iconUpcoming
                  }`}
                >
                  {state === 'completed' ? (
                    <FiCheckCircle className={styles.icon} aria-hidden />
                  ) : (
                    <FiRadio className={styles.icon} aria-hidden />
                  )}
                </div>

                <div className={styles.texts}>
                  <span
                    className={`${styles.title} ${
                      state === 'current' ? styles.titleCurrent : ''
                    }`}
                  >
                    {step.title}
                  </span>
                  {step.statusLabel && (
                    <span
                      className={`${styles.status} ${
                        state === 'completed'
                          ? styles.statusCompleted
                          : state === 'current'
                          ? styles.statusCurrent
                          : styles.statusUpcoming
                      }`}
                    >
                      {step.statusLabel}
                    </span>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
