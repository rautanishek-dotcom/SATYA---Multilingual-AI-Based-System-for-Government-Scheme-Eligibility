import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  CheckCircle2, ChevronRight, Search, X, Target, ClipboardList, 
  Info, ExternalLink, ShieldCheck, FileCheck, User, MapPin, 
  Briefcase, GraduationCap, Users, Heart, AlertCircle, Sparkles,
  Phone, Mail, ArrowLeft, Clock, History, Layout, CreditCard,
  Building, Landmark, Milestone, FileText as ScrollText, List as ListIcon,
  Home, XCircle, Activity
} from 'lucide-react';

const EligibilityForm = () => {
  const { t, i18n } = useTranslation();
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 11;

  const [formData, setFormData] = useState({
    // Step 1: Personal
    name: '',
    dob: '',
    age: 0,
    gender: '',
    mobile: '',
    email: '',
    // Step 2: Location
    state: '',
    district: '',
    pincode: '',
    residence: 'urban',
    // Step 3: Financial
    income: '',
    income_category: '', // Auto-calculated
    bpl_status: false,
    ration_card_type: 'none',
    // Step 4: Family
    family_size: '',
    marital_status: '',
    // Step 5: Category
    category: 'general',
    is_minority: false,
    // Step 6: Education
    education_level: 'none',
    is_student: false,
    // Step 7: Occupation
    occupation: '',
    landholding_size: '',
    employment_type: '',
    business_type: '',
    business_turnover: '',
    // Step 8: Special Conditions
    is_disabled: false,
    disability_type: '',
    disability_percentage: '',
    has_disability_certificate: false,
    is_widow: false,
    is_single_parent: false,
    is_senior_citizen: false,
    // Step 9: Preferences
    scheme_preference: 'all',
    // Step 10: Declaration
    declaration_accepted: false
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [matchBreakdown, setMatchBreakdown] = useState(null);
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [isVerified, setIsVerified] = useState(false);
  const [showVerification, setShowVerification] = useState(false);
  const [userId, setUserId] = useState(null);
  const [activeTab, setActiveTab] = useState('eligible');
  
  // Disability Cert State
  const [certFile, setCertFile] = useState(null);
  const [certLoading, setCertLoading] = useState(false);
  const [certError, setCertError] = useState(null);
  const [certVerified, setCertVerified] = useState(false);
  
  // OTP State
  const [showOTPModal, setShowOTPModal] = useState(false);
  const [otpValue, setOtpValue] = useState(['', '', '', '', '', '']);
  const [otpTimer, setOtpTimer] = useState(0);
  const [resendCount, setResendCount] = useState(0);
  const [isMobileVerified, setIsMobileVerified] = useState(false);

  useEffect(() => {
    try {
      const userStr = localStorage.getItem('satya_user');
      if (userStr && userStr !== 'undefined' && userStr !== 'null') {
        const userObj = JSON.parse(userStr);
        if (userObj && userObj.id) {
          setUserId(userObj.id);
          setFormData(prev => ({ ...prev, name: userObj.name || prev.name }));
        }
      }
    } catch (err) {
      console.error("Error parsing user data:", err);
    }
  }, []);

  // Auto-calculations
  useEffect(() => {
    let age = 0;
    if (formData.dob) {
      const birthDate = new Date(formData.dob);
      const today = new Date();
      age = today.getFullYear() - birthDate.getFullYear();
      const m = today.getMonth() - birthDate.getMonth();
      if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
        age--;
      }
    }

    const incomeVal = parseInt(formData.income) || 0;
    let incCat = '';
    if (incomeVal > 0) {
      if (incomeVal < 100000) incCat = 'Below 1L';
      else if (incomeVal <= 300000) incCat = '1L - 3L';
      else if (incomeVal <= 500000) incCat = '3L - 5L';
      else incCat = 'Above 5L';
    }

    setFormData(prev => ({ 
      ...prev, 
      age: formData.dob ? age : prev.age,
      is_senior_citizen: formData.dob ? (age >= 60) : prev.is_senior_citizen,
      income_category: incCat
    }));
  }, [formData.dob, formData.income]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({ 
      ...formData, 
      [name]: type === 'checkbox' ? checked : value 
    });
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      setCertError(t('FileTooLarge', 'File size exceeds 2MB limit'));
      return;
    }

    const allowed = ['application/pdf', 'image/jpeg', 'image/png'];
    if (!allowed.includes(file.type)) {
      setCertError(t('InvalidFileType', 'Only PDF, JPG, and PNG are allowed'));
      return;
    }

    setCertFile(file);
    setCertError(null);
    uploadCertificate(file);
  };

  const uploadCertificate = async (file) => {
    setCertLoading(true);
    setCertVerified(false);
    const formDataUpload = new FormData();
    formDataUpload.append('file', file);
    formDataUpload.append('user_id', userId || 'guest');
    formDataUpload.append('name', formData.name);
    formDataUpload.append('disability_percentage', formData.disability_percentage);

    try {
      const response = await fetch('http://localhost:5000/api/verify/disability-upload', {
        method: 'POST',
        body: formDataUpload
      });
      const data = await response.json();
      if (data.status === 'Verified' || data.status === 'Partially Verified') {
        setCertVerified(true);
      } else if (data.error) {
          setCertError(data.error);
      }
    } catch (err) {
      setCertError(t('UploadFailed', 'Certificate upload failed'));
    } finally {
      setCertLoading(false);
    }
  };

  const removeFile = () => {
    setCertFile(null);
    setCertVerified(false);
    setCertError(null);
  };

  const nextStep = () => setCurrentStep(prev => Math.min(prev + 1, totalSteps));
  const prevStep = () => setCurrentStep(prev => Math.max(prev - 1, 1));

  const handleVerifyOTP = () => {
    setIsMobileVerified(true);
    setShowOTPModal(false);
  };

  const startOTPTimer = () => {
    setOtpTimer(30);
    const interval = setInterval(() => {
      setOtpTimer(prev => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleSendOTP = () => {
    if (resendCount >= 3) return;
    setShowOTPModal(true);
    setResendCount(prev => prev + 1);
    startOTPTimer();
  };

  const handleSubmit = async (e, isAutoRefresh = false) => {
    if (e) e.preventDefault();
    if (!formData.declaration_accepted) return;
    
    if (!isAutoRefresh) setLoading(true);
    setError(null);
    
    try {
      const payload = { 
        ...formData, 
        user_id: userId, 
        lang: i18n.language,
        certificate_uploaded: true // Mark as uploaded because they have verified documents in vault
      };
      const response = await fetch('http://localhost:5000/api/eligibility/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || t('ServerConnectionError', "Failed to connect to government servers"));
      }

      const data = await response.json();
      
      if (!data.identity_verified) {
        setIsVerified(false);
        setResults(null);
        setMatchBreakdown(data.match_breakdown || null);
        setError(data.reason || "Identity verification failed.");
        if (!isAutoRefresh) {
          setShowVerification(true);
          setCurrentStep(11);
        }
        setLoading(false);
        return;
      }
      
      setIsVerified(true);
      setResults(data.eligible_schemes);
      setMatchBreakdown(data.match_breakdown || null);
      if (!isAutoRefresh) setShowVerification(false); // don't show vault notice
      if (!isAutoRefresh) setCurrentStep(11);
    } catch (err) {
      console.error("Error fetching eligible schemes:", err);
      setError(err.message);
      if (!isAutoRefresh) setCurrentStep(11);
    } finally {
      if (!isAutoRefresh) setLoading(false);
    }
  };

  const renderResults = () => {
    if (error) {
        return (
            <div className="glass-card" style={styles.placeholderCard}>
               <XCircle size={60} color="#ef4444" style={{ marginBottom: '20px' }} />
               <h3>{t('ErrorOccurred', 'Verification Failed')}</h3>
               <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '12px', maxWidth: '400px' }}>
                 {error}
               </p>
               
               {matchBreakdown && (
                 <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(239, 68, 68, 0.05)', borderRadius: '12px', width: '100%', maxWidth: '400px', border: '1px solid rgba(239, 68, 68, 0.1)' }}>
                   <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#7f1d1d' }}>Identity Match Details</h4>
                   <div style={{ display: 'grid', gap: '8px', fontSize: '13px' }}>
                     <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                       <span style={{ color: '#475569' }}>Name Match:</span>
                       <span style={{ fontWeight: 600 }}>{matchBreakdown.name?.similarity}%</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                       <span style={{ color: '#475569' }}>DOB Match:</span>
                       <span style={{ fontWeight: 600, color: matchBreakdown.dob?.match ? '#16a34a' : '#dc2626' }}>
                         {matchBreakdown.dob?.match ? 'Yes' : 'No'}
                       </span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                       <span style={{ color: '#475569' }}>Gender Match:</span>
                       <span style={{ fontWeight: 600, color: matchBreakdown.gender?.match ? '#16a34a' : '#dc2626' }}>
                         {matchBreakdown.gender?.match ? 'Yes' : 'No'}
                       </span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid rgba(0,0,0,0.05)', paddingTop: '8px', marginTop: '4px' }}>
                       <span style={{ fontWeight: 600 }}>Total Score:</span>
                       <span style={{ fontWeight: 700, color: matchBreakdown.total >= 90 ? '#16a34a' : '#dc2626' }}>{matchBreakdown.total}%</span>
                     </div>
                   </div>
                 </div>
               )}

               <button 
                 onClick={() => handleSubmit()} 
                 style={{...styles.submitBtn, marginTop: '24px', width: 'auto', padding: '10px 30px'}}
               >
                 {t('Retry', 'Retry')}
               </button>
            </div>
        );
    }

    if (!results) {
        return (
            <div className="glass-card" style={styles.placeholderCard}>
               <Sparkles size={60} color="var(--primary-color)" style={{ marginBottom: '20px' }} />
               <h3>{t('FindingBestSchemes', 'Finding best schemes for you...')}</h3>
               <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '12px' }}>
                 {t('FinalizingResults', 'Almost there! Finalizing your eligibility results.')}
               </p>
            </div>
        );
    }

    if (showVerification && !isVerified) {
        return (
            <div className="glass-card animate-fade-in" style={styles.placeholderCard}>
                <ShieldCheck size={64} color="#ef4444" style={{ marginBottom: '20px' }} />
                <h3 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)' }}>
                   Document Vault Verification Required
                </h3>
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '12px', maxWidth: '450px', lineHeight: 1.6 }}>
                   {error || "To view eligible schemes, SATYA requires at least one verified document in your personal SATYA AI Document Vault that matches your identity."}
                </p>
                <div style={{ display: 'flex', gap: '16px', marginTop: '24px', flexWrap: 'wrap', justifyContent: 'center' }}>
                    <button 
                      onClick={() => window.location.href = '/vault'} 
                      style={{...styles.submitBtn, width: 'auto', padding: '12px 30px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '12px', cursor: 'pointer', fontWeight: 600}}
                    >
                      Go to Document Vault
                    </button>
                    <button 
                      onClick={() => handleSubmit()} 
                      style={{...styles.submitBtn, width: 'auto', padding: '12px 30px', background: 'transparent', border: '1px solid #e2e8f0', color: 'var(--text-color)', borderRadius: '12px', cursor: 'pointer', fontWeight: 600}}
                    >
                      Check Status Again
                    </button>
                </div>
            </div>
        );
    }

    if (!isVerified) {
        return (
            <div className="glass-card" style={styles.placeholderCard}>
               <ShieldCheck size={60} color="var(--primary-color)" style={{ marginBottom: '20px' }} />
               <h3>{t('VerificationRequired')}</h3>
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '12px', maxWidth: '300px' }}>
                  {error || "Please verify documents in your Document Vault first."}
                </p>
            </div>
        );
    }

    return (
        <div className="animate-fade-in" style={styles.resultsContainer}>
            <div style={styles.tabs}>
                <button 
                  style={{...styles.tab, ...(activeTab === 'eligible' ? styles.activeTab : {})}} 
                  onClick={() => setActiveTab('eligible')}
                >
                  <Target size={18} /> {t('Eligible', 'Eligible')} ({results.eligible?.length || 0})
                </button>
                <button 
                  style={{...styles.tab, ...(activeTab === 'ineligible' ? styles.activeTab : {})}} 
                  onClick={() => setActiveTab('ineligible')}
                >
                  <AlertCircle size={18} /> {t('NotEligible', 'Not Eligible')} ({results.ineligible?.length || 0})
                </button>
            </div>

            <div style={styles.schemeList}>
                {activeTab === 'eligible' ? (
                  results.eligible?.length === 0 ? (
                    <div className="glass-card" style={styles.emptyResults}>
                      <Info size={32} color="var(--text-muted)" />
                      <p>{t('NoEligibleFound', 'No schemes found for your current profile. Try adjusting details or check other states.')}</p>
                    </div>
                  ) : (
                    results.eligible.map((scheme, idx) => (
                      <SchemeItem key={idx} scheme={scheme} t={t} onSelect={setSelectedScheme} />
                    ))
                  )
                ) : (
                  results.ineligible?.length === 0 ? (
                    <div className="glass-card" style={styles.emptyResults}><p>{t('NothingToDisplay')}</p></div>
                  ) : (
                    results.ineligible.map((scheme, idx) => (
                      <SchemeItem key={idx} scheme={scheme} t={t} onSelect={setSelectedScheme} isIneligible={true} />
                    ))
                  )
                )}
            </div>
        </div>
    );
  };

  const renderStep = () => {
    switch(currentStep) {
      case 1:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={User} title={t('PersonalInformation')} />
            <div style={styles.inputGroup}>
              <label>{t('FullName')}*</label>
              <input type="text" name="name" value={formData.name} onChange={handleChange} style={styles.input} placeholder={t('FullNamePlaceholder', 'e.g. Rahul Sharma')} required />
            </div>
            <div style={styles.row}>
              <div style={styles.inputGroup}>
                <label>{t('DateOfBirth')}*</label>
                <input type="date" name="dob" value={formData.dob} onChange={handleChange} style={styles.input} required />
              </div>
              <div style={styles.inputGroup}>
                <label>{t('Age')}</label>
                <input type="text" value={formData.age} disabled style={{...styles.input, background: '#f1f5f9'}} />
              </div>
            </div>
            <div style={styles.inputGroup}>
                <label>{t('Gender')}*</label>
                <select name="gender" value={formData.gender} onChange={handleChange} style={styles.input} required>
                  <option value="">{t('SelectGender')}</option>
                  <option value="male">{t('Male')}</option>
                  <option value="female">{t('Female')}</option>
                  <option value="other">{t('Other')}</option>
                </select>
            </div>
            <div style={styles.row}>
                <div style={styles.inputGroup}>
                    <label>{t('MobileNumber')}*</label>
                    <div style={styles.inputWithBtn}>
                        <input type="tel" name="mobile" value={formData.mobile} onChange={handleChange} style={styles.input} placeholder={t('MobilePlaceholder')} />
                        <button 
                          type="button" 
                          onClick={handleSendOTP} 
                          style={isMobileVerified ? styles.verifiedBtn : styles.verifyBtn}
                          disabled={isMobileVerified}
                        >
                            {isMobileVerified ? <CheckCircle2 size={16}/> : t('Verify')}
                        </button>
                    </div>
                </div>
                <div style={styles.inputGroup}>
                    <label>{t('EmailID')}</label>
                    <input type="email" name="email" value={formData.email} onChange={handleChange} style={styles.input} placeholder={t('Optional')} />
                </div>
            </div>
          </div>
        );
      case 2:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={MapPin} title={t('LocationDetails')} />
            <div style={styles.row}>
                <div style={styles.inputGroup}>
                    <label>{t('State')}*</label>
                    <select name="state" value={formData.state} onChange={handleChange} style={styles.input} required>
                        <option value="">{t('SelectState')}</option>
                        {['Andhra Pradesh', 'Bihar', 'Gujarat', 'Haryana', 'Karnataka', 'Maharashtra', 'Punjab', 'Rajasthan', 'Tamil Nadu', 'Uttar Pradesh', 'West Bengal', 'Delhi'].map(s => (
                            <option key={s} value={s}>{t(s.replace(/\s/g, ''), s)}</option>
                        ))}
                    </select>
                </div>
                <div style={styles.inputGroup}>
                    <label>{t('District')}*</label>
                    <input type="text" name="district" value={formData.district} onChange={handleChange} style={styles.input} placeholder={t('DistrictPlaceholder', 'District')} required />
                </div>
            </div>
            <div style={styles.row}>
                <div style={styles.inputGroup}>
                    <label>{t('Pincode')}*</label>
                    <input type="text" name="pincode" value={formData.pincode} onChange={handleChange} style={styles.input} maxLength="6" placeholder={t('PincodePlaceholder', '6-digit PIN')} required />
                </div>
                <div style={styles.inputGroup}>
                    <label>{t('ResidenceType')}*</label>
                    <select name="residence" value={formData.residence} onChange={handleChange} style={styles.input}>
                        <option value="urban">{t('Urban')}</option>
                        <option value="rural">{t('Rural')}</option>
                    </select>
                </div>
            </div>
          </div>
        );
      case 3:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={CreditCard} title={t('IncomeFinancialDetails')} />
            <div style={styles.inputGroup}>
                <label>{t('AnnualFamilyIncome')} (₹)*</label>
                <input type="number" name="income" value={formData.income} onChange={handleChange} style={styles.input} placeholder={t('IncomePlaceholder')} required />
            </div>
            <div style={styles.inputGroup}>
                <label>{t('IncomeCategory')}</label>
                <div style={styles.infoBadge}>
                    {formData.income ? 
                        t((formData.income_category || '').replace(/\s/g, '').replace(/-/g, ''), formData.income_category) : 
                        <span style={{color: '#94a3b8', fontStyle: 'italic', fontWeight: 400}}>{t('NotCalculated')}</span>
                    }
                </div>
            </div>
            <div style={styles.row}>
                <div style={{...styles.inputGroup, flex: 0.5}}>
                    <label>{t('BPLStatus')}</label>
                    <div style={{...styles.toggleRow, cursor: 'pointer', userSelect: 'none'}} onClick={() => handleChange({target: {name: 'bpl_status', type: 'checkbox', checked: !formData.bpl_status}})}>
                         <label style={styles.switch} onClick={e => e.stopPropagation()}>
                            <input type="checkbox" name="bpl_status" checked={formData.bpl_status} onChange={handleChange} />
                            <span className="slider round"></span>
                        </label>
                        <span>{formData.bpl_status ? t('Yes') : t('No')}</span>
                    </div>
                </div>
                <div style={styles.inputGroup}>
                    <label>{t('RationCardType')}</label>
                    <select name="ration_card_type" value={formData.ration_card_type} onChange={handleChange} style={styles.input}>
                        <option value="none">{t('None')}</option>
                        <option value="aph">{t('AAY')}</option>
                        <option value="phh">{t('PHH')}</option>
                        <option value="nphh">{t('NPHH')}</option>
                    </select>
                </div>
            </div>
          </div>
        );
      case 4:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={Users} title={t('FamilySocialDetails', 'Family & Social Details')} />
            <div style={styles.row}>
                <div style={styles.inputGroup}>
                    <label>{t('FamilySize')}*</label>
                    <input type="number" name="family_size" value={formData.family_size} onChange={handleChange} style={styles.input} placeholder={t('FamilySizePlaceholder', 'No. of members')} required />
                </div>
                <div style={styles.inputGroup}>
                    <label>{t('MaritalStatus')}*</label>
                    <select name="marital_status" value={formData.marital_status} onChange={handleChange} style={styles.input} required>
                        <option value="">{t('SelectStatus')}</option>
                        <option value="single">{t('Single')}</option>
                        <option value="married">{t('Married')}</option>
                        <option value="widowed">{t('Widowed')}</option>
                        <option value="divorced">{t('Divorced')}</option>
                    </select>
                </div>
            </div>
          </div>
        );
      case 5:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={Target} title={t('CategoryDetails', 'Category Details')} />
            <div style={styles.row}>
                <div style={styles.inputGroup}>
                    <label>{t('Category')}*</label>
                    <select name="category" value={formData.category} onChange={handleChange} style={styles.input}>
                        <option value="general">{t('General')}</option>
                        <option value="obc">{t('OBC')}</option>
                        <option value="sc">{t('SC')}</option>
                        <option value="st">{t('ST')}</option>
                    </select>
                </div>
                <div style={{...styles.inputGroup, flex: 0.5}}>
                    <label>{t('MinorityStatus')}</label>
                        <div style={{...styles.toggleRow, cursor: 'pointer', userSelect: 'none'}} onClick={() => handleChange({target: {name: 'is_minority', type: 'checkbox', checked: !formData.is_minority}})}>
                             <label style={styles.switch} onClick={e => e.stopPropagation()}>
                                <input type="checkbox" name="is_minority" checked={formData.is_minority} onChange={handleChange} />
                                <span className="slider round"></span>
                            </label>
                            <span>{formData.is_minority ? t('Yes') : t('No')}</span>
                        </div>
                </div>
            </div>
          </div>
        );
      case 6:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={GraduationCap} title={t('EducationDetails', 'Education Details')} />
            <div style={styles.inputGroup}>
                <label>{t('EducationLevel')}*</label>
                <select name="education_level" value={formData.education_level} onChange={handleChange} style={styles.input}>
                    <option value="none">{t('NoneUneducated')}</option>
                    <option value="primary">{t('PrimarySchool')}</option>
                    <option value="secondary">{t('SecondaryHigherSec')}</option>
                    <option value="graduate">{t('Graduate')}</option>
                    <option value="postgraduate">{t('PostGraduate')}</option>
                </select>
            </div>
            <div style={{...styles.toggleRow, cursor: 'pointer', userSelect: 'none'}} onClick={() => handleChange({target: {name: 'is_student', type: 'checkbox', checked: !formData.is_student}})}>
                 <label style={styles.switch} onClick={e => e.stopPropagation()}>
                    <input type="checkbox" name="is_student" checked={formData.is_student} onChange={handleChange} />
                    <span className="slider round"></span>
                </label>
                <span>{t('CurrentlyStudent')}</span>
            </div>
          </div>
        );
      case 7:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={Briefcase} title={t('OccupationDetails', 'Occupation Details')} />
            <div style={styles.inputGroup}>
                <label>{t('MainOccupation')}*</label>
                <select name="occupation" value={formData.occupation} onChange={handleChange} style={styles.input} required>
                  <option value="">{t('SelectOccupation')}</option>
                  <option value="farmer">{t('Farmer')}</option>
                  <option value="worker">{t('Worker')}</option>
                  <option value="business">{t('Business')}</option>
                  <option value="service">{t('Service')}</option>
                  <option value="retired">{t('Retired')}</option>
                  <option value="other">{t('Other')}</option>
                </select>
            </div>
            
            {formData.occupation === 'farmer' && (
                <div style={styles.inputGroup} className="animate-fade-in">
                    <label>{t('Landholding')}*</label>
                    <input type="number" step="0.1" name="landholding_size" value={formData.landholding_size} onChange={handleChange} style={styles.input} placeholder={t('InAcres')} />
                </div>
            )}
            
            {formData.occupation === 'worker' && (
                <div style={styles.inputGroup} className="animate-fade-in">
                    <label>{t('EmploymentType')}*</label>
                    <select name="employment_type" value={formData.employment_type} onChange={handleChange} style={styles.input}>
                        <option value="unorganized">{t('UnorganizedSector')}</option>
                        <option value="construction">{t('Construction')}</option>
                        <option value="handicraft">{t('HandicraftsArtisan')}</option>
                    </select>
                </div>
            )}
            
            {formData.occupation === 'business' && (
                <div style={styles.row} className="animate-fade-in">
                    <div style={styles.inputGroup}>
                        <label>{t('BusinessType')}*</label>
                        <select name="business_type" value={formData.business_type} onChange={handleChange} style={styles.input}>
                            <option value="micro">{t('Micro')}</option>
                            <option value="small">{t('SmallScale')}</option>
                            <option value="startup">{t('Startup')}</option>
                        </select>
                    </div>
                    <div style={styles.inputGroup}>
                        <label>{t('AnnualTurnover')} (₹)*</label>
                        <input type="number" name="business_turnover" value={formData.business_turnover} onChange={handleChange} style={styles.input} />
                    </div>
                </div>
            )}
          </div>
        );
      case 8:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={Heart} title={t('SpecialConditions', 'Special Conditions')} />
            
            <div style={{...styles.toggleRow, marginBottom: '20px', padding: '15px', background: 'rgba(79, 70, 229, 0.05)', borderRadius: '15px', border: '1px solid rgba(79, 70, 229, 0.1)', cursor: 'pointer', userSelect: 'none'}} onClick={() => handleChange({target: {name: 'is_disabled', type: 'checkbox', checked: !formData.is_disabled}})}>
                 <label style={styles.switch} onClick={e => e.stopPropagation()}>
                    <input type="checkbox" name="is_disabled" checked={formData.is_disabled} onChange={handleChange} />
                    <span className="slider round"></span>
                </label>
                <div style={{display: 'flex', flexDirection: 'column'}}>
                    <span style={{fontWeight: 700, color: 'var(--primary-color)'}}>{t('DifferentlyAbled')}</span>
                    <span style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>{t('DisabilityHint', 'Minimum 40% required for most schemes')}</span>
                </div>
            </div>
            
            {formData.is_disabled && (
                <div className="animate-fade-in" style={{display: 'flex', flexDirection: 'column', gap: '20px', padding: '20px', background: '#f8fafc', borderRadius: '15px', marginBottom: '20px'}}>
                    <div style={styles.row}>
                        <div style={{...styles.inputGroup, flex: 1}}>
                            <label>{t('DisabilityType')}*</label>
                            <select name="disability_type" value={formData.disability_type} onChange={handleChange} style={styles.input}>
                                <option value="" disabled>{t('SelectDisabilityTypePlaceholder', 'Select Disability Type')}</option>
                                <option value="locomotor">{t('Locomotor')}</option>
                                <option value="visual">{t('Visual')}</option>
                                <option value="hearing">{t('Hearing')}</option>
                                <option value="intellectual">{t('Intellectual')}</option>
                                <option value="mental">{t('Mental')}</option>
                                <option value="multiple">{t('Multiple')}</option>
                                <option value="other">{t('Other')}</option>
                            </select>
                        </div>
                        <div style={{...styles.inputGroup, width: '150px'}}>
                            <label>{t('DisabilityPercentage')}*</label>
                            <input 
                              type="number" 
                              name="disability_percentage" 
                              value={formData.disability_percentage} 
                              onChange={(e) => {
                                  let val = parseInt(e.target.value);
                                  if (val < 0) val = 0;
                                  if (val > 100) val = 100;
                                  handleChange({target: {name: 'disability_percentage', value: val}});
                              }} 
                              style={{...styles.input, borderColor: formData.disability_percentage > 0 && formData.disability_percentage < 40 ? '#f59e0b' : '#e2e8f0'}} 
                              min="0" 
                              max="100" 
                              placeholder="%" 
                            />
                        </div>
                    </div>

                        <div style={{...styles.toggleRow, cursor: 'pointer', userSelect: 'none'}} onClick={() => handleChange({target: {name: 'has_disability_certificate', type: 'checkbox', checked: !formData.has_disability_certificate}})}>
                         <label style={styles.switch} onClick={e => e.stopPropagation()}>
                            <input type="checkbox" name="has_disability_certificate" checked={formData.has_disability_certificate} onChange={handleChange} />
                            <span className="slider round"></span>
                        </label>
                        <span style={{fontSize: '0.95rem'}}>{t('DisabilityCertificate')}</span>
                    </div>

                    <div style={{padding: '15px', background: 'white', borderRadius: '12px', border: '1px dashed #cbd5e1'}}>
                        <label style={{fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '10px', display: 'block'}}>{t('UploadDisabilityCert', 'Upload Disability Certificate')}</label>
                        {!certFile ? (
                            <div style={{position: 'relative'}}>
                                <input 
                                    type="file" 
                                    onChange={handleFileChange} 
                                    style={{position: 'absolute', opacity: 0, width: '100%', height: '100%', cursor: 'pointer'}} 
                                    accept=".pdf,.jpg,.jpeg,.png"
                                />
                                <div style={{padding: '12px', background: '#f1f5f9', borderRadius: '8px', textAlign: 'center', color: 'var(--primary-color)', fontWeight: 600}}>
                                    <FileCheck size={18} style={{verticalAlign: 'middle', marginRight: '8px'}} />
                                    {t('ChooseFile', 'Choose File')}
                                </div>
                                <span style={{fontSize: '0.7rem', color: '#64748b', marginTop: '5px', display: 'block'}}>{t('FileTypesNote', 'PDF, JPG, PNG (Max 2MB)')}</span>
                            </div>
                        ) : (
                            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'rgba(79, 70, 229, 0.05)', borderRadius: '8px', border: '1px solid var(--primary-color)'}}>
                                <div style={{display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: 'var(--primary-color)', fontWeight: 500}}>
                                    {certLoading ? <Activity size={16} className="spin" /> : (certVerified ? <CheckCircle2 size={16} color="#10b981" /> : <ShieldCheck size={16} />)}
                                    <span style={{maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>{certFile.name}</span>
                                </div>
                                <button type="button" onClick={removeFile} style={{color: '#ef4444', background: 'none', padding: '5px', borderRadius: '5px'}}>
                                    <X size={16} />
                                </button>
                            </div>
                        )}
                        {certLoading && <span style={{fontSize: '0.75rem', color: 'var(--primary-color)', marginTop: '8px', display: 'block'}}>{t('ScanningDocument', 'AI scanning in progress...')}</span>}
                        {certError && <span style={{fontSize: '0.75rem', color: '#ef4444', marginTop: '8px', display: 'block'}}>{certError}</span>}
                    </div>

                    {formData.disability_percentage >= 40 && (
                        <div style={{display: 'flex', gap: '10px', alignItems: 'center', background: 'rgba(16, 185, 129, 0.1)', color: '#059669', padding: '12px 18px', borderRadius: '12px', fontSize: '0.9rem'}}>
                            <ShieldCheck size={18} />
                            <span>{t('DisabilityRewardHint', 'You may be eligible for disability-based schemes')}</span>
                        </div>
                    )}
                </div>
            )}
            
            <div style={styles.gridChecks}>
                <label style={{...styles.checkCard, ...(formData.is_widow ? {borderColor: 'var(--primary-color)', background: 'rgba(79, 70, 229, 0.05)'} : {})}}>
                    <input type="checkbox" name="is_widow" checked={formData.is_widow} onChange={handleChange} />
                    <span>{t('Widow/Widower')}</span>
                </label>
                <label style={{...styles.checkCard, ...(formData.is_single_parent ? {borderColor: 'var(--primary-color)', background: 'rgba(79, 70, 229, 0.05)'} : {})}}>
                    <input type="checkbox" name="is_single_parent" checked={formData.is_single_parent} onChange={handleChange} />
                    <span>{t('SingleParent')}</span>
                </label>
                <label style={{...styles.checkCard, ...(formData.is_senior_citizen ? {borderColor: 'var(--primary-color)', background: 'rgba(79, 70, 229, 0.05)'} : {})}}>
                    <input type="checkbox" name="is_senior_citizen" checked={formData.is_senior_citizen} onChange={handleChange} />
                    <span>{t('SeniorCitizen')}</span>
                </label>
            </div>
          </div>
        );
      case 9:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={ListIcon} title={t('SchemePreferences')} />
            <p style={{color: 'var(--text-muted)', marginBottom: '15px'}}>{t('PreferenceDesc')}</p>
            
            <div style={styles.gridChecks}>
                {['Agriculture', 'Health', 'Education', 'Housing', 'Business', 'Pension', 'All'].map(pref => (
                    <label key={pref} style={{...styles.checkCard, ...(formData.scheme_preference === pref.toLowerCase() ? {borderColor: 'var(--primary-color)', background: 'rgba(79, 70, 229, 0.05)'} : {})}}>
                        <input 
                            type="radio" 
                            name="scheme_preference" 
                            value={pref.toLowerCase()} 
                            checked={formData.scheme_preference === pref.toLowerCase()} 
                            onChange={handleChange} 
                            style={{display: 'none'}} 
                        />
                        <span style={{fontWeight: formData.scheme_preference === pref.toLowerCase() ? 600 : 400}}>{t(pref, pref)}</span>
                    </label>
                ))}
            </div>
          </div>
        );
      case 10:
        return (
          <div className="animate-fade-in" style={styles.stepContent}>
            <SectionHeader icon={FileCheck} title={t('Declaration')} />
            <div style={{background: '#f8fafc', padding: '25px', borderRadius: '15px', border: '1px solid #e2e8f0', lineHeight: 1.8, fontSize: '0.95rem', color: '#475569', marginBottom: '20px'}}>
                <p>{t('DeclarativeStatement')}</p>
                <p style={{marginTop: '10px'}}>{t('AadhaarConsent', 'I consent to the use of my Aadhaar for verification purposes to finalize my application (if applicable).')}</p>
            </div>
            
            <label style={{...styles.checkboxLabel, background: 'var(--primary-color)', padding: '20px', borderRadius: '15px', color: 'white', display: 'flex', alignItems: 'center', gap: '15px', cursor: 'pointer', boxShadow: 'var(--shadow-md)'}}>
                <input type="checkbox" name="declaration_accepted" checked={formData.declaration_accepted} onChange={handleChange} style={{width: '20px', height: '20px'}} />
                <span style={{fontWeight: 600, fontSize: '1.05rem'}}>{t('AcceptDeclaration')}</span>
            </label>
          </div>
        );
      case 11:
        return renderResults ? renderResults() : null;
    }
  };

  return (
    <>
    <div className="container animate-fade-in" style={styles.container}>
      <div style={styles.header}>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 800, marginBottom: '10px' }}>
          <span className="gradient-text">{t('EligibilityEngine')}</span>
        </h2>
        <p style={{ color: 'var(--text-muted)' }}>{t('StepByStepInstructions', 'Complete all sections for precise matching.')}</p>
      </div>

      <div style={styles.portalLayout}>
        {/* Step Navigation */}
        <div style={styles.sidebar}>
            <div style={styles.progressContainer}>
                <div style={{...styles.progressBar, height: `${(currentStep / totalSteps) * 100}%`}}></div>
                {[...Array(totalSteps)].map((_, i) => (
                    <div 
                      key={i} 
                      style={{
                        ...styles.stepNode, 
                        background: currentStep > i + 1 ? 'var(--secondary-color)' : (currentStep === i + 1 ? 'var(--primary-color)' : '#e2e8f0'),
                        borderColor: currentStep === i + 1 ? 'rgba(79, 70, 229, 0.3)' : 'transparent'
                      }}
                      onClick={() => setCurrentStep(i + 1)}
                    >
                        {currentStep > i + 1 ? <CheckCircle2 size={12} color="white" /> : i + 1}
                    </div>
                ))}
            </div>
            <div style={styles.stepLabels}>
                {['Personal', 'Location', 'Income', 'Family', 'Category', 'Education', 'Occupation', 'Special', 'Preference', 'Declaration', 'FinalResult'].map((label, i) => (
                    <span key={i} style={{...styles.stepLabel, color: currentStep === i + 1 ? 'var(--primary-color)' : 'var(--text-muted)'}}>{t(label)}</span>
                ))}
            </div>
        </div>

        {/* Main Form Area */}
        <div className="glass-card" style={styles.formContainer}>
            {renderStep()}
            
            {currentStep < 11 && (
                <div style={styles.formFooter}>
                    {currentStep > 1 && (
                        <button type="button" onClick={prevStep} style={styles.backBtn}>
                            <ArrowLeft size={18} /> {t('Back')}
                        </button>
                    )}
                    {currentStep < 10 ? (
                        <button type="button" onClick={nextStep} style={{...styles.nextBtn, marginLeft: currentStep === 1 ? 'auto' : '0'}}>
                            {t('Next')} <ChevronRight size={18} />
                        </button>
                    ) : (
                        <button type="button" onClick={handleSubmit} style={styles.submitBtn} disabled={loading || !formData.declaration_accepted}>
                            {loading ? <div style={styles.spinner}></div> : t('FindSchemesNow')}
                        </button>
                    )}
                </div>
            )}
        </div>
      </div>
    </div>

      {/* Detail Modal */}
      {selectedScheme && (
        <SchemeDetailModal 
          scheme={selectedScheme} 
          onClose={() => setSelectedScheme(null)} 
          t={t} 
        />
      )}

      {/* OTP Modal */}
      {showOTPModal && (
          <div style={styles.modalOverlay}>
              <div className="glass-card animate-scale-up" style={styles.otpModal}>
                  <div style={styles.otpHeader}>
                      <Phone size={24} color="var(--primary-color)" />
                      <h3>{t('VerifyMobile')}</h3>
                      <button onClick={() => setShowOTPModal(false)} style={styles.closeBtn}><X size={20}/></button>
                  </div>
                  <p style={styles.otpDesc}>{t('OTPSent')} to <b>+91 {formData.mobile}</b></p>
                  <div style={styles.otpInputs}>
                      {otpValue.map((digit, i) => (
                          <input 
                            key={i} 
                            type="text" 
                            maxLength="1" 
                            style={styles.otpBox} 
                            value={digit}
                            onChange={(e) => {
                                let newOtp = [...otpValue];
                                newOtp[i] = e.target.value;
                                setOtpValue(newOtp);
                                // Auto-focus next
                                if (e.target.value && i < 5) e.target.nextSibling?.focus();
                            }}
                          />
                      ))}
                  </div>
                  <p style={{textAlign: 'center', fontSize: '0.8rem', color: '#10b981', marginTop: '10px'}}>{t('DemoOTPNote', '(Demo: Enter any 6 digits)')}</p>
                  <div style={styles.otpFooter}>
                      <button 
                        onClick={handleSendOTP} 
                        disabled={otpTimer > 0 || resendCount >= 3} 
                        style={styles.resendBtn}
                      >
                          {otpTimer > 0 ? t('OTPTimer', { seconds: otpTimer }) : t('ResendOTP')}
                      </button>
                      <button onClick={handleVerifyOTP} className="btn-primary" style={styles.verifyConfirmBtn}>
                          {t('Verify')}
                      </button>
                  </div>
                  {resendCount >= 3 && <p style={styles.errorText}>{t('MaxRetriesError', 'Max retries reached. Try again later.')}</p>}
              </div>
          </div>
      )}
    </>
  );
};

const SectionHeader = ({ icon: Icon, title }) => (
    <div style={styles.sectionHeader}>
        {Icon ? <Icon size={24} color="var(--primary-color)" /> : <div style={{width: 24}} />}
        <h3 style={{fontSize: '1.4rem', fontWeight: 700}}>{title}</h3>
    </div>
);

const styles = {
  container: { padding: '40px 0', maxWidth: '1200px' },
  header: { textAlign: 'center', marginBottom: '40px' },
  portalLayout: { display: 'grid', gridTemplateColumns: '250px 1fr', gap: '40px', alignItems: 'flex-start' },
  sidebar: { position: 'sticky', top: '100px', display: 'flex', gap: '20px' },
  progressContainer: { width: '4px', background: '#e2e8f0', borderRadius: '10px', position: 'relative', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '0' },
  progressBar: { position: 'absolute', top: 0, left: 0, width: '100%', background: 'var(--primary-color)', transition: 'height 0.3s ease', borderRadius: '10px' },
  stepNode: { width: '30px', height: '30px', borderRadius: '50%', background: 'white', border: '2px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer', zIndex: 1, marginLeft: '-13px', transition: 'all 0.2s' },
  stepLabels: { display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' },
  stepLabel: { fontSize: '0.85rem', fontWeight: 600, height: '30px', display: 'flex', alignItems: 'center' },
  formContainer: { padding: '50px', display: 'flex', flexDirection: 'column', minHeight: '600px', background: 'white' },
  stepContent: { flex: 1, display: 'flex', flexDirection: 'column', gap: '25px' },
  sectionHeader: { display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '10px', borderBottom: '1px solid #f1f5f9', paddingBottom: '15px' },
  inputGroup: { display: 'flex', flexDirection: 'column', gap: '8px' },
  input: { padding: '14px', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#f8fafc', fontSize: '1rem', outline: 'none' },
  row: { display: 'flex', gap: '20px' },
  inputWithBtn: { display: 'flex', gap: '10px' },
  verifyBtn: { padding: '0 20px', background: 'var(--primary-color)', color: 'white', border: 'none', borderRadius: '10px', fontWeight: 600, cursor: 'pointer' },
  verifiedBtn: { padding: '0 20px', background: '#10b981', color: 'white', border: 'none', borderRadius: '10px', cursor: 'default' },
  infoBadge: { background: 'rgba(79,70,229,0.05)', color: 'var(--primary-color)', padding: '14px', borderRadius: '12px', fontWeight: 700, border: '1px dashed var(--primary-color)' },
  switch: { position: 'relative', display: 'inline-block', width: '44px', height: '24px', flexShrink: 0 },
  toggleRow: { display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 0' },
  formFooter: { marginTop: 'auto', paddingTop: '40px', display: 'flex', justifyContent: 'space-between' },
  nextBtn: { padding: '14px 30px', background: 'var(--primary-color)', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' },
  backBtn: { padding: '14px 30px', background: 'transparent', border: '1px solid #e2e8f0', color: 'var(--text-muted)', borderRadius: '12px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' },
  submitBtn: { padding: '14px 40px', background: 'var(--secondary-color)', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 700, flex: 1, display: 'flex', justifyContent: 'center' },
  modalOverlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(5px)', zIndex: 10000, display: 'flex', justifyContent: 'center', alignItems: 'center' },
  otpModal: { width: '400px', padding: '30px', background: 'white' },
  otpHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' },
  otpDesc: { fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '25px' },
  otpInputs: { display: 'flex', gap: '10px', marginBottom: '30px' },
  otpBox: { width: '100%', height: '50px', textAlign: 'center', fontSize: '1.5rem', fontWeight: 700, borderRadius: '10px', border: '2px solid #e2e8f0', background: '#f8fafc', outline: 'none' },
  otpFooter: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  resendBtn: { background: 'transparent', border: 'none', color: 'var(--primary-color)', fontWeight: 600, cursor: 'pointer' },
  verifyConfirmBtn: { padding: '12px 25px', borderRadius: '10px' },
  closeBtn: { background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' },
  errorText: { color: '#ef4444', fontSize: '0.8rem', marginTop: '15px', textAlign: 'center' },
  placeholder: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' },
  gridChecks: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '15px' },
  checkCard: { display: 'flex', alignItems: 'center', gap: '10px', padding: '15px', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0', cursor: 'pointer', fontSize: '0.95rem' },
  checkboxLabel: { cursor: 'pointer' },
  resultsContainer: { display: 'flex', flexDirection: 'column', gap: '25px', width: '100%' },
  tabs: { display: 'flex', gap: '10px', background: 'rgba(255,255,255,0.5)', padding: '5px', borderRadius: '12px' },
  tab: { flex: 1, padding: '12px', borderRadius: '10px', border: 'none', background: 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontWeight: 600, color: 'var(--text-muted)' },
  activeTab: { background: 'white', color: 'var(--primary-color)', boxShadow: 'var(--shadow-md)' },
  schemeList: { display: 'flex', flexDirection: 'column', gap: '20px' },
  schemeCard: { padding: '25px', borderLeft: '6px solid', background: 'white', display: 'flex', flexDirection: 'column', borderRadius: '15px' },
  schemeHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' },
  schemeTitle: { fontSize: '1.3rem', fontWeight: 700, color: 'var(--primary-color)' },
  schemeTag: { padding: '5px 12px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: 700 },
  schemeDesc: { color: 'var(--text-muted)', fontSize: '0.95rem', marginBottom: '20px', lineHeight: 1.6 },
  schemeActions: { display: 'flex', gap: '12px', marginTop: 'auto' },
  detailsBtn: { padding: '10px 20px', borderRadius: '10px' },
  applyLink: { background: 'var(--secondary-color)', color: 'white', padding: '10px 20px', borderRadius: '10px', fontSize: '0.9rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' },
  reasonsBox: { background: 'rgba(239, 68, 68, 0.05)', color: '#ef4444', padding: '12px', borderRadius: '10px', display: 'flex', gap: '10px', marginBottom: '20px', fontSize: '0.85rem' },
  reason: { fontStyle: 'italic' },
  partialReason: { display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(245, 158, 11, 0.05)', color: '#d97706', padding: '8px 12px', borderRadius: '8px', fontSize: '0.8rem', marginBottom: '15px' },
  emptyResults: { padding: '40px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '15px' },
  placeholderCard: { flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', minHeight: '400px', background: 'rgba(255,255,255,0.4)', border: '2px dashed rgba(0,0,0,0.05)' },
  modalContent: { background: 'white', width: '850px', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', borderRadius: '24px' },
  modalHeader: { padding: '25px 40px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  modalTitleArea: { display: 'flex', gap: '20px', alignItems: 'center' },
  modalIcon: { background: 'rgba(79, 70, 229, 0.1)', color: 'var(--primary-color)', padding: '15px', borderRadius: '15px' },
  modalBody: { padding: '40px', overflowY: 'auto', flex: 1 },
  infoGrid: { display: 'flex', flexDirection: 'column', gap: '30px' },
  infoCard: { background: '#f8fafc', padding: '25px', borderRadius: '20px', border: '1px solid #f1f5f9' },
  modalText: { color: '#475569', lineHeight: 1.8 },
  stepsFlow: { display: 'flex', flexDirection: 'column', gap: '15px' },
  stepRow: { display: 'flex', gap: '15px', alignItems: 'flex-start' },
  stepNum: { background: 'var(--primary-color)', color: 'white', minWidth: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.9rem' },
  modalFooter: { padding: '25px 40px', background: '#f8fafc', borderTop: '1px solid #f1f5f9' },
  applyBtn: { background: 'var(--primary-color)', color: 'white', padding: '18px', borderRadius: '12px', fontWeight: 700, width: '100%', display: 'flex', justifyContent: 'center', gap: '12px', border: 'none', cursor: 'pointer' },
  eligibilityFeedback: { padding: '10px 0' },
  rulesList: { display: 'flex', flexDirection: 'column', gap: '10px' },
  stepsFlow: { display: 'flex', flexDirection: 'column', gap: '15px' },
  stepRow: { display: 'flex', gap: '15px', alignItems: 'flex-start' },
  stepNum: { background: 'var(--primary-color)', color: 'white', minWidth: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.9rem' }
};

const formatUrl = (url) => {
    if (!url || url === 'NA') return '#';
    return url.startsWith('http') ? url : `https://${url}`;
};

const formatSteps = (steps) => {
    if (!steps) return [];
    if (Array.isArray(steps)) return steps;
    if (typeof steps === 'string') return steps.split(/(?:\n|\b\d+\s*[.)])/).filter(s => s.trim() && !/^\d+$/.test(s.trim()));
    return [];
};

// Component for Scheme Card
const SchemeItem = ({ scheme, t, onSelect, isIneligible }) => {
  const isPartial = scheme.status === 'Partially Eligible';
  return (
  <div className="glass-card" style={{...styles.schemeCard, borderLeftColor: isIneligible ? 'var(--text-muted)' : (isPartial ? '#f59e0b' : 'var(--secondary-color)')}}>
    <div style={styles.schemeHeader}>
      <h4 style={styles.schemeTitle}>{scheme.name}</h4>
      <div style={{display: 'flex', gap: '8px'}}>
        <span style={{
          ...styles.schemeTag, 
          background: scheme.state === 'All India' ? 'rgba(79, 70, 229, 0.1)' : 'rgba(16, 185, 129, 0.1)',
          color: scheme.state === 'All India' ? 'var(--primary-color)' : 'var(--secondary-color)'
        }}>
          {scheme.state === 'All India' ? t('Central') : t(scheme.state.replace(/\s/g, ''), scheme.state)}
        </span>
        {scheme.match_score !== undefined && (
          <span style={{
              ...styles.schemeTag,
              background: scheme.match_score === 100 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
              color: scheme.match_score === 100 ? '#059669' : '#d97706',
              display: 'flex', alignItems: 'center', gap: '4px'
          }}>
              <CheckCircle2 size={12} /> {scheme.match_score}% {t('Match')}
          </span>
        )}
      </div>
    </div>
    
    <p style={styles.schemeDesc}>{scheme.description?.substring(0, 120)}...</p>
    
    {isPartial && scheme.reasons?.length > 0 && !isIneligible && (
        <div style={styles.partialReason}>
            <Info size={12} />
            <span>{t('PartialMatchNote', 'Matches most criteria')}</span>
        </div>
    )}
    
    {isIneligible && Array.isArray(scheme.reasons) && scheme.reasons.length > 0 && (
        <div style={styles.reasonsBox}>
            <AlertCircle size={14} />
            <div>
                {scheme.reasons.map((r, i) => <span key={i} style={styles.reason}>{r}{i < scheme.reasons.length - 1 ? ' • ' : ''}</span>)}
            </div>
        </div>
    )}

    <div style={styles.schemeActions}>
      <button 
        type="button"
        onClick={() => onSelect(scheme)} 
        className="btn-secondary" 
        style={styles.detailsBtn}
      >
        {t('ViewDetails')}
      </button>
      {!isIneligible && scheme.official_website && scheme.official_website !== 'NA' && (
        <a href={formatUrl(scheme.official_website)} target="_blank" rel="noopener noreferrer" style={styles.applyLink}>
          {t('ApplyNow')} <ExternalLink size={14} />
        </a>
      )}
    </div>
  </div>
)};

// Detail Modal Component
const SchemeDetailModal = ({ scheme, onClose, t }) => (
  <div style={styles.modalOverlay} onClick={onClose}>
    <div className="glass-card animate-fade-in" style={styles.modalContent} onClick={e => e.stopPropagation()}>
      <div style={styles.modalHeader}>
        <div style={styles.modalTitleArea}>
          <div style={styles.modalIcon}><Info size={24} /></div>
          <div>
            <h3>{scheme.name}</h3>
            <p style={{color:'var(--text-muted)'}}>{t('GovernmentSchemeDetails')}</p>
          </div>
        </div>
        <button onClick={onClose} style={styles.closeBtn}><X size={24} /></button>
      </div>

      <div style={styles.modalBody}>
        <div style={styles.infoGrid}>
          <div style={styles.infoCard}>
            <SectionHeader icon={Info} title={t('Overview')} />
            <p style={styles.modalText}>{scheme.description}</p>
          </div>

          <div style={styles.infoCard}>
            <SectionHeader icon={ShieldCheck} title={t('EligibilityCriteria')} />
            <div style={styles.rulesList}>
                {Array.isArray(scheme.reasons) && scheme.reasons.length > 0 ? (
                    <div style={styles.eligibilityFeedback}>
                        <h5 style={{color: scheme.status === 'Partially Eligible' ? '#d97706' : '#ef4444', marginBottom: '8px', fontSize: '0.9rem'}}>{scheme.status === 'Partially Eligible' ? t('MissingCriteria', 'Missing Criteria:') : t('WhyIneligible', 'You do not qualify because:')}</h5>
                        {scheme.reasons.map((r, i) => (
                            <div key={i} style={{display: 'flex', gap: '8px', alignItems: 'center', color: '#475569', fontSize: '0.9rem'}}>
                                <AlertCircle size={14} color={scheme.status === 'Partially Eligible' ? '#f59e0b' : '#ef4444'} /> {String(r)}
                            </div>
                        ))}
                    </div>
                ) : (
                    <div style={styles.eligibilityFeedback}>
                            <CheckCircle2 size={14} /> {t('Qualified')}
                        </div>
                )}
            </div>
          </div>

          {scheme.benefits && (
            <div style={styles.infoCard}>
              <SectionHeader icon={Sparkles} title={t('SchemeBenefits', 'Benefits')} />
              <p style={styles.modalText}>{scheme.benefits}</p>
            </div>
          )}

          {scheme.steps && (
            <div style={styles.infoCard}>
              <SectionHeader icon={ClipboardList} title={t('HowToApply', 'Steps to Apply')} />
                <div style={styles.stepsFlow}>
                                {formatSteps(scheme.steps).map((step, i) => (
                  <div key={i} style={styles.stepRow}>
                    <div style={styles.stepNum}>{i + 1}</div>
                    <span>{step.trim()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      
      {scheme.official_website && scheme.official_website !== 'NA' && (
        <div style={styles.modalFooter}>
          <a href={formatUrl(scheme.official_website)} target="_blank" rel="noopener noreferrer" style={styles.applyBtn}>
            {t('GoToPortal')} <ExternalLink size={18} />
          </a>
        </div>
      )}
    </div>
  </div>
);

export default EligibilityForm;
