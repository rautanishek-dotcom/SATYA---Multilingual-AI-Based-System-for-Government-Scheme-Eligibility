import React, { useState } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, AlertCircle, Eye, EyeOff } from 'lucide-react';

const API_BASE = 'http://localhost:5000/api/vault';

/**
 * DocumentReviewModal - shows extracted fields for user to verify and confirm.
 *
 * Props:
 *   document   - full backend document object
 *   isOpen     - boolean
 *   onClose    - called when user cancels
 *   onConfirm  - called with (verifiedData, corrections)
 */
export default function DocumentReviewModal({ document, isOpen, onClose, onConfirm }) {
  // Prefer verified_data, fall back to ocr_data, then metadata
  const ocr = document?.ocr_data || document?.metadata || {};
  const verified = document?.verified_data || document?.metadata || {};

  // Build initial form values — try all possible key aliases for name
  const getInitial = () => ({
    owner_name: verified.owner_name || verified.name || verified.full_name || ocr.owner_name || ocr.name || ocr.full_name || '',
    dob:        verified.dob        || ocr.dob        || '',
    gender:     verified.gender     || ocr.gender     || '',
    address:    verified.address    || ocr.address    || '',
  });

  const [formData, setFormData] = useState(getInitial);
  const [corrections, setCorrections] = useState([]);
  const [imgError, setImgError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fieldConfidence = document?.field_confidence || {};
  const confidence = parseFloat(document?.confidence || 0);
  const rawVerificationScore = parseFloat(document?.verification_score ?? document?.confidence ?? 0);
  const hasIdentitySignal = parseFloat(document?.identity_match_score ?? 0) > 0 || Boolean(document?.identity_locked);
  const verificationScore = !hasIdentitySignal && confidence > rawVerificationScore
    ? confidence
    : rawVerificationScore;

  // Re-init form if document changes (new upload opens modal)
  React.useEffect(() => {
    setFormData(getInitial());
    setCorrections([]);
    setImgError(false);
    setSubmitting(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document?._id, document?.document_id]);

  if (!isOpen || !document) return null;

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    const orig = ocr[field] || '';
    if (value !== orig) {
      setCorrections(prev => {
        const exists = prev.find(c => c.field === field);
        if (exists) return prev.map(c => c.field === field ? { ...c, corrected_value: value } : c);
        return [...prev, { field, ocr_value: orig, corrected_value: value, reason: 'User corrected during review' }];
      });
    } else {
      setCorrections(prev => prev.filter(c => c.field !== field));
    }
  };

  const handleConfirm = async () => {
    if (submitting) return;
    setSubmitting(true);
    await onConfirm(formData, corrections);
    setSubmitting(false);
  };

  // Confidence badge config
  let bannerIcon = <CheckCircle2 size={22} />;
  let bannerColor = '#166534';
  let bannerBg = '#dcfce7';
  let bannerTitle = 'Document Ready';
  let bannerMsg = 'Please review the extracted information below, then click Confirm & Save.';

  if (confidence < 75) {
    bannerIcon = <XCircle size={22} />;
    bannerColor = '#991b1b';
    bannerBg = '#fee2e2';
    bannerTitle = 'Low Confidence — Manual Review Required';
    bannerMsg = 'Verification confidence is below 75%. Please verify all fields carefully. You may still save after correcting any errors.';
  } else if (confidence < 90) {
    bannerIcon = <AlertTriangle size={22} />;
    bannerColor = '#9a3412';
    bannerBg = '#ffedd5';
    bannerTitle = 'Review Required';
    bannerMsg = 'Moderate confidence. Please check each field for accuracy before saving.';
  }

  // Fields to show — NO document_number or address per user request
  const displayFields = [
    { key: 'owner_name', label: 'Full Name' },
    { key: 'dob',        label: 'Date of Birth (YYYY-MM-DD)' },
    { key: 'gender',     label: 'Gender' },
  ];

  // Build preview URL — absolute to backend, not Vite proxy
  const docId = document._id || document.document_id;
  const userId = document.user_id;
  const previewUrl = docId && userId
    ? `${API_BASE}/preview/${docId}?user_id=${encodeURIComponent(userId)}`
    : null;

  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(15,23,42,0.45)',
        backdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16, zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff',
          borderRadius: 24,
          padding: 32,
          width: '100%',
          maxWidth: 900,
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 25px 60px rgba(15,23,42,0.22)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24 }}>
          <div style={{ width: 46, height: 46, borderRadius: 16, background: '#fee2e2', color: '#dc2626', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
            <AlertTriangle size={22} />
          </div>
          <div>
            <div style={{ fontSize: 21, fontWeight: 900, color: '#0f172a' }}>Verify Document Information</div>
            <div style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>
              Overall Verification Confidence: <strong>{verificationScore.toFixed(1)}%</strong>
              {' · '}
              {document.document_label || document.document_type || 'Document'}
            </div>
          </div>
        </div>

        {/* Body: two columns */}
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>

          {/* Left: Preview */}
          <div style={{ flex: '0 0 300px', minWidth: 220 }}>
            <div style={{
              background: '#f8fafc', border: '1px solid #e2e8f0',
              borderRadius: 14, padding: 12,
              height: 360, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
            }}>
              {previewUrl && !imgError ? (
                <img
                  src={previewUrl}
                  alt="Document Preview"
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 8 }}
                  onError={() => setImgError(true)}
                />
              ) : (
                <div style={{ color: '#94a3b8', textAlign: 'center', padding: 16 }}>
                  <AlertCircle size={36} style={{ margin: '0 auto 10px', display: 'block' }} />
                  <div style={{ fontSize: 13 }}>Preview not available</div>
                </div>
              )}
            </div>
            <div style={{ textAlign: 'center', marginTop: 8, fontSize: 12, color: '#94a3b8' }}>
              Document stored securely
            </div>
          </div>

          {/* Right: Form */}
          <div style={{ flex: 1, minWidth: 260, display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Confidence banner */}
            <div style={{
              display: 'flex', gap: 12, padding: '14px 16px', borderRadius: 12,
              background: bannerBg, color: bannerColor, alignItems: 'flex-start',
            }}>
              <span style={{ flexShrink: 0, marginTop: 1 }}>{bannerIcon}</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{bannerTitle}</div>
                <div style={{ fontSize: 13, marginTop: 4, lineHeight: 1.5 }}>{bannerMsg}</div>
              </div>
            </div>

            {/* Editable fields */}
            {displayFields.map(({ key, label }) => {
              const conf = fieldConfidence[key];
              const isLow = conf !== undefined && conf < 85;
              const changed = formData[key] !== (ocr[key] || '');
              return (
                <div key={key}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 5 }}>
                    <label style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>{label}</label>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {conf !== undefined && (
                        <span style={{
                          fontSize: 11, fontWeight: 700,
                          color: isLow ? '#dc2626' : '#16a34a',
                          background: isLow ? '#fee2e2' : '#dcfce7',
                          padding: '2px 7px', borderRadius: 4,
                        }}>
                          {conf.toFixed(0)}% Match
                        </span>
                      )}
                      {changed && <span style={{ fontSize: 11, color: '#0ea5e9', fontWeight: 600 }}>Edited</span>}
                    </div>
                  </div>
                  <input
                    type="text"
                    value={formData[key] || ''}
                    placeholder={`Enter ${label}`}
                    onChange={e => handleChange(key, e.target.value)}
                    style={{
                      width: '100%', boxSizing: 'border-box',
                      padding: '10px 13px',
                      border: `1.5px solid ${changed ? '#0ea5e9' : isLow ? '#fca5a5' : '#cbd5e1'}`,
                      borderRadius: 9, fontSize: 14, fontFamily: 'inherit',
                      outline: 'none', background: '#f8fafc',
                      transition: 'border 0.2s',
                    }}
                  />
                </div>
              );
            })}

            {/* Action buttons */}
            <div style={{
              display: 'flex', gap: 12, justifyContent: 'flex-end',
              paddingTop: 16, marginTop: 4,
              borderTop: '1px solid #e2e8f0',
            }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '10px 22px', borderRadius: 10,
                  border: '1.5px solid #cbd5e1', background: '#fff',
                  color: '#334155', fontWeight: 600, fontSize: 14,
                  cursor: 'pointer', transition: 'all 0.15s',
                }}
                onMouseEnter={e => e.target.style.background = '#f1f5f9'}
                onMouseLeave={e => e.target.style.background = '#fff'}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={submitting}
                style={{
                  padding: '10px 22px', borderRadius: 10,
                  border: 'none', background: submitting ? '#93c5fd' : '#2563eb',
                  color: '#fff', fontWeight: 700, fontSize: 14,
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: 8,
                  transition: 'background 0.15s',
                }}
              >
                <CheckCircle2 size={16} />
                {submitting ? 'Saving...' : 'Confirm & Save'}
              </button>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
