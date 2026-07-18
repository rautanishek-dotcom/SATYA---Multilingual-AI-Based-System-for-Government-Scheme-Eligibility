import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail, Lock, LogIn } from 'lucide-react';

const Login = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({ email: '', password: '', role: 'user' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:5000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      
      if (response.ok) {
        localStorage.setItem('satya_token', data.token);
        localStorage.setItem('satya_user', JSON.stringify(data.user));
        
        // Redirect based on backend role returned
        if (data.user.role === 'admin') {
          navigate('/admin');
        } else {
          navigate('/');
        }
      } else {
        setError(data.error || t('LoginFailed', 'Login failed'));
      }
    } catch (err) {
      setError(t('ConnectionError', 'Cannot connect to server'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={styles.container}>
      <div className="glass-card" style={styles.card}>
        <div style={styles.header}>
          <h2 style={{ fontSize: '2rem', marginBottom: '10px' }}>
            {formData.role === 'admin' ? t('AdminLogin', 'Admin Login') : t('WelcomeBack')}
          </h2>
          <p style={{ color: 'var(--text-muted)' }}>{t('LoginSubtitle')}</p>
        </div>

        <div style={styles.roleSelector}>
          <button 
            type="button"
            onClick={() => setFormData({ ...formData, role: 'user' })}
            style={formData.role === 'user' ? styles.activeRole : styles.inactiveRole}
          >
            {t('User', 'User')}
          </button>
          <button 
            type="button"
            onClick={() => setFormData({ ...formData, role: 'admin' })}
            style={formData.role === 'admin' ? styles.activeRole : styles.inactiveRole}
          >
            {t('Admin', 'Admin')}
          </button>
        </div>

        {error && <div style={styles.errorBanner}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputGroup}>
            <label>{t('EmailAddress')}</label>
            <div style={styles.inputWrapper}>
              <Mail size={18} style={styles.icon} color="var(--text-muted)" />
              <input 
                type="email" 
                name="email" 
                value={formData.email} 
                onChange={handleChange} 
                required 
                style={styles.input} 
                placeholder={t('EmailPlaceholder')}
              />
            </div>
          </div>

          <div style={styles.inputGroup}>
            <label>{t('Password')}</label>
            <div style={styles.inputWrapper}>
              <Lock size={18} style={styles.icon} color="var(--text-muted)" />
              <input 
                type="password" 
                name="password" 
                value={formData.password} 
                onChange={handleChange} 
                required 
                style={styles.input} 
                placeholder="••••••••"
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" style={styles.submitBtn} disabled={loading}>
            {loading ? t('Authenticating') : <><LogIn size={18} /> {t('Login')}</>}
          </button>
        </form>

        <p style={styles.footerText}>
          {t('NoAccount')} <Link to="/register" style={styles.link}>{t('SignUpSecurely')}</Link>
        </p>
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '80vh',
  },
  card: {
    width: '100%',
    maxWidth: '450px',
    padding: '40px',
  },
  header: {
    textAlign: 'center',
    marginBottom: '30px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  inputWrapper: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  icon: {
    position: 'absolute',
    left: '15px',
  },
  input: {
    width: '100%',
    padding: '12px 15px 12px 45px',
    fontSize: '1rem',
    background: 'rgba(0, 0, 0, 0.2)',
  },
  submitBtn: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '10px',
    padding: '15px',
    fontSize: '1.1rem',
    marginTop: '10px',
  },
  footerText: {
    textAlign: 'center',
    marginTop: '25px',
    color: 'var(--text-muted)',
  },
  link: {
    color: 'var(--primary-color)',
    fontWeight: 600,
  },
  errorBanner: {
    background: 'rgba(239, 68, 68, 0.1)',
    color: 'var(--error-color)',
    padding: '10px',
    borderRadius: 'var(--border-radius)',
    textAlign: 'center',
    marginBottom: '20px',
    border: '1px solid rgba(239, 68, 68, 0.3)',
  },
  roleSelector: {
    display: 'flex',
    background: 'rgba(0, 0, 0, 0.2)',
    padding: '5px',
    borderRadius: 'var(--border-radius)',
    marginBottom: '25px',
  },
  activeRole: {
    flex: 1,
    padding: '10px',
    border: 'none',
    borderRadius: 'calc(var(--border-radius) - 2px)',
    background: 'var(--primary-color)',
    color: 'white',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  inactiveRole: {
    flex: 1,
    padding: '10px',
    border: 'none',
    background: 'transparent',
    color: 'var(--text-muted)',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  }
};

export default Login;
