import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ShieldCheck, Search, Users } from 'lucide-react';
import ImageSlider from '../components/ImageSlider';

const LandingPage = () => {
  const { t } = useTranslation();

  return (
    <div className="container animate-fade-in" style={styles.pageWrapper}>
      <ImageSlider />
      {/* Hero Section */}
      <div style={styles.hero}>
        <h1 style={styles.title}>
          {t('Welcome')}
          <span className="gradient-text" style={{ display: 'block', marginTop: '10px' }}>
            {t('Tagline')}
          </span>
        </h1>
        <p style={styles.subtitle}>
          {t('HomeTagline')}
        </p>
        
        <div style={styles.ctaGroup}>
          <Link to="/check" className="btn-primary" style={styles.mainBtn}>
            {t('CheckEligibilityBtn')}
          </Link>
          <Link to="/schemes" className="btn-secondary" style={styles.secBtn}>
            {t('BrowseSchemes')}
          </Link>
        </div>
      </div>

      {/* Features Section */}
      <div style={styles.features}>
        <Link to="/check" className="glass-card" style={styles.featureCard}>
          <div style={styles.iconWrapper}><ShieldCheck size={32} color="var(--primary-color)" /></div>
          <h3>{t('AIFeatureTitle')}</h3>
          <p>{t('AIFeatureDesc')}</p>
        </Link>
        <Link to="/schemes" className="glass-card" style={styles.featureCard}>
          <div style={styles.iconWrapper}><Search size={32} color="var(--secondary-color)" /></div>
          <h3>{t('DiscoveryFeatureTitle')}</h3>
          <p>{t('DiscoveryFeatureDesc')}</p>
        </Link>
        <div className="glass-card" style={styles.featureCard}>
          <div style={styles.iconWrapper}><Users size={32} color="#a855f7" /></div>
          <h3>{t('MultiLangFeatureTitle')}</h3>
          <p>{t('MultiLangFeatureDesc')}</p>
        </div>
      </div>
    </div>
  );
};

const styles = {
  pageWrapper: {
    minHeight: '80vh',
    display: 'flex',
    flexDirection: 'column',
    gap: '60px',
    paddingTop: '40px',
    paddingBottom: '80px',
  },
  hero: {
    textAlign: 'center',
    maxWidth: '800px',
    margin: '0 auto',
  },
  title: {
    fontSize: '3.5rem',
    marginBottom: '20px',
    lineHeight: 1.1,
  },
  subtitle: {
    fontSize: '1.25rem',
    color: 'var(--text-muted)',
    marginBottom: '40px',
    fontWeight: 300,
  },
  ctaGroup: {
    display: 'flex',
    justifyContent: 'center',
    gap: '20px',
    flexWrap: 'wrap',
  },
  mainBtn: {
    padding: '15px 30px',
    fontSize: '1.1rem',
    borderRadius: 'var(--border-radius-lg)',
  },
  secBtn: {
    padding: '15px 30px',
    fontSize: '1.1rem',
    borderRadius: 'var(--border-radius-lg)',
  },
  features: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '30px',
    marginTop: '40px',
  },
  featureCard: {
    padding: '30px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '15px',
    cursor: 'pointer',
    color: 'inherit',
    textDecoration: 'none',
  },
  iconWrapper: {
    background: 'rgba(255, 255, 255, 0.05)',
    padding: '20px',
    borderRadius: '50%',
    marginBottom: '10px',
  }
};

export default LandingPage;
