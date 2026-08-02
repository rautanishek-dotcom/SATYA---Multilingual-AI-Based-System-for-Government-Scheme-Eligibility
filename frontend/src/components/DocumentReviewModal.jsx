import React, { useState } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, AlertCircle, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';

/**
 * Renders the review modal when a document has AWAITING_REVIEW status.
 *
 * @param {Object} props
 * @param {Object} props.document - The document object from the backend
 * @param {boolean} props.isOpen - Whether the modal is open
 * @param {Function} props.onClose - Called when user cancels/closes without saving
 * @param {Function} props.onConfirm - Called with (verifiedData, corrections) when user confirms
 */
export default function DocumentReviewModal({ document, isOpen, onClose, onConfirm }) {
  if (!isOpen || !document) return null;

  // Track editable fields. We initialize from document.verified_data or fallback to ocr_data/metadata
  const initialData = document.verified_data || document.metadata || {};
  const [formData, setFormData] = useState({ ...initialData });

  // Track which fields the user actually changed
  const [corrections, setCorrections] = useState([]);

  // The immutable original OCR data for comparison
  const ocrData = document.ocr_data || document.metadata || {};
  
  // Field-level confidence map (if provided by backend)
  const fieldConfidence = document.field_confidence || {};
  
  const confidence = parseFloat(document.confidence || 0);

  const handleFieldChange = (field, newValue) => {
    setFormData((prev) => ({ ...prev, [field]: newValue }));
    
    // Track correction
    const originalValue = ocrData[field] || '';
    if (newValue !== originalValue) {
      setCorrections((prev) => {
        const existing = prev.find(c => c.field === field);
        if (existing) {
          return prev.map(c => c.field === field ? { ...c, corrected_value: newValue } : c);
        } else {
          return [...prev, {
            field,
            ocr_value: originalValue,
            corrected_value: newValue,
            reason: 'User corrected during review',
          }];
        }
      });
    } else {
      // Reverted to original
      setCorrections((prev) => prev.filter(c => c.field !== field));
    }
  };

  const handleConfirm = () => {
    onConfirm(formData, corrections);
  };

  // Determine top-level badge
  let BannerIcon = CheckCircle2;
  let bannerColor = '#166534';
  let bannerBg = '#dcfce7';
  let title = 'Document Accepted';
  let message = 'High confidence extraction. Please review the details below before finalizing.';
  
  if (confidence < 80) {
    BannerIcon = XCircle;
    bannerColor = '#991b1b';
    bannerBg = '#fee2e2';
    title = 'Low Confidence Extraction';
    message = 'OCR confidence is below 80%. This document will be marked as Rejected unless manually verified. We recommend re-uploading a clearer image.';
  } else if (confidence < 95) {
    BannerIcon = AlertTriangle;
    bannerColor = '#9a3412';
    bannerBg = '#ffedd5';
    title = 'Review Required';
    message = 'Moderate confidence extraction. Please carefully review and correct any errors below.';
  }

  // Fields to display in the form
  const displayFields = [
    { key: 'owner_name', label: 'Name' },
    { key: 'document_number', label: 'Document Number' },
    { key: 'dob', label: 'Date of Birth (YYYY-MM-DD)' },
    { key: 'gender', label: 'Gender' },
  ];

  return (
    <Modal
      title="Verify Document Information"
      subtitle={`Overall OCR Confidence: ${confidence.toFixed(1)}%`}
      onClose={onClose}
      width={900} // Wide modal to fit preview side-by-side
    >
      <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
        
        {/* Left Column: Image Preview */}
        <div style={{ flex: '1', minWidth: '350px' }}>
          <div style={{ 
            background: '#f8fafc', 
            border: '1px solid #e2e8f0', 
            borderRadius: '12px', 
            padding: '12px',
            height: '400px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden'
          }}>
            {document.storage_path ? (
               <img 
                 src={`/api/vault/preview/${document._id || document.document_id}?user_id=${encodeURIComponent(document.user_id)}`}
                 alt="Document Preview"
                 style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
               />
            ) : (
               <div style={{ color: '#64748b', textAlign: 'center' }}>
                 <AlertCircle size={32} style={{ margin: '0 auto 12px' }} />
                 <div>Preview not available</div>
               </div>
            )}
          </div>
        </div>

        {/* Right Column: Extracted Data & Form */}
        <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{
            display: 'flex', gap: '12px', padding: '16px', borderRadius: '12px',
            backgroundColor: bannerBg, color: bannerColor, alignItems: 'center'
          }}>
            <BannerIcon size={24} />
            <div>
              <div style={{ fontWeight: 700, fontSize: '15px' }}>{title}</div>
              <div style={{ fontSize: '13px', marginTop: '4px', lineHeight: 1.4 }}>{message}</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {displayFields.map(({ key, label }) => {
              const fieldConf = fieldConfidence[key];
              const isLowConf = fieldConf !== undefined && fieldConf < 85;
              const hasChanged = formData[key] !== (ocrData[key] || '');

              return (
                <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
                      {label}
                    </label>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      {fieldConf !== undefined && (
                        <span style={{ 
                          fontSize: '11px', 
                          fontWeight: 700, 
                          color: isLowConf ? '#dc2626' : '#16a34a',
                          background: isLowConf ? '#fee2e2' : '#dcfce7',
                          padding: '2px 6px',
                          borderRadius: '4px'
                        }}>
                          {fieldConf.toFixed(0)}% Match
                        </span>
                      )}
                      {hasChanged && (
                        <span style={{ fontSize: '11px', color: '#0ea5e9', fontWeight: 600 }}>Edited</span>
                      )}
                    </div>
                  </div>
                  <input
                    type="text"
                    value={formData[key] || ''}
                    onChange={(e) => handleFieldChange(key, e.target.value)}
                    style={{
                      padding: '10px 12px',
                      border: `1px solid ${hasChanged ? '#0ea5e9' : (isLowConf ? '#fca5a5' : '#cbd5e1')}`,
                      borderRadius: '8px',
                      fontSize: '15px',
                      fontFamily: 'inherit',
                      outline: 'none',
                      boxShadow: hasChanged ? '0 0 0 2px rgba(14,165,233,0.1)' : 'none',
                      transition: 'all 0.2s'
                    }}
                  />
                </div>
              );
            })}
          </div>

          <div style={{ marginTop: 'auto', paddingTop: '20px', display: 'flex', gap: '12px', justifyContent: 'flex-end', borderTop: '1px solid #e2e8f0' }}>
            <button
              onClick={onClose}
              style={{
                padding: '10px 20px',
                borderRadius: '8px',
                border: '1px solid #cbd5e1',
                background: 'white',
                color: '#475569',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              style={{
                padding: '10px 20px',
                borderRadius: '8px',
                border: 'none',
                background: '#2563eb',
                color: 'white',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <CheckCircle2 size={18} />
              Confirm & Save
            </button>
          </div>
        </div>

      </div>
    </Modal>
  );
}

function Modal({ title, subtitle, children, onClose, width = 620 }) {
  return (
    <div style={modalStyles.modalOverlay} onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, y: 18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 18, scale: 0.98 }}
        onClick={(e) => e.stopPropagation()}
        style={{ ...modalStyles.modalCard, width, maxWidth: 'calc(100vw - 32px)' }}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 42, height: 42, borderRadius: 14, background: '#fee2e2', color: '#dc2626', display: 'grid', placeItems: 'center' }}>
              <AlertTriangle size={20} />
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>{title}</div>
              {subtitle && <div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>{subtitle}</div>}
            </div>
          </div>
        </div>
        {children}
      </motion.div>
    </div>
  );
}

function Badge({ children, tone = 'slate' }) {
  const colors = {
    slate: { bg: '#e2e8f0', fg: '#334155' },
    blue: { bg: '#dbeafe', fg: '#1d4ed8' },
    green: { bg: '#dcfce7', fg: '#166534' },
    amber: { bg: '#fef3c7', fg: '#92400e' },
    red: { bg: '#fee2e2', fg: '#991b1b' },
    purple: { bg: '#ede9fe', fg: '#6d28d9' },
  }[tone] || { bg: '#e2e8f0', fg: '#334155' };

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '6px 10px',
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 700,
      background: colors.bg,
      color: colors.fg,
      letterSpacing: '0.01em',
    }}>
      {children}
    </span>
  );
}

const modalStyles = {
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(15, 23, 42, 0.4)',
    backdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    zIndex: 9999,
  },
  modalCard: {
    background: '#ffffff',
    borderRadius: 24,
    padding: 32,
    boxShadow: '0 25px 50px -12px rgba(15, 23, 42, 0.25)',
    maxHeight: '90vh',
    overflowY: 'auto',
  },
};
