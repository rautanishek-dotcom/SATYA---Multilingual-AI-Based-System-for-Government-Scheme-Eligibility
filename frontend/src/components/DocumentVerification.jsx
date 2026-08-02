import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, CheckCircle, AlertTriangle, XCircle, FileText, User, CreditCard, Wallet, ShieldCheck, ArrowRight, Loader2 } from 'lucide-react';

const DocumentVerification = ({ userId, profileData, onVerificationComplete }) => {
    const { t } = useTranslation();
    const storedUser = JSON.parse(localStorage.getItem('satya_user') || '{}');
    const [loading, setLoading] = useState(false);
    const [verificationStatus, setVerificationStatus] = useState(null);
    const [score, setScore] = useState(0);
    const [mismatches, setMismatches] = useState([]);
    const [files, setFiles] = useState({
        aadhaar: null,
        income: null,
        caste: null
    });
    const [scanResults, setScanResults] = useState([]); // Array of raw logs

    const [internalFormData, setInternalFormData] = useState({
        name: '',
        dob: '',
        income: '',
        category: 'General'
    });

    const activeData = profileData || internalFormData;

    const handleFileChange = (e, type) => {
        setFiles({ ...files, [type]: e.target.files[0] });
    };

    const handleInputChange = (e) => {
        setInternalFormData({ ...internalFormData, [e.target.name]: e.target.value });
    };

    const runVerification = async () => {
        setScanResults([]);
        const isAadhaarPreVerified = window.satya_aadhaar_verified === true;
        
        if (!files.aadhaar && !isAadhaarPreVerified) {
            alert(t('AadhaarMandatoryAlert', "Aadhaar Card is mandatory for identity verification."));
            return;
        }

        const currentUserId = userId || storedUser.id || storedUser._id;
        if (!currentUserId) {
            alert(t('SessionExpiredAlert', "Session expired or User ID missing. Please login again."));
            setLoading(false);
            return;
        }

        setLoading(true);
        try {
            let lastResult = null;
            let mergedFields = {};
            const extractEndpoint = '/api/vault/extract';

            // 1. Upload files to the new clean extraction endpoint
            for (const [type, file] of Object.entries(files)) {
                if (!file) {
                    continue;
                }

                const uploadData = new FormData();
                uploadData.append('file', file);
                uploadData.append('user_id', currentUserId);
                if (type === 'aadhaar') {
                    uploadData.append('force_engine', 'aadhaar_ocr');
                }

                const uploadResponse = await fetch(extractEndpoint, {
                    method: 'POST',
                    body: uploadData
                });

                const uploadResult = await uploadResponse.json();
                if (!uploadResponse.ok) {
                    throw new Error(uploadResult.error || `Upload failed for ${type}`);
                }

                lastResult = uploadResult;

                if (uploadResult.ocr_candidates) {
                    const logs = uploadResult.ocr_candidates.map((candidate) => `${candidate.engine} (${candidate.lang}): ${candidate.text}`);
                    setScanResults(prev => [...prev, ...logs]);
                }

                if (uploadResult.fields) {
                    mergedFields = { ...mergedFields, ...uploadResult.fields };
                    setInternalFormData(prev => ({
                        ...prev,
                        name: uploadResult.fields.name?.value || uploadResult.fields.full_name?.value || prev.name,
                        dob: uploadResult.fields.dob?.value || prev.dob,
                        income: uploadResult.fields.income?.value || prev.income,
                        category: uploadResult.fields.category?.value || prev.category,
                    }));
                }

                if (uploadResult.status) {
                    setScore(uploadResult.confidence || 0);
                    setMismatches(uploadResult.missing_fields || []);
                }
            }

            if (lastResult) {
                setVerificationStatus({ ...lastResult, fields: mergedFields });
                const isSuccess = lastResult.status === 'EXTRACTED';
                onVerificationComplete?.(isSuccess);
            }

        } catch (error) {
            console.error("Verification error:", error);
            alert(`Verification Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'Verified': return '#10b981';
            case 'Partially Verified': return '#f59e0b';
            case 'Rejected': return '#ef4444';
            case 'match': return '#10b981';
            case 'mismatch': return '#ef4444';
            default: return '#6b7280';
        }
    };

    return (
        <div style={styles.container} className="glass-card">
            <div style={styles.header}>
                <ShieldCheck size={28} color="var(--primary-color)" />
                <h3 style={styles.title}>{t('DocumentVerification', 'AI Document Verification')}</h3>
            </div>

            {!verificationStatus ? (
                <div style={styles.formSection}>
                    <p style={styles.instruction}>
                        {t('VerificationInstruction', 'Enter your details exactly as they appear on your documents and upload them for AI verification.')}
                    </p>

                    {/* Show internal form only if profileData is NOT provided externally */}
                    {!profileData && (
                        <div style={styles.internalForm}>
                            <div style={styles.grid}>
                                <div style={styles.inputGroup}>
                                    <label style={styles.inputLabel}>{t('FullName', 'Full Name')}</label>
                                    <input type="text" name="name" value={internalFormData.name} onChange={handleInputChange} style={styles.input} />
                                </div>
                                <div style={styles.inputGroup}>
                                    <label style={styles.inputLabel}>{t('DateOfBirth', 'Date of Birth')}</label>
                                    <input type="date" name="dob" value={internalFormData.dob} onChange={handleInputChange} style={styles.input} />
                                </div>
                                <div style={styles.inputGroup}>
                                    <label style={styles.inputLabel}>{t('Income', 'Annual Income')}</label>
                                    <input type="number" name="income" value={internalFormData.income} onChange={handleInputChange} style={styles.input} />
                                </div>
                                <div style={styles.inputGroup}>
                                    <label style={styles.inputLabel}>{t('Category', 'Category')}</label>
                                    <select name="category" value={internalFormData.category} onChange={handleInputChange} style={styles.input}>
                                        <option value="General">{t('General')}</option>
                                        <option value="OBC">{t('OBC')}</option>
                                        <option value="SC">{t('SC')}</option>
                                        <option value="ST">{t('ST')}</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    )}
                    
                    <div style={styles.uploadGrid}>
                        {window.satya_aadhaar_verified ? (
                            <div style={{...styles.uploadItem, borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.05)'}}>
                                <div style={styles.uploadLabel}>
                                    <ShieldCheck size={20} color="#10b981" />
                                    <span style={{color: '#10b981'}}>{t('AadhaarVerified', 'Aadhaar Verified (QR)')}</span>
                                    <div style={styles.fileName}>{window.satya_aadhaar_data?.name}</div>
                                </div>
                            </div>
                        ) : (
                            <div style={{...styles.uploadItem, borderColor: files.aadhaar ? '#10b981' : '#cbd5e1'}}>
                                <label style={styles.uploadLabel}>
                                    <CreditCard size={20} />
                                    <span>{t('AadhaarCard', 'Aadhaar Card')} *</span>
                                    <input type="file" onChange={(e) => handleFileChange(e, 'aadhaar')} style={styles.fileInput} accept="image/*" />
                                    <div style={styles.fileName}>{files.aadhaar?.name || t('ChooseFile', 'Choose File')}</div>
                                </label>
                            </div>
                        )}
                        <div style={{...styles.uploadItem, borderColor: files.income ? '#10b981' : '#cbd5e1'}}>
                            <label style={styles.uploadLabel}>
                                <Wallet size={20} />
                                <span>{t('IncomeCert', 'Income Certificate')}</span>
                                <input type="file" onChange={(e) => handleFileChange(e, 'income')} style={styles.fileInput} accept="image/*" />
                                <div style={styles.fileName}>{files.income?.name || t('Optional', 'Optional')}</div>
                            </label>
                        </div>
                        <div style={{...styles.uploadItem, borderColor: files.caste ? '#10b981' : '#cbd5e1'}}>
                            <label style={styles.uploadLabel}>
                                <FileText size={20} />
                                <span>{t('CasteCert', 'Caste Certificate')}</span>
                                <input type="file" onChange={(e) => handleFileChange(e, 'caste')} style={styles.fileInput} accept="image/*" />
                                <div style={styles.fileName}>{files.caste?.name || t('Optional', 'Optional')}</div>
                            </label>
                        </div>
                    </div>

                    <button onClick={runVerification} disabled={loading || (!files.aadhaar && !window.satya_aadhaar_verified)} style={{...styles.verifyBtn, opacity: ((!files.aadhaar && !window.satya_aadhaar_verified) || loading) ? 0.6 : 1, position: 'relative', overflow: 'hidden'}}>
                        {loading ? (
                            <><Loader2 size={18} className="animate-spin" /> {t('Processing', 'Scanning Documents...')}</>
                        ) : (
                            <>{t('StartVerification', 'Start Verification')} <ArrowRight size={18} /></>
                        )}
                        {loading && <div className="scan-line-animation"></div>}
                    </button>
                    
                    {loading && (
                        <div style={styles.logBox}>
                            <p style={{fontSize: '0.8rem', color: 'var(--primary-color)', fontWeight: 600, marginBottom: '10px'}}>{t('AIExtraction', 'AI Live Data Extraction')}</p>
                            <div style={styles.logList}>
                                {scanResults.length > 0 ? scanResults.map((line, i) => (
                                    <div key={i} className="log-entry" style={{marginBottom: '4px', opacity: 0, animation: 'fadeIn 0.3s forwards'}}>
                                        <span style={{color: '#10b981', marginRight: '8px'}}>&gt;</span>
                                        {line}
                                    </div>
                                )) : (
                                    <div style={{color: 'var(--text-muted)'}}>{t('WaitInit', 'Initializing neural engine...')}</div>
                                )}
                            </div>
                        </div>
                    )}
                    
                    {(!files.aadhaar && !window.satya_aadhaar_verified) && <p style={styles.helperText}>{t('AadhaarRequiredNote')}</p>}
                </div>
            ) : (
                <div style={styles.resultSection}>
                    <div style={{ ...styles.statusBadge, backgroundColor: getStatusColor(verificationStatus?.status) }}>
                        {verificationStatus?.status === 'EXTRACTED' ? <CheckCircle size={18} /> : verificationStatus?.status === 'Verified' ? <CheckCircle size={18} /> : verificationStatus?.status === 'Partially Verified' ? <AlertTriangle size={18} /> : <XCircle size={18} />}
                        <span>{verificationStatus?.status ? t(verificationStatus.status.replace(/\s/g, ''), verificationStatus.status) : t('Unknown')} ({verificationStatus?.confidence || 0})</span>
                    </div>

                    <div style={styles.summaryCard}>
                        <h4 style={styles.summaryTitle}>{t('ExtractedSummary', 'Extracted Summary')}</h4>
                        <div style={styles.summaryGrid}>
                            <div style={styles.summaryItem}>
                                <div style={{display: 'flex', alignItems: 'center', gap: '5px'}}>
                                    <span style={styles.sumLabel}>{t('Name')}</span>
                                </div>
                                <span style={{...styles.sumValue}}>{verificationStatus?.fields?.name?.value || verificationStatus?.fields?.full_name?.value || t('NotScanned')}</span>
                            </div>
                            <div style={styles.summaryItem}>
                                <div style={{display: 'flex', alignItems: 'center', gap: '5px'}}>
                                    <span style={styles.sumLabel}>{t('DateOfBirth')}</span>
                                </div>
                                <span style={{...styles.sumValue}}>{verificationStatus?.fields?.dob?.value || t('NotScanned')}</span>
                            </div>
                            <div style={styles.summaryItem}>
                                <div style={{display: 'flex', alignItems: 'center', gap: '5px'}}>
                                    <span style={styles.sumLabel}>{t('Income')}</span>
                                </div>
                                <span style={{...styles.sumValue}}>₹{verificationStatus?.fields?.income?.value || '0'}</span>
                            </div>
                            <div style={styles.summaryItem}>
                                <div style={{display: 'flex', alignItems: 'center', gap: '5px'}}>
                                    <span style={styles.sumLabel}>{t('Category')}</span>
                                </div>
                                <span style={{...styles.sumValue}}>{verificationStatus?.fields?.category?.value || t('Not Scanned')}</span>
                            </div>
                        </div>
                    </div>

                    {verificationStatus?.mismatches?.length > 0 && (
                        <div style={styles.errorSection}>
                            <h4 style={styles.errorTitle}>{t('MismatchesFound', 'Mismatches Found')}</h4>
                            <ul style={styles.errorList}>
                                {verificationStatus.mismatches.map((err, i) => (
                                    <li key={i} style={styles.errorItem}><XCircle size={14} /> {err}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {verificationStatus.status === 'Rejected' && (
                        <button onClick={() => setVerificationStatus(null)} style={styles.retryBtn}>
                            {t('RetryVerification', 'Retry with corrected data')}
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};

const styles = {
    container: {
        padding: '24px',
        borderRadius: '20px',
        marginBottom: '20px',
    },
    internalForm: {
        marginBottom: '20px',
        padding: '15px',
        backgroundColor: 'rgba(0,0,0,0.02)',
        borderRadius: '12px',
        border: '1px solid rgba(0,0,0,0.05)'
    },
    grid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '12px'
    },
    inputGroup: {
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
    },
    inputLabel: {
        fontSize: '0.75rem',
        fontWeight: 600,
        color: 'var(--text-muted)'
    },
    input: {
        padding: '10px 12px',
        borderRadius: '8px',
        border: '1px solid #cbd5e1',
        fontSize: '0.85rem',
        outline: 'none',
        backgroundColor: 'white',
        color: '#000'
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '15px'
    },
    title: {
        fontSize: '1.2rem',
        fontWeight: 700,
        margin: 0,
        color: 'var(--text-dark)'
    },
    instruction: {
        fontSize: '0.9rem',
        color: 'var(--text-muted)',
        marginBottom: '20px'
    },
    uploadGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '15px',
        marginBottom: '20px'
    },
    uploadItem: {
        padding: '15px',
        borderRadius: '12px',
        border: '2px dashed #cbd5e1',
        backgroundColor: 'rgba(255, 255, 255, 0.03)',
        cursor: 'pointer',
    },
    uploadLabel: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '8px',
        color: 'var(--text-dark)',
        fontSize: '0.8rem',
        fontWeight: 600,
        cursor: 'pointer'
    },
    fileInput: {
        display: 'none'
    },
    fileName: {
        fontSize: '0.7rem',
        color: 'var(--text-muted)',
        textAlign: 'center'
    },
    verifyBtn: {
        width: '100%',
        padding: '14px',
        borderRadius: '12px',
        backgroundColor: 'var(--primary-color)',
        color: 'white',
        fontSize: '1rem',
        fontWeight: 700,
        border: 'none',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '10px'
    },
    helperText: {
        fontSize: '0.75rem',
        color: '#f59e0b',
        textAlign: 'center',
        marginTop: '10px'
    },
    resultSection: {
        textAlign: 'center'
    },
    statusBadge: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 16px',
        borderRadius: '50px',
        color: 'white',
        fontSize: '0.9rem',
        fontWeight: 700,
        marginBottom: '20px',
        textTransform: 'uppercase'
    },
    summaryCard: {
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        padding: '16px',
        borderRadius: '16px',
        textAlign: 'left',
        marginBottom: '20px'
    },
    summaryTitle: {
        fontSize: '0.9rem',
        fontWeight: 700,
        color: 'var(--text-dark)',
        marginBottom: '10px'
    },
    summaryGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '12px'
    },
    logBox: {
        marginTop: '20px',
        padding: '15px',
        backgroundColor: 'rgba(0,0,0,0.05)',
        borderRadius: '12px',
        textAlign: 'left',
        borderLeft: '3px solid var(--secondary-color)'
    },
    logList: {
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        fontFamily: 'monospace'
    },
    summaryItem: {
        display: 'flex',
        flexDirection: 'column'
    },
    sumLabel: {
        fontSize: '0.7rem',
        color: 'var(--text-muted)',
        marginBottom: '2px'
    },
    sumValue: {
        fontSize: '0.85rem',
        fontWeight: 700,
        color: 'var(--text-dark)'
    },
    errorSection: {
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        padding: '15px',
        borderRadius: '12px',
        textAlign: 'left',
        marginBottom: '15px',
        border: '1px solid rgba(239, 68, 68, 0.2)'
    },
    errorTitle: {
        fontSize: '0.85rem',
        fontWeight: 700,
        color: '#ef4444',
        marginBottom: '5px'
    },
    errorList: {
        listStyle: 'none',
        padding: 0,
        margin: 0
    },
    errorItem: {
        color: '#fca5a5',
        fontSize: '0.8rem',
        marginBottom: '3px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
    },
    retryBtn: {
        padding: '10px 20px',
        borderRadius: '10px',
        backgroundColor: '#475569',
        color: 'white',
        fontSize: '0.85rem',
        fontWeight: 600,
        border: 'none',
        cursor: 'pointer'
    }
};

export default DocumentVerification;
