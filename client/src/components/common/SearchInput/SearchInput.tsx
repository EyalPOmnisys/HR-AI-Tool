import { forwardRef } from 'react';
import type { ChangeEvent, InputHTMLAttributes, ReactElement } from 'react';

import styles from './SearchInput.module.css';

type SearchInputProps = {
  value: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  isLoading?: boolean;
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'type'>;

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ value, onChange, placeholder = 'Search…', isLoading = false, className = '', ...rest }, ref): ReactElement => {
    return (
      <div className={`${styles.wrapper} ${className}`}>
        <input
          ref={ref}
          type="search"
          className={styles.input}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          aria-label={placeholder}
          autoComplete="off"
          spellCheck={false}
          {...rest}
        />
        <div className={styles.icon} aria-hidden>
          <svg viewBox="0 0 24 24" focusable="false">
            <path
              d="M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14zm0-2C6.582 2 3 5.582 3 10s3.582 8 8 8a7.95 7.95 0 0 0 4.9-1.65l3.875 3.877a1 1 0 0 0 1.414-1.414L17.3 15.9A7.95 7.95 0 0 0 19 10c0-4.418-3.582-8-8-8z"
              fill="currentColor"
            />
          </svg>
        </div>
        {isLoading && <span className={styles.spinner} aria-hidden />}
      </div>
    );
  }
);

SearchInput.displayName = 'SearchInput';
