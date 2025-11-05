import React from 'react'
import styles from './Skeleton.module.css'

type SkeletonProps = React.HTMLAttributes<HTMLDivElement> & {
  width?: number | string
  height?: number | string
  radius?: number | string
}

export const Skeleton = ({ width = '100%', height = 12, radius = 8, style, ...rest }: SkeletonProps) => (
  <div
    className={styles.skeleton}
    style={{ width, height, borderRadius: radius, ...style }}
    {...rest}
  />
)

export const SkeletonText = ({ lines = 2, lineHeight = 12, gap = 6 }: { lines?: number; lineHeight?: number; gap?: number }) => {
  return (
    <div className={styles.stack}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height={lineHeight}
          width={`${100 - (i === lines - 1 ? 30 : 0)}%`}
          style={{ marginBottom: i === lines - 1 ? 0 : gap }}
        />
      ))}
    </div>
  )
}

export const SkeletonChipRow = ({ chips = 3, chipWidth = 70, chipHeight = 18, gap = 6, style }: { chips?: number; chipWidth?: number; chipHeight?: number; gap?: number; style?: React.CSSProperties }) => {
  return (
    <div className={styles.row} style={{ gap, ...style }}>
      {Array.from({ length: chips }).map((_, i) => (
        <Skeleton key={i} width={chipWidth} height={chipHeight} radius={10} />
      ))}
    </div>
  )
}
