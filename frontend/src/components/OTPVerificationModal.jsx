import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle2, XCircle, Loader2, Mail, RefreshCw, X } from 'lucide-react';

export default function OTPVerificationModal({
  isOpen,
  onClose,
  onVerified,
  purpose,
  documentId,
}) {
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [timer, setTimer] = useState(300); // 5 minutes
  const [resendsRemaining, setResendsRemaining] = useState(3);
  const [isResending, setIsResending] = useState(false);

  const inputRefs = useRef([]);

  useEffect(() => {
    if (isOpen) {
      setOtp(['', '', '', '', '', '']);
      setError(null);
      setSuccess(false);
      setTimer(300);
      
      // Auto-focus first input after a tiny delay for modal render
      setTimeout(() => {
        if (inputRefs.current[0]) inputRefs.current[0].focus();
      }, 100);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || success) return;
    
    const interval = setInterval(() => {
      setTimer((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isOpen, success]);

  if (!isOpen) return null;

  const handleResend = async () => {
    if (isResending || resendsRemaining <= 0) return;
    
    setIsResending(true);
    setError(null);
    try {
      const token = localStorage.getItem('satya_token');
      const res = await fetch('http://localhost:5000/api/otp/resend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ purpose, document_id: documentId })
      });
      const data = await res.json();
      
      if (res.ok) {
        setTimer(300); // reset timer
        setResendsRemaining(data.resends_remaining);
        setError({ type: 'success', message: 'New OTP sent to your email.' });
      } else {
        setError({ type: 'error', message: data.error || 'Failed to resend OTP.' });
      }
    } catch {
      setError({ type: 'error', message: 'Network error. Please try again.' });
    } finally {
      setIsResending(false);
    }
  };

  const handleChange = (index, value) => {
    if (!/^[0-9]*$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Auto-next
    if (value && index < 5) {
      inputRefs.current[index + 1].focus();
    }

    // Auto-submit if all filled
    if (value && index === 5 && newOtp.every(d => d !== '')) {
      handleVerify(newOtp.join(''));
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1].focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').slice(0, 6).replace(/[^0-9]/g, '');
    if (pastedData) {
      const newOtp = [...otp];
      for (let i = 0; i < pastedData.length; i++) {
        newOtp[i] = pastedData[i];
      }
      setOtp(newOtp);
      const focusIndex = Math.min(pastedData.length, 5);
      inputRefs.current[focusIndex].focus();
      if (pastedData.length === 6) {
        handleVerify(pastedData);
      }
    }
  };

  const handleVerify = async (code) => {
    const otpCode = code || otp.join('');
    if (otpCode.length !== 6) {
      setError({ type: 'error', message: 'Please enter all 6 digits.' });
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await Promise.resolve(onVerified(otpCode));
      setSuccess(true);
    } catch (err) {
      setError({ type: 'error', message: err?.message || 'Verification failed.' });
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div style={modalStyles.modalOverlay} onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={modalStyles.modalCard}
      >
        <button onClick={onClose} style={modalStyles.closeButton}>
          <X size={20} />
        </button>

        <div style={modalStyles.header}>
          <div style={modalStyles.iconContainer}>
            <Mail size={24} color="#2563eb" />
          </div>
          <h2 style={modalStyles.title}>Email Verification</h2>
          <p style={modalStyles.subtitle}>
            We've sent a 6-digit verification code to your registered email address.
          </p>
        </div>

        {error && (
          <div style={{
            ...modalStyles.errorAlert,
            backgroundColor: error.type === 'success' ? '#dcfce7' : '#fee2e2',
            color: error.type === 'success' ? '#166534' : '#991b1b',
            border: `1px solid ${error.type === 'success' ? '#bbf7d0' : '#fecaca'}`
          }}>
            {error.message}
          </div>
        )}

        <div style={modalStyles.otpContainer}>
          {otp.map((digit, index) => (
            <input
              key={index}
              ref={el => inputRefs.current[index] = el}
              type="text"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              onPaste={handlePaste}
              style={modalStyles.otpInput}
              disabled={loading || success || timer === 0}
            />
          ))}
        </div>

        <div style={modalStyles.footer}>
          <div style={modalStyles.timerText}>
            {timer > 0 ? (
              <span>Code expires in <strong>{formatTime(timer)}</strong></span>
            ) : (
              <span style={{ color: '#dc2626' }}>Code has expired</span>
            )}
          </div>

          <div style={modalStyles.resendContainer}>
            <span style={{ color: '#64748b', fontSize: '13px' }}>Didn't receive code?</span>
            <button 
              onClick={handleResend}
              disabled={isResending || resendsRemaining <= 0 || timer > 270}
              style={{
                ...modalStyles.resendButton,
                opacity: (isResending || resendsRemaining <= 0 || timer > 270) ? 0.5 : 1
              }}
            >
              {isResending ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}
              Resend Code
            </button>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>({resendsRemaining} left)</span>
          </div>
        </div>

        <button
          onClick={() => handleVerify()}
          disabled={loading || success || otp.join('').length !== 6 || timer === 0}
          style={{
            ...modalStyles.verifyButton,
            opacity: (loading || success || otp.join('').length !== 6 || timer === 0) ? 0.7 : 1
          }}
        >
          {loading ? (
            <><Loader2 size={18} className="spin" /> Verifying...</>
          ) : success ? (
            <><CheckCircle2 size={18} /> Verified</>
          ) : (
            'Verify & Continue'
          )}
        </button>

        <style>{`
          .spin { animation: spin 1s linear infinite; }
          @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        `}</style>
      </div>
    </div>
  );
}

const modalStyles = {
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.5)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '16px',
    zIndex: 10000,
  },
  modalCard: {
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '32px',
    width: '100%',
    maxWidth: '440px',
    position: 'relative',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  },
  closeButton: {
    position: 'absolute',
    top: '20px',
    right: '20px',
    background: 'transparent',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '50%',
    transition: 'all 0.2s',
  },
  header: {
    textAlign: 'center',
    marginBottom: '24px',
  },
  iconContainer: {
    width: '48px',
    height: '48px',
    backgroundColor: '#eff6ff',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '20px',
    fontWeight: '700',
    color: '#0f172a',
  },
  subtitle: {
    margin: 0,
    fontSize: '14px',
    color: '#64748b',
    lineHeight: '1.5',
  },
  errorAlert: {
    padding: '12px 16px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '500',
    marginBottom: '20px',
    textAlign: 'center',
  },
  otpContainer: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    marginBottom: '24px',
  },
  otpInput: {
    width: '48px',
    height: '56px',
    fontSize: '24px',
    fontWeight: '700',
    textAlign: 'center',
    border: '1px solid #cbd5e1',
    borderRadius: '12px',
    color: '#1e293b',
    backgroundColor: '#f8fafc',
    outline: 'none',
    transition: 'all 0.2s',
  },
  footer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '24px',
  },
  timerText: {
    fontSize: '14px',
    color: '#475569',
  },
  resendContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  resendButton: {
    background: 'transparent',
    border: 'none',
    color: '#2563eb',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 8px',
    borderRadius: '4px',
  },
  verifyButton: {
    width: '100%',
    padding: '14px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '12px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    transition: 'all 0.2s',
  }
};
