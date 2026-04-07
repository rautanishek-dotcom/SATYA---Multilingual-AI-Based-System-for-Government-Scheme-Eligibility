import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Globe, Menu, X, User } from 'lucide-react';

const Navbar = () => {
  const { t, i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng);
    setIsOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('satya_token');
    localStorage.removeItem('satya_user');
    navigate('/login');
    setIsOpen(false);
  };

  const token = localStorage.getItem('satya_token');

  return (
    <nav style={styles.nav} className="glass-card">
      <div className="container" style={styles.navContainer}>
        <Link to="/" style={styles.logo} onClick={() => setIsOpen(false)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="24" viewBox="0 0 900 600" style={{ borderRadius: '2px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
              <rect width="900" height="200" fill="#FF9933"/>
              <rect y="200" width="900" height="200" fill="#FFFFFF"/>
              <rect y="400" width="900" height="200" fill="#138808"/>
              <g transform="translate(450, 300)">
                <circle r="92.5" fill="none" stroke="#000080" stroke-width="6.5"/>
                <circle r="17.5" fill="#000080"/>
                <g id="chakra">
                  <g id="spoke-group">
                    <g id="spoke">
                      <g id="single-spoke">
                        <path d="M0,-17.5 L-5.8,27.7 L0,75 L5.8,27.7 Z" fill="#000080"/>
                        <circle r="3.5" cy="-86" fill="#000080"/>
                      </g>
                      <use href="#single-spoke" transform="rotate(15)"/>
                    </g>
                    <use href="#spoke" transform="rotate(30)"/>
                  </g>
                  <use href="#spoke-group" transform="rotate(60)"/>
                </g>
                <use href="#chakra" transform="rotate(120)"/>
                <use href="#chakra" transform="rotate(240)"/>
              </g>
            </svg>
            <span className="gradient-text" style={{ fontSize: '1.8rem', fontWeight: 800, letterSpacing: '-0.5px' }}>SATYA</span>
          </div>
        </Link>

        {/* Desktop Menu */}
        <div style={styles.desktopMenu}>
          <Link to="/" style={styles.link}>{t('Home') || 'Home'}</Link>
          <Link to="/schemes" style={styles.link}>{t('Schemes')}</Link>
          <Link to="/check" style={styles.link}>{t('EligibilityEngine')}</Link>
          <Link to="/verify" style={styles.link}>{t('VerifyDocs', 'Verify Docs')}</Link>
          <Link to="/admin" style={styles.link}>{t('Admin', 'Admin')}</Link>
          
          <div style={styles.langSelector}>
            <Globe size={18} />
            <select 
              value={i18n.language} 
              onChange={(e) => changeLanguage(e.target.value)}
              style={styles.select}
            >
              <option value="en" style={{color: '#000'}}>English</option>
              <option value="hi" style={{color: '#000'}}>हिंदी (Hindi)</option>
              <option value="bn" style={{color: '#000'}}>বাংলা (Bengali)</option>
              <option value="mr" style={{color: '#000'}}>मराठी (Marathi)</option>
              <option value="te" style={{color: '#000'}}>తెలుగు (Telugu)</option>
              <option value="ta" style={{color: '#000'}}>தமிழ் (Tamil)</option>
              <option value="gu" style={{color: '#000'}}>ગુજરાતી (Gujarati)</option>
              <option value="kn" style={{color: '#000'}}>ಕನ್ನಡ (Kannada)</option>
              <option value="ml" style={{color: '#000'}}>മലയാളം (Malayalam)</option>
            </select>
          </div>
          
          {token ? (
            <button onClick={handleLogout} className="btn-secondary" style={styles.loginBtn}>
              <User size={16} /> {t('Logout', 'Logout')}
            </button>
          ) : (
            <Link to="/login" className="btn-secondary" style={styles.loginBtn}>
              <User size={16} /> {t('Login')}
            </Link>
          )}
        </div>

        {/* Mobile menu button */}
        <div style={styles.mobileMenuBtn} onClick={() => setIsOpen(!isOpen)}>
          {isOpen ? <X size={24} /> : <Menu size={24} />}
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div style={styles.mobileMenu} className="glass-card">
          <Link to="/" style={styles.mobileLink} onClick={() => setIsOpen(false)}>{t('Home')}</Link>
          <Link to="/schemes" style={styles.mobileLink} onClick={() => setIsOpen(false)}>{t('Schemes')}</Link>
          <Link to="/check" style={styles.mobileLink} onClick={() => setIsOpen(false)}>{t('EligibilityEngine')}</Link>
          <Link to="/verify" style={styles.mobileLink} onClick={() => setIsOpen(false)}>{t('VerifyDocs', 'Verify Docs')}</Link>
          <Link to="/admin" style={styles.mobileLink} onClick={() => setIsOpen(false)}>{t('Admin', 'Admin')}</Link>
          <div style={{ ...styles.mobileLink, ...styles.langSelector }}>
            <Globe size={18} />
            <select 
              value={i18n.language} 
              onChange={(e) => changeLanguage(e.target.value)}
              style={styles.select}
            >
              <option value="en" style={{color: '#000'}}>English</option>
              <option value="hi" style={{color: '#000'}}>हिंदी (Hindi)</option>
              <option value="bn" style={{color: '#000'}}>বাংলা (Bengali)</option>
              <option value="mr" style={{color: '#000'}}>मराठी (Marathi)</option>
              <option value="te" style={{color: '#000'}}>తెలుగు (Telugu)</option>
              <option value="ta" style={{color: '#000'}}>தமிழ் (Tamil)</option>
              <option value="gu" style={{color: '#000'}}>ગુજરાતી (Gujarati)</option>
              <option value="kn" style={{color: '#000'}}>ಕನ್ನಡ (Kannada)</option>
              <option value="ml" style={{color: '#000'}}>മലയാളം (Malayalam)</option>
            </select>
          </div>
          {token ? (
            <button onClick={handleLogout} style={{...styles.mobileLink, background: 'transparent', border: 'none', textAlign: 'left', width: '100%', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px'}}>
              <User size={16} /> {t('Logout', 'Logout')}
            </button>
          ) : (
            <Link to="/login" style={styles.mobileLink} onClick={() => setIsOpen(false)}>{t('Login')}</Link>
          )}
        </div>
      )}
    </nav>
  );
};

const styles = {
  nav: {
    position: 'fixed',
    top: 0,
    width: '100%',
    zIndex: 1000,
    borderRadius: 0,
    borderTop: 'none',
    borderLeft: 'none',
    borderRight: 'none',
  },
  navContainer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    height: '70px',
  },
  logo: {
    fontFamily: "var(--font-heading)",
  },
  desktopMenu: {
    display: 'flex',
    alignItems: 'center',
    gap: '30px',
  },
  link: {
    fontWeight: 500,
    fontSize: '1rem',
    color: 'var(--text-light)',
    transition: 'color 0.3s ease',
  },
  langSelector: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  select: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-light)',
    outline: 'none',
    cursor: 'pointer',
    fontWeight: 500,
  },
  loginBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
  },
  mobileMenuBtn: {
    display: 'none',
    cursor: 'pointer',
  },
  mobileMenu: {
    position: 'absolute',
    top: '70px',
    left: 0,
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    padding: '20px',
    borderTop: 'none',
    borderLeft: 'none',
    borderRight: 'none',
  },
  mobileLink: {
    padding: '15px 0',
    borderBottom: '1px solid var(--border-color)',
    color: 'var(--text-light)',
    fontWeight: 500,
  }
};

// Simple media query fix for inline styles (usually better done in CSS, but for quick scaffolding it's fine)
if (typeof window !== 'undefined') {
  const styleTag = document.createElement('style');
  styleTag.innerHTML = `
    @media (max-width: 768px) {
      .desktopMenu { display: none !important; }
      .mobileMenuBtn { display: block !important; }
    }
  `;
  document.head.appendChild(styleTag);
}

export default Navbar;
