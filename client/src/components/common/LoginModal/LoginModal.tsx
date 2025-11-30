import React, { useState } from 'react';
import styles from './LoginModal.module.css';
import logo from '../../../assets/logo.png';
import { FaEye, FaEyeSlash } from 'react-icons/fa';

interface LoginModalProps {
  onLogin: (password: string) => boolean;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onLogin }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const success = onLogin(password);
    if (!success) {
      setError('Incorrect password, please try again');
      setPassword('');
    }
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <div className={styles.logoContainer}>
            <img src={logo} alt="OmniAI HR Logo" className={styles.logo} />
          </div>
          <div>
            <h1 className={styles.appName}>OmniAI HR</h1>
            <p className={styles.appDesc}>AI-Powered Hiring Platform</p>
          </div>
        </div>
        
        <h2 className={styles.title}>Welcome Back</h2>
        
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.inputWrapper}>
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password..."
              className={styles.input}
              autoFocus
            />
            <button
              type="button"
              className={styles.eyeButton}
              onClick={() => setShowPassword(!showPassword)}
              tabIndex={-1}
            >
              {showPassword ? <FaEyeSlash /> : <FaEye />}
            </button>
          </div>
          <button type="submit" className={styles.button}>
            Login
          </button>
        </form>
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
};
