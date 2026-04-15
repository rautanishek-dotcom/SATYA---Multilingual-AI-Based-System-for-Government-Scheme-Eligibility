import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Filter, AlertCircle, X, Target, ClipboardList, Info, ExternalLink, ShieldCheck, CheckCircle, Sparkles } from 'lucide-react';

const SchemeList = () => {
  const { t, i18n } = useTranslation();
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState(null);
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('All');
  const [selectedState, setSelectedState] = useState('All');
  
  const filterOptions = ['All', 'Farmer', 'Student', 'Woman', 'Senior Citizen', 'Business', 'Housing', 'Healthcare'];
  const states = [
    'All', 'All India', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 
    'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 
    'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 
    'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Andaman and Nicobar Islands', 
    'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Jammu and Kashmir', 'Ladakh', 
    'Lakshadweep', 'Puducherry'
  ];

  useEffect(() => {
    fetchSchemes();
  }, [i18n.language]);

  const fetchSchemes = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/schemes/?lang=${i18n.language}`);
      if (!response.ok) throw new Error(t('FetchError', "Failed to fetch"));
      const data = await response.json();
      setSchemes(data);
    } catch (err) {
      console.error(err);
      setError(t('ConnectionError', "Could not connect to server. Ensure backend is running."));
    } finally {
      setLoading(false);
    }
  };

  const filteredAndSortedSchemes = schemes
    .filter(s => {
      const matchesSearch = !searchTerm || 
                            s.name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
                            s.description?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesFilter = selectedFilter === 'All' || 
                            (s.target_beneficiaries?.toLowerCase().includes(selectedFilter.toLowerCase()) || 
                             s.description?.toLowerCase().includes(selectedFilter.toLowerCase()));
      
      const schemeState = (s.rules && s.rules.state && s.rules.state.length > 0) ? s.rules.state[0] : (s.state || 'All India');
      // Fix state matching to handle both English and Localized names
      const matchesState = selectedState === 'All' || 
                           (selectedState === 'All India' ? 
                             (schemeState === 'All India' || schemeState.toLowerCase() === 'all') : 
                             (schemeState.toLowerCase() === selectedState.toLowerCase() || 
                              schemeState === 'All India' || 
                              schemeState.toLowerCase() === 'all'));

      return matchesSearch && matchesFilter && matchesState;
    })
    .sort((a, b) => {
      const aState = (a.rules && a.rules.state && a.rules.state.length > 0) ? a.rules.state[0] : (a.state || 'All India');
      const bState = (b.rules && b.rules.state && b.rules.state.length > 0) ? b.rules.state[0] : (b.state || 'All India');
      
      if (selectedState !== 'All' && selectedState !== 'All India') {
        const aIsState = aState.toLowerCase() === selectedState.toLowerCase();
        const bIsState = bState.toLowerCase() === selectedState.toLowerCase();
        if (aIsState && !bIsState) return -1;
        if (!aIsState && bIsState) return 1;
      }
      return 0;
    });

  return (
    <div className="container animate-fade-in" style={styles.container}>
      <div style={styles.header}>
        <h2 style={{ fontSize: '2.5rem', marginBottom: '10px' }}>{t('GovtSchemesDirectory')}</h2>
        <p style={{ color: 'var(--text-muted)' }}>{t('BrowseAllSchemes')}</p>
      </div>

      <div style={styles.searchBar} className="glass-card">
        <Search size={20} color="var(--text-muted)" style={styles.searchIcon} />
        <input 
          type="text" 
          placeholder={t('SearchPlaceholder')} 
          style={styles.searchInput}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', borderLeft: '1px solid var(--border-color)', paddingLeft: '15px', marginLeft: '10px' }}>
          <select 
            style={{...styles.searchInput, maxWidth: '130px'}}
            value={selectedFilter}
            onChange={(e) => setSelectedFilter(e.target.value)}
          >
            {filterOptions.map(opt => (
              <option key={opt} value={opt} style={{color: '#000'}}>{t(opt.replace(' ', ''), opt)}</option>
            ))}
          </select>
          <select 
            style={{...styles.searchInput, maxWidth: '150px'}}
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
          >
            <option value="All" style={{color: '#000'}}>{t('AllStates', 'All States')}</option>
            {states.filter(s => s !== 'All').map(st => (
              <option key={st} value={st} style={{color: '#000'}}>{t(st.replace(/\s/g, ''), st)}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div style={styles.loader}>{t('LoadingSchemes')}</div>
      ) : error ? (
        <div className="glass-card" style={styles.errorCard}>
          <AlertCircle size={32} color="var(--error-color)" />
          <p>{error}</p>
        </div>
      ) : (
        <div style={styles.grid}>
          {filteredAndSortedSchemes.map((scheme, idx) => {
            const schemeSt = (scheme.rules?.state && scheme.rules.state.length > 0) ? scheme.rules.state[0] : (scheme.state || 'All India');
            const isCentral = !schemeSt || schemeSt.toLowerCase() === 'all' || schemeSt === 'All India';
            return (
              <div key={idx} className="glass-card" style={styles.card}>
                <div style={styles.cardContent}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                    <h3 style={{ ...styles.cardTitle, margin: 0 }}>{scheme.name}</h3>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '12px',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      background: isCentral ? 'rgba(79, 70, 229, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                      color: isCentral ? 'var(--primary-color)' : 'var(--secondary-color)',
                      border: `1px solid ${isCentral ? 'rgba(79, 70, 229, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`,
                      whiteSpace: 'nowrap'
                    }}>
                      {isCentral 
                        ? t('Central', 'Central') 
                        : schemeSt}
                    </span>
                  </div>
                  <p style={styles.cardDesc}>{scheme.description?.substring(0, 100)}...</p>
                  <div style={styles.badgeGroup}>
                    <span style={styles.badge}>{scheme.target_beneficiaries}</span>
                  </div>
                </div>
                <div style={styles.cardFooter}>
                  <button 
                    className="btn-secondary" 
                    style={{ ...styles.cardBtn, transition: 'all 0.3s ease' }} 
                    onClick={() => setSelectedScheme(scheme)}
                  >
                    {t('ViewDetails')}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

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
                  <span style={{fontSize: '0.85rem', color: 'var(--text-muted)'}}>{t('SchemeDetailsSubtitle', 'Government Scheme Details')}</span>
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
                      <h4 style={styles.infoCardTitle}>{t('SchemeOverview')}</h4>
                    </div>
                    <p style={styles.cardText}>{selectedScheme.description}</p>
                  </div>

                  {/* Benefits Section (New) */}
                  <div style={styles.infoCard}>
                    <div style={styles.cardHeader}>
                      <div style={{...styles.iconWrapperIcon, background: 'rgba(52, 211, 153, 0.1)'}}>
                        <Sparkles size={20} color="#34d399" />
                      </div>
                      <h4 style={styles.infoCardTitle}>{t('KeyBenefits', 'Main Benefits')}</h4>
                    </div>
                    <p style={styles.cardText}>
                      {selectedScheme.benefits || t('BenefitsDefault', 'Provides financial assistance, social security, and direct support to eligible citizens as per government norms.')}
                    </p>
                  </div>

                  {/* Beneficiaries Section */}
                  <div style={styles.infoCard}>
                    <div style={styles.cardHeader}>
                      <Target size={18} color="var(--secondary-color)" />
                      <h4 style={styles.infoCardTitle}>{t('TargetBeneficiaries')}</h4>
                    </div>
                    <div style={styles.cardText}>
                      <span style={styles.highlightBadge}>{selectedScheme.target_beneficiaries || t('NotSpecified', 'Not specified')}</span>
                    </div>
                  </div>

                  {/* Eligibility Section */}
                  {selectedScheme.rules && (
                    <div style={styles.infoCard}>
                      <div style={styles.cardHeader}>
                        <div style={{...styles.iconWrapperIcon, background: 'rgba(168, 85, 247, 0.1)'}}>
                          <ShieldCheck size={20} color="#a855f7" />
                        </div>
                        <h4 style={styles.infoCardTitle}>{t('EligibilityCriteria')}</h4>
                      </div>
                      <div style={styles.rulesGrid}>
                        <div style={styles.ruleItem}>
                          <span style={styles.ruleLabel}>{t('AgeLimit', 'Age Limit')}:</span>
                          <span style={styles.ruleValue}>{selectedScheme.rules.min_age} - {selectedScheme.rules.max_age} {t('Years', 'Years')}</span>
                        </div>
                        <div style={styles.ruleItem}>
                          <span style={styles.ruleLabel}>{t('IncomeLimit', 'Income Limit')}:</span>
                          <span style={styles.ruleValue}>₹{selectedScheme.rules.max_income || t('NoLimit', 'No Limit')}</span>
                        </div>
                        <div style={styles.ruleItem}>
                          <span style={styles.ruleLabel}>{t('StateRestrictions', 'Location')}:</span>
                          <span style={styles.ruleValue}>{(() => { const st = (selectedScheme.rules?.state && selectedScheme.rules.state.length > 0) ? selectedScheme.rules.state[0] : (selectedScheme.state || 'All India'); return (!st || st.toLowerCase() === 'all' || st === 'All India') ? t('Central', 'Central') : st; })()}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Application Section */}
                  <div style={styles.infoCard}>
                    <div style={styles.cardHeader}>
                      <div style={{...styles.iconWrapperIcon, background: 'rgba(245, 158, 11, 0.1)'}}>
                        <ClipboardList size={20} color="#f59e0b" />
                      </div>
                      <h4 style={styles.infoCardTitle}>{t('HowToApply')}</h4>
                    </div>
                    <div style={styles.cardText}>
                      {selectedScheme.steps ? (
                        <div style={styles.stepsList}>
                          {selectedScheme.steps.split(/(?:\n|\b\d+\.\s*)/).filter(s => s.trim() && !/^[\d\.]+$/.test(s.trim())).map((step, idx) => (
                            <div key={idx} style={styles.stepItem}>
                              <div style={styles.stepNumber}>{idx + 1}</div>
                              <p>{step.trim()}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p>{selectedScheme.application_process || t('StepsDefault')}</p>
                      )}
                    </div>
                  </div>
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
                    {t('GoToPortal')} <ExternalLink size={18} />
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
    textAlign: 'center',
    marginBottom: '40px',
  },
  searchBar: {
    display: 'flex',
    alignItems: 'center',
    padding: '10px 20px',
    marginBottom: '40px',
    maxWidth: '800px',
    margin: '0 auto 40px auto',
  },
  searchIcon: {
    marginRight: '15px',
  },
  searchInput: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    fontSize: '1rem',
    color: 'var(--text-dark)',
  },
  filterBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 15px',
    border: 'none',
    background: 'rgba(255, 255, 255, 0.05)',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '25px',
  },
  card: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  cardContent: {
    padding: '25px',
    flex: 1,
  },
  cardTitle: {
    fontSize: '1.2rem',
    marginBottom: '10px',
    color: 'var(--primary-color)',
    fontWeight: 700,
  },
  cardDesc: {
    color: 'var(--text-muted)',
    fontSize: '0.95rem',
    marginBottom: '20px',
  },
  badgeGroup: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '10px',
  },
  badge: {
    fontSize: '0.8rem',
    padding: '4px 10px',
    background: 'rgba(16, 185, 129, 0.1)',
    color: 'var(--secondary-color)',
    borderRadius: '100px',
    fontWeight: 500,
  },
  cardFooter: {
    padding: '15px 25px',
    borderTop: '1px solid var(--border-color)',
  },
  cardBtn: {
    width: '100%',
    padding: '10px',
    textAlign: 'center',
  },
  loader: {
    textAlign: 'center',
    fontSize: '1.2rem',
    color: 'var(--text-muted)',
    padding: '40px',
  },
  errorCard: {
    padding: '40px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '15px',
    border: '1px solid var(--error-color)',
    maxWidth: '500px',
    margin: '0 auto',
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
    gap: '12px',
    marginBottom: '15px',
  },
  iconWrapperIcon: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  infoCardTitle: {
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
  rulesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '15px',
    marginTop: '5px',
  },
  ruleItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    padding: '10px',
    background: 'rgba(255,255,255,0.02)',
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.03)',
  },
  ruleLabel: {
    fontSize: '0.75rem',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    letterSpacing: '0.05em',
  },
  ruleValue: {
    fontSize: '1rem',
    fontWeight: 600,
    color: '#fff',
  },
  stepsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginTop: '10px',
  },
  stepItem: {
    display: 'flex',
    gap: '15px',
    alignItems: 'flex-start',
  },
  stepNumber: {
    minWidth: '24px',
    height: '24px',
    borderRadius: '50%',
    background: 'var(--primary-color)',
    color: 'white',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    fontSize: '0.8rem',
    fontWeight: 700,
    marginTop: '2px',
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

export default SchemeList;
