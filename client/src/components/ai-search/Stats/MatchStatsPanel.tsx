import { useMemo } from 'react'
import styles from './MatchStatsPanel.module.css'
import type { CandidateRow } from '../../../types/match'
import { calculateAnalysis } from '../../../utils/statsUtils'

type Props = {
  candidates: CandidateRow[]
  variant?: 'default' | 'minimal'
}

export default function MatchStatsPanel({ candidates, variant = 'default' }: Props) {
  const data = useMemo(() => calculateAnalysis(candidates), [candidates])

  if (!candidates || candidates.length === 0) {
    return null
  }

  // Helper to create conic-gradient string for donut
  const getDonutGradient = () => {
    let currentAngle = 0
    const parts = data.verdictBreakdown.map(item => {
      const start = currentAngle
      const end = currentAngle + (item.percentage * 3.6) // 3.6 deg per 1%
      currentAngle = end
      return `${item.color} ${start}deg ${end}deg`
    })
    return `conic-gradient(${parts.join(', ')})`
  }

  return (
    <section className={`${styles.statsSection} ${variant === 'minimal' ? styles.minimal : ''}`}>
      {variant !== 'minimal' && (
        <div className={styles.header}>
          <h3 className={styles.title}>Match Analysis</h3>
          <span className={styles.subtitle}>Based on {data.totalCandidates} candidates</span>
        </div>
      )}

      <div className={styles.grid}>
        {/* 1. Quality Funnel */}
        <div className={styles.card}>
          <div className={styles.cardTitle}>Quality Funnel</div>
          <div className={styles.donutContainer}>
            <div 
              className={styles.donutChart} 
              style={{ background: getDonutGradient() }}
            >
              <div className={styles.donutHole}>
                {data.totalCandidates}
              </div>
            </div>
          </div>
          <div className={styles.legend}>
            {data.verdictBreakdown.map(item => (
              <div key={item.label} className={styles.legendItem}>
                <div className={styles.legendColor} style={{ backgroundColor: item.color }} />
                <span style={{ flex: 1 }}>{item.label}</span>
                <span style={{ fontWeight: 600 }}>{item.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 2. Experience Level Distribution */}
        <div className={styles.card}>
          <div className={styles.cardTitle}>Experience Levels</div>
          <div className={styles.skillList}>
            {data.experienceDistribution.length > 0 ? (
              data.experienceDistribution.map(item => (
                <div key={item.label} className={styles.skillItem}>
                  <div className={styles.skillHeader}>
                    <span>{item.label}</span>
                    <span>{item.count} ({item.percentage}%)</span>
                  </div>
                  <div className={styles.progressBarBg}>
                    <div 
                      className={styles.progressBarFill} 
                      style={{ 
                        width: `${item.percentage}%`,
                        backgroundColor: item.color 
                      }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div style={{ color: '#9ca3af', fontSize: '0.8rem', textAlign: 'center', marginTop: '20px' }}>
                No experience data available
              </div>
            )}
          </div>
        </div>

        {/* 3. Score Distribution */}
        <div className={styles.card}>
          <div className={styles.cardTitle}>Score Distribution</div>
          <div className={styles.histogram}>
            {data.scoreDistribution.map(item => {
              // Calculate height relative to max count, min 4px
              const maxCount = Math.max(...data.scoreDistribution.map(d => d.count)) || 1
              const heightPercent = Math.max((item.count / maxCount) * 100, 5)
              
              return (
                <div key={item.range} className={styles.barContainer}>
                  <div className={styles.barValue}>{item.count > 0 ? item.count : ''}</div>
                  <div 
                    className={styles.bar} 
                    style={{ 
                      height: `${heightPercent}%`, 
                      backgroundColor: item.color 
                    }} 
                  />
                  <div className={styles.barLabel}>{item.range}</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* 4. Top Talent Metrics */}
        <div className={styles.card}>
          <div className={styles.cardTitle}>Top Talent Metrics</div>
          <div className={styles.metricsGrid}>
            <div className={`${styles.metricBox} ${styles.topCandidateBox}`}>
              <div className={styles.metricValue}>{data.topTalentStats.topCandidateName}</div>
              <div className={styles.metricLabel}>Top Candidate</div>
            </div>
            <div className={styles.metricBox}>
              <div className={styles.metricValue}>{data.topTalentStats.highestScore}</div>
              <div className={styles.metricLabel}>Top Score</div>
            </div>
            <div className={styles.metricBox}>
              <div className={styles.metricValue}>{data.topTalentStats.avgExperience}y</div>
              <div className={styles.metricLabel}>Avg Exp.</div>
            </div>
            <div className={styles.metricBox}>
              <div className={styles.metricValue}>{data.topTalentStats.avgStability}%</div>
              <div className={styles.metricLabel}>Avg Stability</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
