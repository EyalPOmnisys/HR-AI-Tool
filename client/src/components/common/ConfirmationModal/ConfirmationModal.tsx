import { createPortal } from 'react-dom';
import type { ReactElement } from 'react';
import styles from './ConfirmationModal.module.css';

interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  cancelLabel?: string;
  isDangerous?: boolean;
}

export const ConfirmationModal = ({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDangerous = false,
}: ConfirmationModalProps): ReactElement | null => {
  if (!isOpen) return null;

  return createPortal(
    <div className={styles.overlay} onClick={onCancel}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3 className={styles.title}>{title}</h3>
        <p className={styles.message}>{message}</p>
        <div className={styles.actions}>
          <button 
            className={`${styles.button} ${styles.cancelButton}`} 
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button 
            className={`${styles.button} ${isDangerous ? styles.deleteButton : ''}`}
            onClick={onConfirm}
            style={!isDangerous ? { background: '#3b82f6', color: 'white' } : undefined}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};
