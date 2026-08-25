import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Search, AlertCircle, X, Target, ClipboardList, Info,
  ExternalLink, ShieldCheck, CheckCircle, Sparkles, SlidersHorizontal,
  MapPin, Briefcase, Users, FileText, Activity, Clock, ChevronRight, Calendar
} from 'lucide-react';

// ─────────────────────────────────────────
// SchemeList (main page)
// ─────────────────────────────────────────
const SchemeList = () => {
  const { t, i18n } = useTranslation();
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState(null);
  const [selectedScheme, setSelectedScheme] = useState(null);

  const [filters, setFilters] = useState({
    state: 'All', category: 'All', occupation: 'All', type: 'All'
  });

  const stateOptions = [
    'All', 'All India', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar',
    'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand',
    'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya',
    'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
    'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi'
  ];
  const categoryOptions  = ['All', 'General', 'OBC', 'SC', 'ST'];
  const occupationOptions = ['All', 'Farmer', 'Student', 'Worker', 'Business', 'Service', 'Retired'];
  const typeOptions       = ['All', 'Agriculture', 'Health', 'Education', 'Housing', 'Business', 'Social Welfare', 'Pension'];

  const fetchSchemes = useCallback(async () => {
    try {
      const res = await fetch(`http://localhost:5000/api/schemes/?lang=${i18n.language}`);
      if (!res.ok) throw new Error(t('FetchError', 'Failed to fetch schemes'));
      setSchemes(await res.json());
    } catch (_err) {
      console.error(_err);
      setError(t('ConnectionError', 'Could not connect to server. Ensure backend is running.'));
    } finally {
      setLoading(false);
    }
  }, [i18n.language, t]);

  useEffect(() => { fetchSchemes(); }, [fetchSchemes]);

  const handleFilterChange = (name, value) =>
    setFilters(prev => ({ ...prev, [name]: value }));

  const filteredSchemes = schemes.filter(s => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = !searchTerm ||
      s.name?.toLowerCase().includes(term) ||
      s.description?.toLowerCase().includes(term);

    const schemeState = s.state || 'All India';
    const matchesState = filters.state === 'All' ||
      (filters.state === 'All India'
        ? schemeState === 'All India'
        : schemeState.toLowerCase() === filters.state.toLowerCase() || schemeState === 'All India');

    const allowedCats = s.rules?.allowed_categories || ['all'];
    const matchesCategory = filters.category === 'All' ||
      allowedCats.includes('all') || allowedCats.includes(filters.category.toLowerCase());

    const allowedOccs = s.rules?.occupation || ['all'];
    const matchesOccupation = filters.occupation === 'All' ||
      allowedOccs.includes('all') || allowedOccs.includes(filters.occupation.toLowerCase());

    const matchesType = filters.type === 'All' ||
      s.target_beneficiaries?.toLowerCase().includes(filters.type.toLowerCase()) ||
      s.description?.toLowerCase().includes(filters.type.toLowerCase());

    return matchesSearch && matchesState && matchesCategory && matchesOccupation && matchesType;
  });

  return (
    <>
      <div className="container animate-fade-in" style={styles.container}>
        <div style={styles.header}>
          <h2 style={{ fontSize: '2.8rem', fontWeight: 800, marginBottom: '10px' }}>
            <span className="gradient-text">{t('GovtSchemesDirectory', 'Schemes Directory')}</span>
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>
            {t('BrowseAllSchemes', 'Explore and search through a comprehensive list of all government initiatives.')}
          </p>
        </div>

        {/* Filter Bar */}
        <div style={styles.filterBar} className="glass-card">
          <div style={styles.searchSection}>
            <Search size={20} color="var(--text-muted)" style={styles.searchIcon} />
            <input
              type="text"
              placeholder={t('SearchSchemesPlaceholder', 'Search by name or keyword...')}
              style={styles.searchInput}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
          <div style={styles.controlsSection}>
            <div style={styles.filterGroup}>
              <MapPin size={16} />
              <select value={filters.state} onChange={e => handleFilterChange('state', e.target.value)} style={styles.select}>
                {stateOptions.map(o => <option key={o} value={o}>{t(o.replace(/\s/g, ''), o)}</option>)}
              </select>
            </div>
            <div style={styles.filterGroup}>
              <Users size={16} />
              <select value={filters.category} onChange={e => handleFilterChange('category', e.target.value)} style={styles.select}>
                {categoryOptions.map(o => <option key={o} value={o}>{t(o, o)}</option>)}
              </select>
            </div>
            <div style={styles.filterGroup}>
              <Briefcase size={16} />
              <select value={filters.occupation} onChange={e => handleFilterChange('occupation', e.target.value)} style={styles.select}>
                {occupationOptions.map(o => <option key={o} value={o}>{t(o, o)}</option>)}
              </select>
            </div>
            <div style={styles.filterGroup}>
              <SlidersHorizontal size={16} />
              <select value={filters.type} onChange={e => handleFilterChange('type', e.target.value)} style={styles.select}>
                {typeOptions.map(o => <option key={o} value={o}>{t(o.replace(/\s/g, ''), o)}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Results Header */}
        <div style={styles.resultsHeader}>
          <p style={{ fontWeight: 600, color: 'var(--text-dark)' }}>
            {t('Showing')} {filteredSchemes.length} {t('Schemes')}
          </p>
          {(searchTerm || filters.state !== 'All' || filters.category !== 'All' || filters.occupation !== 'All' || filters.type !== 'All') && (
            <button style={styles.clearBtn} onClick={() => { setFilters({ state: 'All', category: 'All', occupation: 'All', type: 'All' }); setSearchTerm(''); }}>
              {t('ClearAll')} <X size={14} />
            </button>
          )}
        </div>

        {loading ? (
          <div style={styles.loaderArea}>
            <div style={styles.spinner}></div>
            <p>{t('LoadingSchemes')}</p>
          </div>
        ) : error ? (
          <div className="glass-card" style={styles.errorCard}>
            <AlertCircle size={40} color="var(--error-color)" />
            <p style={{ fontSize: '1.2rem', fontWeight: 600 }}>{error}</p>
            <button className="btn-primary" onClick={fetchSchemes}>{t('TryAgain')}</button>
          </div>
        ) : (
          <div style={styles.grid}>
            {filteredSchemes.length === 0 ? (
              <div style={styles.noResults}>
                <Search size={60} style={{ opacity: 0.1, marginBottom: '20px' }} />
                <h3>{t('NoResultsTitle')}</h3>
                <p>{t('NoResultsDesc')}</p>
              </div>
            ) : (
              filteredSchemes.map((scheme, idx) => (
                <SchemeCard key={idx} scheme={scheme} t={t} onSelect={setSelectedScheme} />
              ))
            )}
          </div>
        )}
      </div>

      {selectedScheme && (
        <SchemeDetailModal
          scheme={selectedScheme}
          onClose={() => setSelectedScheme(null)}
          t={t}
        />
      )}
    </>
  );
};

// ─────────────────────────────────────────
// SchemeCard
// ─────────────────────────────────────────
const SchemeCard = ({ scheme, t, onSelect }) => {
  const isCentral = scheme.state === 'All India';
  const isPartial = scheme.status === 'Partially Eligible';

  return (
    <div className="glass-card" style={{ ...styles.card, borderTop: isPartial ? '4px solid #f59e0b' : 'none' }}>
      <div style={styles.cardContent}>
        <div style={styles.cardTop}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span style={{
              ...styles.cardTag,
              background: isCentral ? 'rgba(79,70,229,0.1)' : 'rgba(16,185,129,0.1)',
              color: isCentral ? 'var(--primary-color)' : 'var(--secondary-color)',
            }}>
                {isCentral ? t('Central') : t(scheme.state.replace(/\s/g, ''), scheme.state)}
            </span>
            {scheme.match_score !== undefined && (
              <span style={{
                ...styles.cardTag,
                background: scheme.match_score === 100 ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                color: scheme.match_score === 100 ? '#059669' : '#d97706',
                display: 'flex', alignItems: 'center', gap: '4px'
              }}>
                <CheckCircle size={12} /> {scheme.match_score}% {t('Match')}
              </span>
            )}
          </div>
          {isPartial && <AlertCircle size={16} color="#f59e0b" title={t('PartiallyEligible')} />}
        </div>
        <h3 style={styles.cardTitle}>{scheme.name}</h3>
        <p style={styles.cardDesc}>{scheme.description?.substring(0, 110)}...</p>
        {isPartial && scheme.reasons?.length > 0 && (
          <div style={styles.partialReason}>
            <Info size={12} />
            <span>{t('PartialMatchNote', 'Matches most criteria')}</span>
          </div>
        )}
        <div style={styles.beneficiaries}>
          <Target size={14} />
          <span>{scheme.target_beneficiaries?.substring(0, 40)}</span>
        </div>
      </div>
      <div style={styles.cardFooter}>
        <button type="button" className="btn-secondary" style={styles.vBtn} onClick={() => onSelect(scheme)}>
          {t('ViewDetails')}
        </button>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────
// Utility helpers
// ─────────────────────────────────────────
const formatUrl = (url) => {
  if (!url || url === 'NA') return '#';
  return url.startsWith('http') ? url : `https://${url}`;
};

const formatSteps = (steps) => {
  if (!steps) return [];
  if (Array.isArray(steps)) return steps;
  if (typeof steps === 'string')
    return steps.split(/(?:\n|\b\d+\s*[.)])/).filter(s => s.trim() && !/^\d+$/.test(s.trim()));
  return [];
};

/** Formats an ISO date string → "Month YYYY", or returns the fallback "March 2026" */
const formatLastUpdated = (dateStr) => {
  if (!dateStr) return 'March 2026';
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
  } catch {
    return 'March 2026';
  }
};

// ─────────────────────────────────────────
// Sub-components for the Detail Modal
// ─────────────────────────────────────────

/** Highlights ₹ amounts and % values in bold primary colour */
const HighlightText = ({ text }) => {
  if (!text) return null;
  const parts = text.split(/(₹[\d,]+(?:\s*(?:lakhs?|crores?)?)?|\d+(?:\.\d+)?%)/gi);
  return (
    <span>
      {parts.map((part, i) =>
        /^(₹|\d+(\.\d+)?%)/.test(part)
          ? <strong key={i} style={{ color: 'var(--primary-color)', fontWeight: 800 }}>{part}</strong>
          : <span key={i}>{part}</span>
      )}
    </span>
  );
};

/** Renders any string or array as a clean chevron-bullet list */
const BulletList = ({ text, highlightValues }) => {
  if (!text)
    return <p style={{ color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>—</p>;

  const raw = typeof text === 'string'
    ? text.split(/(?:\.\s+|\n)/).filter(s => s.trim().length > 3)
    : Array.isArray(text) ? text : [String(text)];

  return (
    <ul style={{ margin: 0, paddingLeft: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '9px' }}>
      {raw.map((item, i) => (
        <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '9px', color: 'var(--text-muted)', lineHeight: 1.65 }}>
          <span style={{ marginTop: '4px', flexShrink: 0, color: 'var(--primary-color)' }}>
            <ChevronRight size={14} />
          </span>
          {highlightValues
            ? <HighlightText text={item.trim() + (item.trim().endsWith('.') ? '' : '.')} />
            : <span>{item.trim()}{item.trim().endsWith('.') ? '' : '.'}</span>}
        </li>
      ))}
    </ul>
  );
};

/** Reusable card with a coloured header bar for each section */
const SectionCard = ({ icon, title, iconColor, accentBg, children, fullWidth }) => (
  <div style={{
    background: 'white',
    border: '1px solid #e2e8f0',
    borderRadius: '16px',
    overflow: 'hidden',
    gridColumn: fullWidth ? '1 / -1' : undefined,
    boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
  }}>
    <div style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      padding: '13px 18px',
      background: accentBg || 'rgba(79,70,229,0.05)',
      borderBottom: '1px solid #e2e8f0',
    }}>
      <span style={{ color: iconColor || 'var(--primary-color)', display: 'flex' }}>{icon}</span>
      <h4 style={{ margin: 0, fontSize: '0.92rem', fontWeight: 700, color: '#1e293b' }}>{title}</h4>
    </div>
    <div style={{ padding: '16px 18px' }}>{children}</div>
  </div>
);

/** Coloured pill badge */
const TagBadge = ({ label, bg, color }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center', gap: '5px',
    background: bg, color,
    padding: '6px 14px', borderRadius: '30px',
    fontSize: '0.8rem', fontWeight: 700,
  }}>{label}</span>
);

/** Numbered step row with gradient circle */
const StepItem = ({ number, text }) => (
  <div style={{
    display: 'flex', gap: '13px', alignItems: 'flex-start',
    padding: '11px 15px', borderRadius: '12px',
    background: number % 2 === 0 ? '#f8fafc' : 'white',
    border: '1px solid #e2e8f0',
  }}>
    <div style={{
      minWidth: '30px', height: '30px', borderRadius: '50%',
      background: 'linear-gradient(135deg, var(--primary-color), #7c3aed)',
      color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 800, fontSize: '0.82rem', flexShrink: 0,
      boxShadow: '0 3px 8px rgba(79,70,229,0.3)',
    }}>{number}</div>
    <span style={{ paddingTop: '5px', color: '#334155', fontSize: '0.92rem', lineHeight: 1.55 }}>{text}</span>
  </div>
);

/** Infer scheme type from description keywords */
const getSchemeType = (description = '', t) => {
  const d = description.toLowerCase();
  if (d.includes('hous') || d.includes('awas'))           return t('Housing', 'Housing');
  if (d.includes('health') || d.includes('medical') || d.includes('swasth')) return t('Healthcare', 'Health');
  if (d.includes('edu')   || d.includes('scholar') || d.includes('vidya'))   return t('Education');
  if (d.includes('agri')  || d.includes('farm')   || d.includes('kisan'))    return t('Agriculture');
  if (d.includes('business') || d.includes('mudra') || d.includes('msme'))   return t('Business');
  if (d.includes('pension') || d.includes('vriddha'))     return t('Pension');
  return t('SocialWelfare');
};

// ─────────────────────────────────────────
// SchemeDetailModal  — full government-portal UI
// ─────────────────────────────────────────
const SchemeDetailModal = ({ scheme, onClose, t }) => {
  const schemeType = getSchemeType(scheme.description, t);
  const steps      = formatSteps(scheme.steps);

  /** Default 7-step process shown when scheme has no steps data */
  const defaultSteps = [
    t('Step1', 'Visit the official government portal or nearest Common Service Centre (CSC).'),
    t('Step2', 'Search and select this scheme from the scheme list.'),
    t('Step3', 'Enter your Aadhaar number and verify identity via OTP.'),
    t('Step4', 'Fill the application form with accurate personal and family details.'),
    t('Step5', 'Upload required documents (Aadhaar, Income Certificate, Address Proof, etc.).'),
    t('Step6', 'Submit the form and note your Application Reference Number.'),
    t('Step7', 'Track application status using Reference Number or Aadhaar on the official portal.'),
  ];
  const finalSteps = steps.length > 0 ? steps : defaultSteps;

  return (
    <div style={modal.overlay} onClick={onClose}>
      <div className="animate-fade-in" style={modal.content} onClick={e => e.stopPropagation()}>

        {/* ══ HEADER ══ */}
        <div style={modal.header}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
              <div style={{ flex: 1, minWidth: 0 }}>

                {/* Status / type badges */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
                  <span style={{ ...modal.statusBadge, background: 'rgba(16,185,129,0.12)', color: '#059669' }}>
                    <Activity size={11} style={{ display: 'inline', marginRight: '3px' }} />
                    {t('ActiveOngoing', 'Active / Ongoing')}
                  </span>
                  <span style={{ ...modal.statusBadge, background: 'rgba(79,70,229,0.1)', color: 'var(--primary-color)' }}>
                    🏛 {schemeType}
                  </span>
                  <span style={{ ...modal.statusBadge, background: 'rgba(245,158,11,0.1)', color: '#b45309' }}>
                    <MapPin size={11} style={{ display: 'inline', marginRight: '3px' }} />
                    {scheme.state === 'All India' ? t('CentralScheme') : t(scheme.state.replace(/\s/g, ''), scheme.state)}
                  </span>
                  <span style={{ ...modal.statusBadge, background: 'rgba(100,116,139,0.08)', color: '#475569', border: '1px solid rgba(100,116,139,0.18)' }}>
                    <Calendar size={11} style={{ display: 'inline', marginRight: '3px' }} />
                    {t('LastUpdated', 'Last Updated')}: {formatLastUpdated(scheme.last_updated)}
                  </span>
                </div>

                {/* Scheme name */}
                <h2 style={{ fontSize: '1.45rem', fontWeight: 900, color: '#0f172a', lineHeight: 1.25, margin: 0 }}>
                  {scheme.name}
                </h2>

                {/* Short tagline */}
                <p style={{ margin: '8px 0 0', fontSize: '0.92rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>
                  {scheme.description?.substring(0, 130)}...
                </p>
              </div>

              <button onClick={onClose} style={modal.closeBtn} aria-label="Close">
                <X size={20} />
              </button>
            </div>
          </div>
        </div>

        {/* ══ BODY ══ */}
        <div style={modal.body}>
          <div style={modal.grid}>

            {/* 1 · SCHEME OVERVIEW — full width */}
            <SectionCard fullWidth
              icon={<Info size={17} />}
              iconColor="var(--primary-color)"
              accentBg="rgba(79,70,229,0.05)"
              title={t('SchemeOverview', 'Scheme Overview')}
            >
              <p style={{ color: '#334155', lineHeight: 1.85, fontSize: '0.95rem', margin: 0 }}>
                {scheme.description || t('NoDescription')}
              </p>
              {scheme.target_beneficiaries && (
                <div style={{ marginTop: '12px', padding: '10px 14px', background: '#f0fdf4', borderRadius: '10px', border: '1px solid #bbf7d0' }}>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: '#166534', fontWeight: 600 }}>
                    🎯 {t('TargetBeneficiaries', 'Target Beneficiaries')}:{' '}
                    <span style={{ fontWeight: 400 }}>{scheme.target_beneficiaries?.substring(0, 220)}</span>
                  </p>
                </div>
              )}
            </SectionCard>

            {/* 2 · KEY BENEFITS */}
            <SectionCard
              icon={<Sparkles size={17} />}
              iconColor="#10b981"
              accentBg="rgba(16,185,129,0.05)"
              title={t('KeyBenefits', 'Key Benefits')}
            >
              <BulletList
                text={scheme.benefits || t('BenefitsDefault')}
                highlightValues={true}
              />
            </SectionCard>

            {/* 3 · ELIGIBILITY CRITERIA */}
            <SectionCard
              icon={<ShieldCheck size={17} />}
              iconColor="#a855f7"
              accentBg="rgba(168,85,247,0.05)"
              title={t('EligibilityCriteria', 'Eligibility Criteria')}
            >
              <BulletList text={scheme.target_beneficiaries} highlightValues={true} />

              {/* Rule chips — income / age / category */}
              {scheme.rules && (
                <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '7px' }}>
                  {scheme.rules.min_age && (
                    <span style={modal.chip}>🎂 {t('MinAge', 'Min Age')}: <strong>{scheme.rules.min_age}</strong></span>
                  )}
                  {scheme.rules.max_age && (
                    <span style={modal.chip}>🎂 {t('MaxAge', 'Max Age')}: <strong>{scheme.rules.max_age}</strong></span>
                  )}
                  {scheme.rules.max_income && (
                    <span style={modal.chip}>
                      💰 {t('MaxIncome', 'Max Income')}: <strong>₹{Number(scheme.rules.max_income).toLocaleString('en-IN')}</strong>
                    </span>
                  )}
                  {scheme.rules.allowed_categories && !scheme.rules.allowed_categories.includes('all') && (
                    <span style={modal.chip}>
                      👥 {t('Category', 'Category')}: <strong>{scheme.rules.allowed_categories.join(', ').toUpperCase()}</strong>
                    </span>
                  )}
                </div>
              )}
            </SectionCard>

            {/* 4 · REQUIRED DOCUMENTS */}
            <SectionCard
              icon={<FileText size={17} />}
              iconColor="#3b82f6"
              accentBg="rgba(59,130,246,0.05)"
              title={t('RequiredDocuments', 'Required Documents')}
            >
              {[
                { icon: '🆔', text: t('AadhaarCard', 'Aadhaar Card'),                           required: true  },
                { icon: '📄', text: t('IncomeCertificate', 'Income Certificate'),               required: false },
                { icon: '📍', text: t('AddressProof', 'Address / Domicile Proof'),              required: true  },
                { icon: '🏦', text: t('BankDetails', 'Bank Account Details (Linked to Aadhaar)'), required: true },
                { icon: '📋', text: t('SchemeSpecificDocs', 'Scheme-specific certificates (if any)'), required: false },
              ].map((doc, i, arr) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 0',
                  borderBottom: i < arr.length - 1 ? '1px solid #f1f5f9' : 'none',
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#334155', fontSize: '0.88rem' }}>
                    {doc.icon} {doc.text}
                  </span>
                  <span style={{
                    fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: '20px', flexShrink: 0, marginLeft: '8px',
                    background: doc.required ? 'rgba(239,68,68,0.08)' : 'rgba(100,116,139,0.1)',
                    color: doc.required ? '#dc2626' : '#64748b',
                  }}>
                    {doc.required ? t('Mandatory', 'REQUIRED') : t('Optional', 'OPTIONAL')}
                  </span>
                </div>
              ))}
            </SectionCard>

            {/* 5 · PRIORITY GROUPS — full width */}
            <SectionCard fullWidth
              icon={<Users size={17} />}
              iconColor="#ec4899"
              accentBg="rgba(236,72,153,0.05)"
              title={t('PriorityGroups', 'Priority Groups')}
            >
              <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '12px', marginTop: 0 }}>
                {t('PriorityDesc', 'Reserved quotas and special consideration are typically extended to the following groups:')}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                <TagBadge label={`👩 ${t('Women', 'Women')}`}                            bg="#fce7f3" color="#be185d" />
                <TagBadge label={`🏅 ${t('SCST', 'SC / ST')}`}                           bg="#ede9fe" color="#6d28d9" />
                <TagBadge label={`👴 ${t('SeniorCitizen', 'Senior Citizens')}`}          bg="#ffedd5" color="#c2410c" />
                <TagBadge label={`♿ ${t('DisabledPersons', 'Persons with Disabilities')}`} bg="#e0f2fe" color="#0369a1" />
                <TagBadge label={`🏠 ${t('BPLHouseholds', 'BPL Households')}`}           bg="#f0fdf4" color="#166534" />
              </div>
            </SectionCard>

            {/* 6 · APPLICATION PROCESS — full width */}
            <SectionCard fullWidth
              icon={<ClipboardList size={17} />}
              iconColor="#f59e0b"
              accentBg="rgba(245,158,11,0.05)"
              title={t('ApplicationProcess', 'Application Process')}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
                {finalSteps.map((step, i) => (
                  <StepItem key={i} number={i + 1} text={typeof step === 'string' ? step.trim() : String(step)} />
                ))}
              </div>
            </SectionCard>

            {/* 7 · APPLICATION TRACKING */}
            <SectionCard
              icon={<Clock size={17} />}
              iconColor="#6366f1"
              accentBg="rgba(99,102,241,0.05)"
              title={t('ApplicationTracking', 'Application Tracking')}
            >
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.7, margin: '0 0 12px' }}>
                {t('TrackingDesc', 'Track your application status using your Application Reference Number or Aadhaar number on the official portal or Umang App.')}
              </p>
              <div style={{ display: 'flex', gap: '7px', flexWrap: 'wrap' }}>
                <span style={modal.chip}>🖥️ {t('OnlinePortal', 'Online Portal')}</span>
                <span style={modal.chip}>📱 {t('UmangApp', 'Umang App')}</span>
                <span style={modal.chip}>🏢 {t('CSC', 'CSC Centre')}</span>
              </div>
            </SectionCard>

            {/* 8 · AVAILABILITY */}
            <SectionCard
              icon={<MapPin size={17} />}
              iconColor="#0891b2"
              accentBg="rgba(8,145,178,0.05)"
              title={t('Availability', 'Availability')}
            >
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.7, margin: '0 0 12px' }}>
                {t('AvailabilityDesc', 'This scheme is applicable to eligible citizens in both Urban and Rural areas across India.')}
              </p>
              <div style={{ display: 'flex', gap: '7px', flexWrap: 'wrap' }}>
                <span style={{ ...modal.chip, background: 'rgba(16,185,129,0.1)', color: '#065f46' }}>🏙️ {t('Urban', 'Urban')}</span>
                <span style={{ ...modal.chip, background: 'rgba(245,158,11,0.1)', color: '#78350f' }}>🌾 {t('Rural', 'Rural')}</span>
                <span style={{ ...modal.chip, background: 'rgba(79,70,229,0.1)', color: '#3730a3' }}>
                  {scheme.state === 'All India' ? `🇮🇳 ${t('AllIndia', 'All India')}` : `📍 ${scheme.state}`}
                </span>
              </div>
            </SectionCard>

          </div>{/* end sectionsGrid */}

          {/* ── IMPORTANT NOTES ── */}
          <div style={modal.notesBox}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '9px' }}>
              <AlertCircle size={16} color="#dc2626" />
              <h5 style={{ margin: 0, color: '#dc2626', fontWeight: 700, fontSize: '0.92rem' }}>
                {t('ImportantNotes', 'Important Notes')}
              </h5>
            </div>
            <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <li style={{ color: '#7f1d1d', fontSize: '0.86rem', lineHeight: 1.6 }}>
                {t('Note1', 'Final approval is subject to verification of all submitted documents by relevant authorities.')}
              </li>
              <li style={{ color: '#7f1d1d', fontSize: '0.86rem', lineHeight: 1.6 }}>
                {t('Note2', 'All documents must be valid, clear, and up-to-date at the time of submission.')}
              </li>
              <li style={{ color: '#7f1d1d', fontSize: '0.86rem', lineHeight: 1.6 }}>
                {t('Note3', 'Scheme rules, eligibility criteria, and benefit amounts are subject to revision by the Government of India.')}
              </li>
            </ul>
          </div>
        </div>{/* end body */}

        {/* ══ FOOTER / APPLY NOW ══ */}
        <div style={modal.footer}>
          <div>
            <p style={{ margin: 0, fontWeight: 700, fontSize: '0.92rem', color: '#0f172a' }}>
              {t('ReadyToApply', 'Ready to apply?')}
            </p>
            <p style={{ margin: '2px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {t('VisitOfficialPortal', 'Visit the official government portal to start your application.')}
            </p>
          </div>
          {scheme.official_website && scheme.official_website !== 'NA' ? (
            <a
              href={formatUrl(scheme.official_website)}
              target="_blank"
              rel="noopener noreferrer"
              style={modal.applyBtn}
            >
              {t('ApplyNow', 'Apply Now')} <ExternalLink size={15} />
            </a>
          ) : (
            <button disabled style={{ ...modal.applyBtn, background: '#e2e8f0', color: '#94a3b8', cursor: 'not-allowed', boxShadow: 'none' }}>
              {t('PortalNA')}
            </button>
          )}
        </div>

      </div>{/* end modal.content */}
    </div>
  );
};

// ─────────────────────────────────────────
// Styles
// ─────────────────────────────────────────

/** Styles for SchemeList page elements */
const styles = {
  container:     { padding: '40px 0' },
  header:        { textAlign: 'center', marginBottom: '40px' },
  filterBar:     { maxWidth: '1000px', margin: '0 auto 20px auto', padding: '10px 10px 10px 25px', display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap', background: 'white' },
  searchSection: { display: 'flex', alignItems: 'center', gap: '15px', flex: 1, minWidth: '300px' },
  searchIcon:    { flexShrink: 0 },
  searchInput:   { border: 'none', background: 'transparent', outline: 'none', fontSize: '1rem', width: '100%', padding: '10px 0' },
  controlsSection: { display: 'flex', gap: '10px', flexWrap: 'wrap', borderLeft: '1px solid #f1f5f9', paddingLeft: '20px' },
  filterGroup:   { display: 'flex', alignItems: 'center', gap: '8px', padding: '0 10px', background: '#f8fafc', borderRadius: '10px', color: 'var(--text-muted)' },
  select:        { border: 'none', background: 'transparent', padding: '8px 5px', fontSize: '0.85rem', fontWeight: 600, outline: 'none', color: 'var(--text-dark)', minWidth: '80px' },
  resultsHeader: { maxWidth: '1000px', margin: '0 auto 30px auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 10px' },
  clearBtn:      { background: 'transparent', border: 'none', color: 'var(--primary-color)', fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer' },
  grid:          { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '25px' },
  card:          { display: 'flex', flexDirection: 'column', height: '100%', background: 'white' },
  cardContent:   { padding: '30px', flex: 1 },
  cardTop:       { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' },
  cardTag:       { padding: '4px 12px', borderRadius: '20px', fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase' },
  cardTitle:     { fontSize: '1.25rem', fontWeight: 700, marginBottom: '15px', color: 'var(--primary-color)', lineHeight: 1.3 },
  cardDesc:      { color: 'var(--text-muted)', fontSize: '0.95rem', marginBottom: '20px', lineHeight: 1.6 },
  beneficiaries: { display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981', fontSize: '0.8rem', fontWeight: 600 },
  partialReason: { display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(245,158,11,0.05)', color: '#d97706', padding: '8px 12px', borderRadius: '8px', fontSize: '0.8rem', marginBottom: '15px' },
  cardFooter:    { padding: '20px 30px', borderTop: '1px solid #f1f5f9' },
  vBtn:          { width: '100%', padding: '12px', textAlign: 'center', fontWeight: 700 },
  loaderArea:    { padding: '100px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' },
  spinner:       { width: '40px', height: '40px', border: '4px solid #f1f5f9', borderTop: '4px solid var(--primary-color)', borderRadius: '50%', animation: 'spin 1s linear infinite' },
  errorCard:     { padding: '60px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', maxWidth: '500px', margin: '0 auto' },
  noResults:     { gridColumn: '1 / -1', padding: '100px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' },
};

/** Styles specifically for the SchemeDetailModal */
const modal = {
  overlay: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(2,8,24,0.78)', backdropFilter: 'blur(14px)',
    zIndex: 10000, display: 'flex', justifyContent: 'center', alignItems: 'center',
    padding: '16px', overflowY: 'auto',
  },
  content: {
    background: '#f8fafc', width: '100%', maxWidth: '940px',
    maxHeight: '95vh', overflow: 'hidden',
    display: 'flex', flexDirection: 'column',
    borderRadius: '24px',
    boxShadow: '0 30px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.08)',
  },
  header: {
    padding: '22px 26px 18px',
    borderBottom: '1px solid #e2e8f0',
    background: 'linear-gradient(135deg, #ffffff 0%, #eef2ff 100%)',
    flexShrink: 0,
  },
  body: {
    padding: '20px 24px',
    overflowY: 'auto', flex: 1,
    background: '#f8fafc',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '14px',
    marginBottom: '14px',
  },
  footer: {
    padding: '16px 24px',
    background: 'white',
    borderTop: '1px solid #e2e8f0',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    gap: '14px', flexWrap: 'wrap', flexShrink: 0,
  },
  statusBadge: {
    display: 'inline-flex', alignItems: 'center', gap: '4px',
    padding: '4px 11px', borderRadius: '30px',
    fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.03em',
  },
  chip: {
    display: 'inline-flex', alignItems: 'center', gap: '5px',
    background: 'rgba(79,70,229,0.07)', color: '#4338ca',
    padding: '4px 11px', borderRadius: '20px',
    fontSize: '0.77rem', fontWeight: 600,
  },
  notesBox: {
    padding: '14px 18px',
    background: 'rgba(254,242,242,0.9)',
    borderRadius: '14px',
    border: '1px solid rgba(252,165,165,0.5)',
    borderLeft: '4px solid #dc2626',
  },
  applyBtn: {
    display: 'inline-flex', alignItems: 'center', gap: '8px',
    background: 'linear-gradient(135deg, var(--primary-color) 0%, #7c3aed 100%)',
    color: 'white', padding: '11px 26px', borderRadius: '12px',
    fontWeight: 800, fontSize: '0.92rem', textDecoration: 'none',
    boxShadow: '0 4px 14px rgba(79,70,229,0.4)', border: 'none',
    cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
  },
  closeBtn: {
    background: 'rgba(100,116,139,0.1)', border: 'none', color: '#64748b',
    cursor: 'pointer', borderRadius: '50%', width: '34px', height: '34px',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
};

export default SchemeList;
