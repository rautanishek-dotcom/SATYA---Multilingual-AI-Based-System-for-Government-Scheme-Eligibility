import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, ChevronRight, Search, X, Target, ClipboardList, Info, ExternalLink, ShieldCheck, FileCheck } from 'lucide-react';
import DocumentVerification from '../components/DocumentVerification';

const EligibilityForm = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    gender: '',
    state: '',
    district: '',
    income: '',
    occupation: '',
    category: 'general',
    special_category: 'none'
  });

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [isVerified, setIsVerified] = useState(false);
  const [showVerification, setShowVerification] = useState(false);
  const [userId, setUserId] = useState(null);

  React.useEffect(() => {
    try {
      const userStr = localStorage.getItem('satya_user');
      if (userStr && userStr !== 'undefined' && userStr !== 'null') {
        const userObj = JSON.parse(userStr);
        if (userObj && userObj.id) {
          setUserId(userObj.id);
        }
      }
    } catch (err) {
      console.error("Error parsing user data:", err);
    }
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = { ...formData, user_id: userId };

      // Assuming backend is running on localhost:5000
      const response = await fetch('http://localhost:5000/api/schemes/eligible', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      setResults(data);
      setShowVerification(true); // Trigger verification step
    } catch (error) {
      console.error("Error fetching eligible schemes:", error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container animate-fade-in" style={styles.container}>
      <div style={styles.header}>
        <h2 style={{ fontSize: '2.5rem', marginBottom: '10px' }}>{t('Profile')}</h2>
        <p style={{ color: 'var(--text-muted)' }}>Fill in your details accurately to find government schemes you are eligible for.</p>
      </div>

      <div style={styles.layout}>
        {/* Form Section */}
        <div className="glass-card" style={styles.formCard}>
          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.inputGroup}>
              <label>{t('Name')}</label>
              <input type="text" name="name" value={formData.name} onChange={handleChange} required style={styles.input} />
            </div>

            <div style={styles.row}>
              <div style={styles.inputGroup}>
                <label>{t('Age')}</label>
                <input type="number" name="age" value={formData.age} onChange={handleChange} required style={styles.input} min="0" />
              </div>
              <div style={styles.inputGroup}>
                <label>{t('Gender')}</label>
                <select name="gender" value={formData.gender} onChange={handleChange} style={styles.input} required>
                  <option value="" disabled style={{color: '#000'}}>Select Gender</option>
                  <option value="male" style={{color: '#000'}}>Male</option>
                  <option value="female" style={{color: '#000'}}>Female</option>
                  <option value="other" style={{color: '#000'}}>Other</option>
                </select>
              </div>
            </div>

            <div style={styles.row}>
              <div style={styles.inputGroup}>
                <label>{t('State')}</label>
                <input type="text" name="state" value={formData.state} onChange={handleChange} required style={styles.input} />
              </div>
              <div style={styles.inputGroup}>
                <label>{t('District')}</label>
                <input type="text" name="district" value={formData.district} onChange={handleChange} required style={styles.input} />
              </div>
            </div>

            <div style={styles.inputGroup}>
              <label>{t('Income')} (₹)</label>
              <input type="number" name="income" value={formData.income} onChange={handleChange} required style={styles.input} min="0" />
            </div>

            <div style={styles.row}>
              <div style={styles.inputGroup}>
                <label>{t('Category')}</label>
                <select name="category" value={formData.category} onChange={handleChange} style={styles.input}>
                  <option value="general" style={{color: '#000'}}>General</option>
                  <option value="obc" style={{color: '#000'}}>OBC</option>
                  <option value="sc" style={{color: '#000'}}>SC</option>
                  <option value="st" style={{color: '#000'}}>ST</option>
                </select>
              </div>
              <div style={styles.inputGroup}>
                <label>{t('SpecialCategory')}</label>
                <select name="special_category" value={formData.special_category} onChange={handleChange} style={styles.input}>
                  <option value="none" style={{color: '#000'}}>None</option>
                  <option value="woman" style={{color: '#000'}}>Woman</option>
                  <option value="farmer" style={{color: '#000'}}>Farmer</option>
                  <option value="student" style={{color: '#000'}}>Student</option>
                  <option value="entrepreneur" style={{color: '#000'}}>Entrepreneur</option>
                  <option value="senior_citizen" style={{color: '#000'}}>Senior Citizen</option>
                  <option value="disabled" style={{color: '#000'}}>Disabled</option>
                </select>
              </div>
            </div>

            <div style={styles.inputGroup}>
              <label>{t('Occupation')}</label>
              <input type="text" name="occupation" value={formData.occupation} onChange={handleChange} style={styles.input} />
            </div>

            <button type="submit" className="btn-primary" style={styles.submitBtn} disabled={loading}>
              {loading ? 'Analyzing...' : t('Submit')} <ChevronRight size={18} />
            </button>
          </form>
        </div>

        {/* Results Section */}
        <div style={styles.resultsArea}>
          {showVerification && !isVerified ? (
            <DocumentVerification 
              userId={userId} 
              profileData={formData} 
              onVerificationComplete={(status) => setIsVerified(status)} 
            />
          ) : results === null ? (
             <div className="glass-card" style={styles.placeholderCard}>
                <Search size={48} color="var(--text-muted)" style={{ marginBottom: '20px' }} />
                <h3>Waiting for your profile</h3>
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '10px' }}>
                  Submit the form to see your eligible schemes here.
                </p>
             </div>
          ) : isVerified ? (
            <div style={styles.resultsContainer}>
              <h3 style={{ fontSize: '1.5rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <CheckCircle2 color="var(--secondary-color)" />
                {t('EligibleSchemes')} ({results.length})
              </h3>
              
              {results.length === 0 ? (
                <div className="glass-card" style={{ padding: '30px', textAlign: 'center' }}>
                  <p>We couldn't find exact matches. Try updating your profile or browsing all schemes.</p>
                </div>
              ) : (
                <div style={styles.schemeList}>
                  {results.map((scheme, idx) => (
                    <div key={idx} className="glass-card" style={styles.schemeCard}>
                      <h4 style={styles.schemeTitle}>{scheme.name}</h4>
                      <p style={styles.schemeDesc}>{scheme.description}</p>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button 
                          onClick={() => setSelectedScheme(scheme)} 
                          className="btn-secondary" 
                          style={{ padding: '8px 16px', borderRadius: 'var(--border-radius)', transition: 'all 0.3s ease' }}
                        >
                          View Details
                        </button>
                        {scheme.official_website && (
                          <a href={scheme.official_website} target="_blank" rel="noopener noreferrer" style={styles.linkBtn}>
                            Apply Now
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
             <div className="glass-card" style={styles.placeholderCard}>
                <FileCheck size={48} color="var(--primary-color)" style={{ marginBottom: '20px' }} />
                <h3>Verification Required</h3>
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '10px' }}>
                  Please complete the document verification to view your eligible schemes.
                </p>
             </div>
          )}
        </div>
      </div>

      {selectedScheme && (
        <div style={styles.modalOverlay} onClick={() => setSelectedScheme(null)}>
          <div className="glass-card animate-fade-in" style={styles.modalContent} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div style={{display: 'flex', alignItems: 'center', gap: '15px'}}>
                <div style={{background: 'rgba(79, 70, 229, 0.2)', padding: '10px', borderRadius: '12px'}}>
                  <Info size={24} color="var(--primary-color)" />
                </div>
                <div>
                  <h3 style={{fontSize: '1.4rem', fontWeight: 700, color: '#fff', lineHeight: 1.2}}>{selectedScheme.name}</h3>
                  <span style={{fontSize: '0.85rem', color: 'var(--text-muted)'}}>Government Scheme Details</span>
                </div>
              </div>
              <button onClick={() => setSelectedScheme(null)} style={styles.closeBtn}><X size={24} color="var(--text-muted)" /></button>
            </div>

            <div style={styles.modalBody}>
              <div style={styles.infoGrid}>
                {/* Overview Section */}
                <div style={styles.infoCard}>
                  <div style={styles.cardHeader}>
                    <Info size={18} color="var(--primary-color)" />
                    <h4 style={styles.cardTitle}>Scheme Overview</h4>
                  </div>
                  <p style={styles.cardText}>{selectedScheme.description}</p>
                </div>

                {/* Beneficiaries Section */}
                <div style={styles.infoCard}>
                  <div style={styles.cardHeader}>
                    <Target size={18} color="var(--secondary-color)" />
                    <h4 style={styles.cardTitle}>Target Beneficiaries</h4>
                  </div>
                  <div style={styles.cardText}>
                    <span style={styles.highlightBadge}>{selectedScheme.target_beneficiaries || 'Not specified'}</span>
                  </div>
                </div>

                {/* Eligibility Section */}
                {selectedScheme.rules && (
                  <div style={styles.infoCard}>
                    <div style={styles.cardHeader}>
                      <ShieldCheck size={18} color="#a855f7" />
                      <h4 style={styles.cardTitle}>Eligibility Criteria</h4>
                    </div>
                    <ul style={styles.detailList}>
                      {selectedScheme.rules?.min_age && <li>Minimum Age: <strong>{selectedScheme.rules.min_age}</strong></li>}
                      {selectedScheme.rules?.max_age && <li>Maximum Age: <strong>{selectedScheme.rules.max_age}</strong></li>}
                      {selectedScheme.rules?.max_income && <li>Maximum Income: <strong>₹{selectedScheme.rules.max_income}</strong></li>}
                      <li>Supported Categories: <strong>{Array.isArray(selectedScheme.rules?.allowed_categories) ? selectedScheme.rules.allowed_categories.join(', ') : 'All'}</strong></li>
                    </ul>
                  </div>
                )}

                {/* Application Section */}
                {selectedScheme.application_process && (
                  <div style={styles.infoCard}>
                    <div style={styles.cardHeader}>
                      <ClipboardList size={18} color="#f59e0b" />
                      <h4 style={styles.cardTitle}>How to Apply</h4>
                    </div>
                    <p style={styles.cardText}>{selectedScheme.application_process}</p>
                  </div>
                )}
              </div>

              {/* Action Section */}
              {selectedScheme.official_website && (
                <div style={styles.modalFooter}>
                  <a 
                    href={selectedScheme.official_website} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    style={styles.applyBtn}
                  >
                    Go to Official Portal <ExternalLink size={18} />
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '40px 0',
  },
  header: {
    marginBottom: '40px',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: 'minmax(300px, 1fr) minmax(300px, 1.5fr)',
    gap: '40px',
  },
  formCard: {
    padding: '30px',
    height: 'fit-content',
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
    flex: 1,
  },
  row: {
    display: 'flex',
    gap: '15px',
  },
  input: {
    width: '100%',
    boxSizing: 'border-box',
    padding: '12px 15px',
    fontSize: '1rem',
    outline: 'none',
    transition: 'border-color 0.3s',
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
  resultsArea: {
    height: '100%',
  },
  placeholderCard: {
    height: '100%',
    minHeight: '400px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '40px',
  },
  resultsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  schemeList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
    maxHeight: '800px',
    overflowY: 'auto',
    paddingRight: '10px',
  },
  schemeCard: {
    padding: '20px',
    borderLeft: '4px solid var(--primary-color)',
  },
  schemeTitle: {
    fontSize: '1.25rem',
    marginBottom: '10px',
    color: 'var(--primary-color)',
  },
  schemeDesc: {
    color: 'var(--text-muted)',
    marginBottom: '15px',
    fontSize: '0.95rem',
  },
  linkBtn: {
    display: 'inline-block',
    padding: '8px 16px',
    background: 'rgba(79, 70, 229, 0.1)',
    color: 'var(--primary-color)',
    borderRadius: 'var(--border-radius)',
    fontWeight: 500,
    fontSize: '0.9rem',
    textAlign: 'center'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    zIndex: 2000,
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-start',
    padding: '40px 20px',
  },
  modalContent: {
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    padding: '0',
    borderRadius: '24px',
    width: '750px',
    maxWidth: '95vw',
    maxHeight: '90vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    border: '1px solid rgba(255,255,255,0.1)',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '25px 30px',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
    background: 'rgba(255, 255, 255, 0.02)',
  },
  modalBody: {
    padding: '30px',
    overflowY: 'auto',
    flex: 1,
    scrollbarWidth: 'thin',
    scrollbarColor: 'var(--primary-color) rgba(255,255,255,0.05)',
  },
  infoGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  infoCard: {
    background: 'rgba(255, 255, 255, 0.03)',
    padding: '20px',
    borderRadius: '16px',
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '12px',
  },
  cardTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    color: '#fff',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  cardText: {
    color: '#cbd5e1',
    lineHeight: '1.6',
    fontSize: '0.95rem',
  },
  highlightBadge: {
    display: 'inline-block',
    padding: '6px 14px',
    background: 'rgba(16, 185, 129, 0.1)',
    color: 'var(--secondary-color)',
    borderRadius: '8px',
    fontWeight: 600,
    fontSize: '0.9rem',
  },
  detailList: {
    listStyle: 'none',
    padding: 0,
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '10px',
  },
  modalFooter: {
    padding: '20px 30px',
    borderTop: '1px solid rgba(255,255,255,0.05)',
    background: 'rgba(255, 255, 255, 0.02)',
  },
  applyBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    width: '100%',
    padding: '14px',
    background: 'linear-gradient(135deg, var(--primary-color), var(--primary-hover))',
    color: '#fff',
    borderRadius: '12px',
    fontWeight: 600,
    fontSize: '1rem',
    transition: 'transform 0.2s',
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: '4px',
    display: 'flex',
  }
};

// Add responsive layout styles inline for speed
if (typeof window !== 'undefined') {
  const style = document.createElement('style');
  style.innerHTML = `
    @media (max-width: 768px) {
      .layout {
        display: flex !important;
        flex-direction: column !important;
      }
      .schemeList {
        max-height: none !important;
      }
    }
  `;
  document.head.appendChild(style);
}

export default EligibilityForm;
