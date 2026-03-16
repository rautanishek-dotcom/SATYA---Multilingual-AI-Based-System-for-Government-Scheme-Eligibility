import React, { useState, useMemo } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, X, Info } from 'lucide-react';

const DocumentVerification = ({ userId, profileData, onVerificationComplete }) => {
  const [documents, setDocuments] = useState({
    aadhaar: { file: null, status: 'idle', label: 'Aadhaar Card' },
    income: { file: null, status: 'idle', label: 'Income Certificate' },
    caste: { file: null, status: 'idle', label: 'Caste Certificate' },
    farmer: { file: null, status: 'idle', label: 'Farmer Certificate (Optional)' },
  });
  
  const [verificationResult, setVerificationResult] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState(null);

  const GENERIC_ERROR = "Something went wrong during verification. Please ensure your document photos are clear and try again.";

  const handleFileChange = (e, type) => {
    const file = e.target.files?.[0];
    if (file) {
      setDocuments(prev => ({
        ...prev,
        [type]: { ...prev[type], file, status: 'uploaded' }
      }));
      setError(null);
    }
  };

  const uploadAndVerify = async () => {
    setIsVerifying(true);
    setVerificationResult(null);
    setError(null);

    try {
      // 1. Upload each uploaded document
      for (const type in documents) {
        if (documents[type].file) {
          const formData = new FormData();
          formData.append('file', documents[type].file);
          formData.append('doc_type', type);
          formData.append('user_id', userId);

          setDocuments(prev => ({
            ...prev,
            [type]: { ...prev[type], status: 'processing' }
          }));

          const res = await fetch('http://localhost:5000/api/verify/upload', {
            method: 'POST',
            body: formData,
          });
          
          if (res.ok) {
            setDocuments(prev => ({
              ...prev,
              [type]: { ...prev[type], status: 'done' }
            }));
          } else {
             const errorData = await res.json();
             setDocuments(prev => ({
              ...prev,
              [type]: { ...prev[type], status: 'error' }
            }));
            setError(errorData.error || "Document rejection: Invalid image detected.");
            setIsVerifying(false);
            return; 
          }
        }
      }

      // 2. Final verification check
      const verifyRes = await fetch('http://localhost:5000/api/verify/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          profile_data: profileData
        }),
      });

      if (!verifyRes.ok) {
        throw new Error("Verification service temporarily unavailable.");
      }

      const data = await verifyRes.json();
      console.log("Verification Response:", data);
      
      if (!data || !data.status) {
        throw new Error("Invalid response from verification server.");
      }
      
      setVerificationResult(data);
      onVerificationComplete?.(data.status.toLowerCase() === 'verified');
    } catch (err) {
      console.error("Verification error:", err);
      setError(err.message || GENERIC_ERROR);
    } finally {
      setIsVerifying(false);
    }
  };

  const hasFiles = useMemo(() => Object.values(documents).some(d => d.file), [documents]);

  return (
    <div className="glass-card animate-fade-in" style={styles.container}>
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <Info size={20} color="var(--primary-color)" />
            <h3 style={{ fontSize: '1.4rem' }}>Verify Your Profile</h3>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Upload government documents to confirm your details. We use AI to extract and match details safely.
        </p>
      </div>

      <div style={styles.docGrid}>
        {Object.entries(documents).map(([type, doc]) => (
          <div key={type} style={styles.docItem}>
            <div style={styles.docIcon}>
              <FileText size={24} color="var(--primary-color)" />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.label}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {doc.file ? doc.file.name : 'No file uploaded'}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {doc.status === 'done' && <CheckCircle size={20} color="#10b981" />}
              {doc.status === 'processing' && <Loader2 size={20} className="animate-spin" color="var(--primary-color)" />}
              {doc.status === 'error' && <AlertCircle size={20} color="#ef4444" />}
              
              <label style={styles.uploadBtn}>
                <Upload size={16} />
                <input 
                  type="file" 
                  hidden 
                  onChange={(e) => handleFileChange(e, type)} 
                  accept="image/*"
                />
              </label>
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div style={styles.errorBanner}>
            <AlertCircle size={18} /> {error}
        </div>
      )}

      {verificationResult && (
        <div style={{
          ...styles.resultBox,
          backgroundColor: verificationResult.status === 'Verified' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
          border: `1px solid ${verificationResult.status === 'Verified' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '20px' }}>
            {verificationResult.status === 'Verified' ? 
              <CheckCircle color="#10b981" size={28} /> : 
              <AlertCircle color="#ef4444" size={28} />
            }
            <div>
              <strong style={{ 
                color: verificationResult.status === 'Verified' ? '#10b981' : '#ef4444',
                fontSize: '1.2rem',
                display: 'block'
              }}>
                {verificationResult.status === 'Verified' ? 'Verified Successfully' : 'Action Required'}
              </strong>
              <p style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '0.9rem', marginTop: '4px' }}>
                {verificationResult.message || "Please review the matching results below."}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {verificationResult.detailed_results && Object.entries(verificationResult.detailed_results).map(([key, result]) => (
              <div key={key} style={styles.comparisonRow}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                      background: result?.status === 'match' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      padding: '5px', borderRadius: '50%', display: 'flex'
                  }}>
                    {result?.status === 'match' ? <CheckCircle color="#10b981" size={16} /> : <X size={16} color="#ef4444" />}
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{result?.label || key}</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{result?.form_val || 'N/A'}</div>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>In Document</div>
                  <div style={{ 
                    fontSize: '0.85rem', 
                    color: result?.status === 'match' ? '#10b981' : '#ef4444',
                    fontWeight: 600 
                  }}>
                    {result?.doc_val || 'Not Found'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!isVerifying && (!verificationResult || verificationResult.status !== 'Verified') && (
        <button 
          onClick={uploadAndVerify}
          disabled={!hasFiles}
          className="btn-primary"
          style={{ width: '100%', marginTop: '25px', padding: '16px', borderRadius: '12px', fontSize: '1rem', fontWeight: 600 }}
        >
          {verificationResult?.status === 'Failed' ? 'Retry Verification' : 'Verify My Details'}
        </button>
      )}

      {isVerifying && (
        <div style={styles.loadingBox}>
          <Loader2 size={32} className="animate-spin" color="var(--primary-color)" />
          <div style={{ marginTop: '10px', fontWeight: 600 }}>Analyzing Government Marks...</div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '5px' }}>This may take 5-10 seconds for high-security extraction</p>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '25px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },
  header: {
    marginBottom: '20px',
  },
  docGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  docItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
    padding: '12px 15px',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  docIcon: {
    padding: '10px',
    backgroundColor: 'rgba(79, 70, 229, 0.1)',
    borderRadius: '10px',
    display: 'flex',
  },
  uploadBtn: {
    padding: '8px',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '8px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  errorBanner: {
    marginTop: '15px',
    padding: '12px',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    color: '#ef4444',
    borderRadius: '8px',
    fontSize: '0.85rem',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    border: '1px solid rgba(239, 68, 68, 0.2)'
  },
  resultBox: {
    marginTop: '25px',
    padding: '20px',
    borderRadius: '16px',
    backdropFilter: 'blur(10px)',
  },
  comparisonRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 15px',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: '10px',
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  loadingBox: {
    width: '100%',
    marginTop: '25px',
    padding: '30px',
    textAlign: 'center',
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '12px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  }
};

export default DocumentVerification;

