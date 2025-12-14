import { useState, useRef, useEffect, type ReactNode } from 'react';
import styles from './SegmentedControl.module.css';

export type SegmentOption = {
  value: string;
  label: string;
  icon?: ReactNode;
  count?: number;
  disabled?: boolean;
};

type SegmentedControlProps = {
  options: SegmentOption[];
  value: string;
  onChange: (value: string) => void;
};

export const SegmentedControl = ({ options, value, onChange }: SegmentedControlProps) => {
  const [indicatorStyle, setIndicatorStyle] = useState<React.CSSProperties>({});
  const segmentRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  useEffect(() => {
    const activeSegment = segmentRefs.current.get(value);
    if (activeSegment) {
      const { offsetLeft, offsetWidth, offsetHeight } = activeSegment;
      setIndicatorStyle({
        left: `${offsetLeft}px`,
        width: `${offsetWidth}px`,
        height: `${offsetHeight}px`,
        top: '4px',
      });
    }
  }, [value, options]);

  return (
    <div className={styles.segmentedControl}>
      <div className={styles.activeIndicator} style={indicatorStyle} />
      {options.map((option) => (
        <button
          key={option.value}
          ref={(el) => {
            if (el) {
              segmentRefs.current.set(option.value, el);
            }
          }}
          className={`${styles.segment} ${value === option.value ? styles.active : ''} ${option.disabled ? styles.disabled : ''}`}
          onClick={() => !option.disabled && onChange(option.value)}
          type="button"
          disabled={option.disabled}
        >
          {option.icon && <span className={styles.segmentIcon}>{option.icon}</span>}
          <span>{option.label}</span>
          {option.count !== undefined && (
            <span className={styles.badge}>{option.count}</span>
          )}
        </button>
      ))}
    </div>
  );
};
