import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
  Upload, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  User, 
  Calendar, 
  MapPin, 
  ArrowRight,
  ShieldCheck,
  FileText,
  ScanLine
} from 'lucide-react';

const AadhaarScanner = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Upload, 2: Scanning/Extracting, 3: Review
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [extractedData, setExtractedData] = useState({
    name: '',
    dob: '',
    gender: '',
    address: ''
  });

  const maskData = (str, visibleCount = 4) => {
    if (!str) return 'N/A';
    if (str.length <= visibleCount) return str;
    return str.substring(0, visibleCount) + 'x'.repeat(str.length - visibleCount * 2) + str.substring(str.length - visibleCount);
  };

  const user = JSON.parse(localStorage.getItem('satya_user') || '{}');

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (!['image/jpeg', 'image/png', 'application/pdf'].includes(selectedFile.type)) {
        setError("Please upload JPG, PNG or PDF only");
        return;
      }
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setError(null);
    }
  };

  const startScan = async () => {
    if (!file) return;

    setLoading(true);
    setStep(2);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', user.id || user._id);

    try {
      const response = await fetch('http://localhost:5000/api/verify/scan-aadhaar', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (result.status === 'Success') {
        setExtractedData(result.data);
        setStep(3);
      } else {
        setError(result.message || "Failed to scan Aadhaar");
        setStep(1);
      }
    } catch (err) {
      setError("Connection error. Please check your backend.");
      setStep(1);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setLoading(true);
    try {
      // Set ephemeral global variables for the session
      // This ensures if the user hard-refreshes the browser, they will need to rescan
      window.satya_aadhaar_verified = true;
      window.satya_aadhaar_data = extractedData;
      
      // Navigate to the Verify Docs section, carrying the ephemeral state
      navigate('/verify');
    } catch (err) {
      setError("Failed to process profile. " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.outerContainer} className="animate-fade-in">
      <div className="container" style={styles.container}>
        <div className="glass-card" style={styles.card}>
          
          {/* Progress Header */}
          <div style={styles.header}>
            <div style={styles.iconContainer}>
              <ShieldCheck size={32} color="var(--primary-color)" />
            </div>
            <h1 style={styles.title}>{t('ProfileVerificationTitle', 'Profile Verification')}</h1>
            <p style={styles.subtitle}>{t('ProfileVerificationSubtitle', 'Verify your Aadhaar to access government schemes')}</p>
            
            <div style={styles.stepper}>
              <div style={step >= 1 ? styles.stepActive : styles.stepInactive}>1</div>
              <div style={styles.stepLine}></div>
              <div style={step >= 2 ? styles.stepActive : styles.stepInactive}>2</div>
              <div style={styles.stepLine}></div>
              <div style={step >= 3 ? styles.stepActive : styles.stepInactive}>3</div>
            </div>
            <div style={styles.stepLabels}>
              <span>{t('StepUpload', 'Upload')}</span>
              <span>{t('StepScanning', 'Scanning')}</span>
              <span>{t('StepConfirm', 'Confirm')}</span>
            </div>
          </div>

          <hr style={styles.divider} />

          {/* Step 1: Upload */}
          {step === 1 && (
            <div style={styles.content}>
               {error && (
                <div style={styles.errorBox}>
                  <AlertCircle size={20} />
                  <span>{error}</span>
                </div>
              )}

              <div style={styles.uploadArea}>
                {!preview ? (
                  <label style={styles.dropZone}>
                    <Upload size={48} color="var(--text-muted)" />
                    <span style={styles.dropText}>{t('ClickToUpload', 'Click to upload Aadhaar (Front Side)')}</span>
                    <span style={styles.dropSubtext}>{t('UploadFormats', 'JPG, PNG, or PDF supported')}</span>
                    <input type="file" onChange={handleFileChange} style={{ display: 'none' }} accept="image/*,.pdf" />
                  </label>
                ) : (
                  <div style={styles.previewContainer}>
                    <img src={preview} alt="Aadhaar Preview" style={styles.preview} />
                    <button 
                      onClick={() => {setPreview(null); setFile(null);}} 
                      style={styles.removeBtn}
                    >
                      {t('ChangeFile', 'Change File')}
                    </button>
                  </div>
                )}
              </div>

              <div style={styles.instructions}>
                <div style={styles.instructionItem}>
                   <CheckCircle size={16} color="var(--success-color)" />
                   <span>{t('InstructionQR', 'Ensure the QR code is clearly visible')}</span>
                </div>
                <div style={styles.instructionItem}>
                   <CheckCircle size={16} color="var(--success-color)" />
                   <span>{t('InstructionBlurry', 'Avoid glares or blurry images')}</span>
                </div>
                <div style={styles.instructionItem}>
                   <ShieldCheck size={16} color="var(--primary-color)" />
                   <span>{t('InstructionSecure', 'Your data is encrypted and secure')}</span>
                </div>
              </div>

              <button 
                onClick={startScan} 
                disabled={!file || loading}
                className="btn-primary"
                style={styles.mainBtn}
              >
                {loading ? <Loader2 className="animate-spin" /> : <><ScanLine size={20} /> {t('StartAutoExtraction', 'Start Auto-Extraction')}</>}
              </button>
            </div>
          )}

          {/* Step 2: Scanning */}
          {step === 2 && (
            <div style={styles.scanContainer}>
              <div style={styles.scannerAnimation}>
                 <div style={styles.scanLine}></div>
                 {preview && <img src={preview} alt="Scanning" style={styles.scanningImg} />}
              </div>
              <h3 style={{ marginTop: '30px' }}>{t('ExtractingData', 'Extracting Identity Data...')}</h3>
              <p style={{ color: 'var(--text-muted)' }}>{t('ExtractingSubtitle', 'Using AI to decode Aadhaar QR code securely')}</p>
              <div style={styles.loadingDots}>
                <span>.</span><span>.</span><span>.</span>
              </div>
            </div>
          )}

          {/* Step 3: Review & Confirm */}
          {step === 3 && (
            <div style={styles.content}>
               <div style={styles.successHeader}>
                  <div style={styles.successIcon}>
                    <CheckCircle size={40} color="var(--success-color)" />
                  </div>
                  <h3>{t('IdentityVerified', 'Identity Verified!')}</h3>
                  <p>{t('IdentityVerifiedDesc', "We've successfully extracted your details.")}</p>
               </div>

               <div style={styles.profileGrid}>
                  <div style={styles.fieldGroup}>
                    <label><User size={14} /> {t('FullName', 'Full Name')}</label>
                    <input 
                      type="text" 
                      value={extractedData.name} 
                      onChange={(e) => setExtractedData({...extractedData, name: e.target.value})}
                      style={styles.input}
                    />
                  </div>
                  
                  <div style={styles.fieldGroup}>
                    <label><Calendar size={14} /> {t('DateOfBirth', 'Date of Birth')}</label>
                    <input 
                      type="text" 
                      value={extractedData.dob} 
                      onChange={(e) => setExtractedData({...extractedData, dob: e.target.value})}
                      style={styles.input}
                    />
                  </div>

                  <div style={styles.fieldGroup}>
                    <label><User size={14} /> {t('Gender', 'Gender')}</label>
                    <input 
                      type="text" 
                      value={extractedData.gender} 
                      onChange={(e) => setExtractedData({...extractedData, gender: e.target.value})}
                      style={styles.input}
                    />
                  </div>

                  <div style={styles.fieldGroup}>
                    <label><MapPin size={14} /> {t('AddressMasked', 'Address (Masked for privacy)')}</label>
                    <textarea 
                      value={maskData(extractedData.address, 10)} 
                      readOnly
                      style={{...styles.input, height: '80px', resize: 'none', background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.5)'}}
                    />
                    <span style={{fontSize: '0.7rem', color: 'var(--text-muted)'}}>{t('AddressCapturedNote', 'Full address captured for eligibility processing.')}</span>
                  </div>
               </div>

               <div style={styles.infoNote}>
                  <AlertCircle size={16} />
                  <span>{t('VerifyCorrectData', 'Verify and correct data if needed before proceeding.')}</span>
               </div>

               <button 
                onClick={handleConfirm} 
                className="btn-primary"
                style={styles.mainBtn}
              >
                {t('ConfirmContinue', 'Confirm & Continue')} <ArrowRight size={20} />
              </button>
              
              <button 
                onClick={() => setStep(1)} 
                style={styles.secondaryBtn}
              >
                {t('RetakePhoto', 'Retake Photo')}
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

const styles = {
  outerContainer: {
    minHeight: 'calc(100vh - 70px)',
    background: 'radial-gradient(circle at top right, rgba(139, 92, 246, 0.1), transparent), radial-gradient(circle at bottom left, rgba(20, 184, 166, 0.1), transparent)',
    padding: '40px 20px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center'
  },
  container: {
    maxWidth: '600px',
    width: '100%',
  },
  card: {
    padding: '40px',
    textAlign: 'center',
  },
  header: {
    marginBottom: '30px',
  },
  iconContainer: {
    width: '64px',
    height: '64px',
    borderRadius: '50%',
    background: 'rgba(56, 189, 248, 0.1)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    margin: '0 auto 20px',
  },
  title: {
    fontSize: '2rem',
    fontWeight: 800,
    marginBottom: '10px',
    background: 'linear-gradient(to right, #fff, #94a3b8)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  subtitle: {
    color: 'var(--text-muted)',
    fontSize: '1rem',
    marginBottom: '30px',
  },
  stepper: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '10px',
  },
  stepActive: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    background: 'var(--primary-color)',
    color: 'white',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    fontWeight: 'bold',
    fontSize: '0.9rem',
    boxShadow: '0 0 15px rgba(56, 189, 248, 0.5)',
  },
  stepInactive: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    background: 'rgba(255,255,255,0.1)',
    color: 'rgba(255,255,255,0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    fontSize: '0.9rem',
  },
  stepLine: {
    width: '40px',
    height: '2px',
    background: 'rgba(255,255,255,0.1)',
  },
  stepLabels: {
    display: 'flex',
    justifyContent: 'center',
    gap: '30px',
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    paddingLeft: '10px'
  },
  divider: {
    border: 'none',
    borderTop: '1px solid rgba(255,255,255,0.1)',
    margin: '20px 0 30px',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  uploadArea: {
    width: '100%',
  },
  dropZone: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '15px',
    padding: '40px',
    borderRadius: 'var(--border-radius)',
    border: '2px dashed rgba(255,255,255,0.2)',
    background: 'rgba(255,255,255,0.03)',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    ':hover': {
      borderColor: 'var(--primary-color)',
      background: 'rgba(255,255,255,0.05)',
    }
  },
  dropText: {
    fontSize: '1.1rem',
    fontWeight: 600,
  },
  dropSubtext: {
    fontSize: '0.85rem',
    color: 'var(--text-muted)',
  },
  previewContainer: {
    position: 'relative',
    width: '100%',
    borderRadius: 'var(--border-radius)',
    overflow: 'hidden',
  },
  preview: {
    width: '100%',
    maxHeight: '300px',
    objectFit: 'contain',
    background: '#000',
  },
  removeBtn: {
    position: 'absolute',
    bottom: '10px',
    right: '10px',
    background: 'rgba(0,0,0,0.7)',
    color: 'white',
    border: 'none',
    padding: '5px 12px',
    borderRadius: '4px',
    fontSize: '0.8rem',
    cursor: 'pointer'
  },
  instructions: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    textAlign: 'left',
    background: 'rgba(255,255,255,0.03)',
    padding: '20px',
    borderRadius: 'var(--border-radius)',
  },
  instructionItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    fontSize: '0.9rem',
    color: 'var(--text-muted)',
  },
  mainBtn: {
    padding: '16px',
    fontSize: '1.1rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    marginTop: '10px',
  },
  secondaryBtn: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    textDecoration: 'underline',
    fontSize: '0.9rem',
  },
  scanContainer: {
    padding: '40px 0',
  },
  scannerAnimation: {
    position: 'relative',
    width: '100%',
    maxWidth: '450px',
    height: '250px',
    margin: '0 auto',
    overflow: 'hidden',
    border: '2px solid var(--primary-color)',
    borderRadius: '12px',
    background: 'rgba(0,0,0,0.4)',
  },
  scanningImg: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    opacity: 0.8,
  },
  scanLine: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '4px',
    background: 'var(--primary-color)',
    boxShadow: '0 0 15px var(--primary-color)',
    zIndex: 10,
    animation: 'scan 2s infinite ease-in-out',
  },
  loadingDots: {
    fontSize: '2rem',
    display: 'flex',
    justifyContent: 'center',
    gap: '10px',
    marginTop: '10px',
  },
  successHeader: {
    marginBottom: '20px',
  },
  successIcon: {
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    background: 'rgba(16, 185, 129, 0.1)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    margin: '0 auto 15px',
  },
  profileGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '20px',
    textAlign: 'left',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  input: {
    width: '100%',
    padding: '12px',
    borderRadius: '8px',
    background: 'rgba(0,0,0,0.3)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: '#fff',
    fontSize: '0.95rem',
  },
  infoNote: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '0.85rem',
    color: 'var(--info-color)',
    background: 'rgba(14, 165, 233, 0.1)',
    padding: '12px',
    borderRadius: '8px',
    textAlign: 'left',
  },
  errorBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '15px',
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.2)',
    borderRadius: '8px',
    color: 'var(--error-color)',
    fontSize: '0.9rem',
    textAlign: 'left',
  }
};

// Add global scan animation
if (typeof window !== 'undefined') {
  const style = document.createElement('style');
  style.innerHTML = `
    @keyframes scan {
      0% { top: 0; }
      50% { top: 96%; }
      100% { top: 0; }
    }
    .fieldGroup:nth-child(4) {
      grid-column: span 2;
    }
  `;
  document.head.appendChild(style);
}

export default AadhaarScanner;
