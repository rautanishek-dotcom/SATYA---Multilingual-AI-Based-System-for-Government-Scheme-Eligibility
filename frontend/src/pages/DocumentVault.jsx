import React, { useCallback, useEffect, useMemo, useDeferredValue, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Shield, Upload, Search, RefreshCw, ShieldCheck, Lock,
  AlertTriangle, CheckCircle2, XCircle, Clock3, Sparkles, Trash2,
  ChevronRight, BadgeInfo, BadgeAlert, BadgeCheck, Loader2, FileSearch,
  Fingerprint, UserRound, CalendarDays, VenetianMask, FileText
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import DocumentReviewModal from '../components/DocumentReviewModal';
import OTPVerificationModal from '../components/OTPVerificationModal';

const API_BASE = 'http://localhost:5000/api/vault';
const DATE_LOCALE_FALLBACKS = {
  brx: 'as-IN', doi: 'hi-IN', ks: 'ur-PK', kok: 'mr-IN', mai: 'hi-IN', mni: 'bn-IN', sat: 'bn-IN',
};

const formatDate = (value, locale, notAvailableLabel = 'N/A') => {
  if (!value) return notAvailableLabel;
  try {
    const dateLocale = DATE_LOCALE_FALLBACKS[locale] || locale || undefined;
    return new Date(value).toLocaleDateString(dateLocale, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return notAvailableLabel;
  }
};

const displayValue = (value) => {
  if (value === null || value === undefined || value === '') return 'Not Available';
  if (typeof value === 'object') {
    const candidate = value.value ?? value.Value ?? value.text ?? value.Text ?? value.display ?? value.Display;
    return candidate ? String(candidate) : 'Not Available';
  }
  return String(value);
};

const localizeVaultValue = (value, t) => {
  const raw = displayValue(value);
  const normalized = raw.trim().toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ');
  const translations = {
    'not available': 'NotAvailable',
    'n/a': 'NotAvailable',
    male: 'Male',
    female: 'Female',
    verified: 'Verified',
    accepted: 'Accepted',
    rejected: 'Rejected',
    pending: 'Pending',
    'awaiting review': 'AwaitingFinalReview',
    'aadhaar card': 'AadhaarCard',
    'aadhaar ocr': 'AadhaarCard',
    'aadhaar ocr + ai': 'AadhaarIdentityVerificationTitle',
    'caste certificate': 'CasteCert',
    'caste certificate user confirmed ocr': 'CasteCertificateVerification',
    identity: 'IdentityMatchDetails',
    classification: 'DocumentType',
    quality: 'Quality',
    qr: 'QrFraudChecksTitle',
    ocr: 'OcrExtractionValidationTitle',
  };
  const key = translations[normalized];
  return key ? t(key, raw) : raw;
};

const localizeMissingField = (field, t) => {
  const normalized = String(field || '').trim().toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ');
  const keys = {
    'full name': 'FullName',
    dob: 'DateOfBirth',
    'date of birth': 'DateOfBirth',
    gender: 'Gender',
    category: 'Category',
    aadhaar: 'AadhaarCard',
    'aadhaar number': 'AadhaarCard',
    address: 'Address',
    income: 'AnnualIncome',
  };
  return keys[normalized] ? t(keys[normalized], field) : String(field || '');
};

const normalizeIdentityProfile = (profile = {}) => ({
  user_id: displayValue(profile.user_id || profile.userId || ''),
  full_name: displayValue(profile.full_name || profile.fullName || ''),
  dob: displayValue(profile.dob || ''),
  gender: displayValue(profile.gender || ''),
  masked_aadhaar: displayValue(profile.masked_aadhaar || profile.maskedAadhaar || ''),
  aadhaar_reference_id: displayValue(profile.aadhaar_reference_id || profile.aadhaarReferenceId || ''),
  identityLocked: Boolean(profile.identity_locked ?? profile.identityLocked),
  verification_status: displayValue(profile.verification_status || profile.verificationStatus || (profile.identity_locked || profile.identityLocked ? 'Verified' : '')),
  confidence: Number(profile.confidence ?? 0) || 0,
  verified_at: displayValue(profile.verified_at || profile.verifiedAt || ''),
  document_type: displayValue(profile.document_type || profile.documentType || ''),
  verification_method: displayValue(profile.verification_method || profile.verificationMethod || ''),
  last_reset_at: displayValue(profile.last_reset_at || profile.lastResetAt || ''),
  resetAvailable: profile.resetAvailable,
});

const summarizeLogResult = (step, result, t) => {
  if (result === null || result === undefined || result === '') {
    return t('NotAvailable', 'Not Available');
  }
  if (typeof result === 'string') {
    return result.length > 180 ? `${result.slice(0, 177)}...` : result;
  }
  if (Array.isArray(result)) {
    if (!result.length) return t('NotAvailable', 'Not Available');
    const top = result.slice(0, 3).map((item) => {
      if (typeof item === 'string') return item;
      const engine = item.engine || item.verification_engine || item.step || 'item';
      const confidence = item.confidence !== undefined ? `${Math.round(Number(item.confidence) || 0)}%` : '';
      const text = item.text || item.value || item.label || item.message || '';
      return [localizeVaultValue(engine, t), confidence, text].filter(Boolean).join(': ');
    });
    return top.join(' | ');
  }
  if (typeof result === 'object') {
    if (step === 'quality') {
      const score = result.quality_score !== undefined ? `${Math.round(Number(result.quality_score) || 0)}%` : 'n/a';
      const issues = Array.isArray(result.issues) && result.issues.length ? ` - ${result.issues.slice(0, 2).join(', ')}` : '';
      return `${t('Quality', 'Quality')}: ${score}${issues}`;
    }
    if (step === 'classification') {
      return `${localizeVaultValue(result.document_label || result.document_type || 'Document', t)} (${displayValue(result.confidence || 'n/a')}% ${t('Confidence', 'Confidence')})`;
    }
    if (step === 'identity') {
      return `${t('IdentityMatchScore', 'Identity match score')}: ${displayValue(result.score || result.identityMatchScore || 'n/a')}`;
    }
    if (step === 'qr') {
      return `QR: ${result.passed === false ? t('Rejected', 'Rejected') : result.available ? t('Verified', 'Verified') : t('NotAvailable', 'Not Available')}`;
    }
    if (step === 'ocr') {
      const first = result[0] || {};
      return `${localizeVaultValue(first.engine || 'OCR', t)} ${first.confidence !== undefined ? `${Math.round(Number(first.confidence) || 0)}%` : ''}`.trim();
    }
    const entries = Object.entries(result)
      .filter(([key]) => !['raw_text', 'raw_xml', 'candidates', 'sealed_payload'].includes(key))
      .slice(0, 3)
      .map(([key, value]) => `${localizeVaultValue(key.replace(/_/g, ' '), t)}: ${localizeVaultValue(value, t)}`);
    return entries.length ? entries.join(' | ') : t('NotAvailable', 'Not Available');
  }
  return String(result);
};

const getUser = () => {
  try {
    const raw = localStorage.getItem('satya_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const apiFetch = async (path, options = {}) => {
  const token = localStorage.getItem('satya_token');
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(`${API_BASE}${path}`, { ...options, headers, credentials: 'include' });
};

function Badge({ children, tone = 'slate' }) {
  const colors = {
    slate: { bg: '#e2e8f0', fg: '#334155' },
    blue: { bg: '#dbeafe', fg: '#1d4ed8' },
    green: { bg: '#dcfce7', fg: '#166534' },
    amber: { bg: '#fef3c7', fg: '#92400e' },
    red: { bg: '#fee2e2', fg: '#991b1b' },
    purple: { bg: '#ede9fe', fg: '#6d28d9' },
  }[tone];

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

function StatCard({ icon: Icon, label, value, accent, subtext }) {
  return (
    <div style={{
      background: 'rgba(255,255,255,0.85)',
      border: '1px solid rgba(148,163,184,0.15)',
      borderRadius: 24,
      padding: '20px 22px',
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      boxShadow: '0 18px 50px rgba(15,23,42,0.07)',
      backdropFilter: 'blur(16px)',
    }}>
      <div style={{
        width: 52,
        height: 52,
        borderRadius: 18,
        background: `${accent}18`,
        display: 'grid',
        placeItems: 'center',
        color: accent,
        flexShrink: 0,
      }}>
        {Icon && <Icon size={24} />}
      </div>
      <div>
        <div style={{ color: '#64748b', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
        <div style={{ color: '#0f172a', fontSize: 26, fontWeight: 900, lineHeight: 1.1, marginTop: 2 }}>{value}</div>
        {subtext && <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 2 }}>{subtext}</div>}
      </div>
    </div>
  );
}

function LockRow({ icon: Icon, label, labelKey, value }) {
  const { t } = useTranslation();
  const safeLabel = label || '';
  const key = labelKey || safeLabel.replace(/\s/g, '');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0' }}>
      {Icon && <Icon size={15} style={{ color: '#64748b', flexShrink: 0 }} />}
      <span style={{ color: '#64748b', fontSize: 13, minWidth: 130 }}>{t(key, safeLabel)}</span>
      <span style={{ color: '#0f172a', fontSize: 13, fontWeight: 700 }}>{value || t('NotAvailable', 'Not Available')}</span>
    </div>
  );
}


function DocumentCard({ doc, onDelete, onDownload, onPreview }) {
  const { t, i18n } = useTranslation();
  const status = (doc.document_status || doc.verification_status || '').toUpperCase();
  const confidence = Math.round(doc.confidence || 0);
  const qualityScore = Math.round(doc.quality_score || 0);
  const identityMatchScore = Math.round(Number(doc.identity_match_score ?? 0) || 0);
  // Use the actual verification signals: prefer confidence as the primary score
  // since it is the real OCR/verification pipeline result.
  // Only blend in identity match if it exists, otherwise show the confidence directly.
  const verificationScore = identityMatchScore > 0
    ? Math.round((confidence * 0.45 + qualityScore * 0.25 + identityMatchScore * 0.30) / 1.0)
    : confidence;
  const risk = doc.document_summary?.risk || 'low';
  
  const isAccepted = status === 'ACCEPTED';
  const isRejected = status === 'REJECTED';
  const isReview = status === 'AWAITING REVIEW' || status === 'AWAITING_REVIEW';
  
  const tone = isAccepted ? 'green' : isRejected ? 'red' : isReview ? 'amber' : 'slate';
  const statusLabel = isAccepted ? t('Verified', 'Verified') : isRejected ? t('Rejected', 'Rejected') : isReview ? t('AwaitingFinalReview', 'Awaiting final review') : localizeVaultValue(status || 'Pending', t);
  const documentLabel = localizeVaultValue(doc.document_label || doc.document_type || 'Document', t);
  const normalizedRisk = String(risk).toLowerCase();
  const riskKey = normalizedRisk.includes('high') ? 'HighRisk' : normalizedRisk.includes('medium') ? 'MediumRisk' : 'LowRisk';

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.9)',
        border: '1px solid rgba(148,163,184,0.14)',
        borderRadius: 24,
        padding: 18,
        boxShadow: '0 18px 45px rgba(15,23,42,0.08)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
            <Badge tone={tone}>{statusLabel}</Badge>
            <Badge tone="blue">{documentLabel}</Badge>
            <Badge tone={risk === 'high' ? 'red' : risk === 'medium' ? 'amber' : 'green'}>{t(riskKey, riskKey)}</Badge>
          </div>
          <h3 style={{ margin: 0, color: '#0f172a', fontSize: 18, fontWeight: 800, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {doc.document_name || doc.document_label || doc.document_type || 'Vault Document'}
          </h3>
          <div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>
            {t('VerifiedOn', 'Verified on')} {formatDate(doc.created_at, i18n.language, t('NotAvailable', 'N/A'))}
          </div>
        </div>
        <div style={{
          width: 70,
          height: 70,
          borderRadius: '50%',
          border: '8px solid rgba(59,130,246,0.12)',
          display: 'grid',
          placeItems: 'center',
          color: '#0f172a',
          fontWeight: 800,
          fontSize: 16,
          background: 'linear-gradient(135deg, rgba(14,165,233,0.08), rgba(16,185,129,0.08))',
        }}>
          {verificationScore}%
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10, marginTop: 16 }}>
        <MiniStat label={t('Confidence', 'Confidence')} value={`${confidence}%`} />
        <MiniStat label={t('Quality', 'Quality')} value={doc.quality_score ? `${Math.round(doc.quality_score)}%` : t('NotAvailable', 'N/A')} />
      </div>

      <div style={{ marginTop: 14, color: '#334155', fontSize: 13, lineHeight: 1.6 }}>
        {doc.document_summary ? (
          <div>{doc.document_summary.missingFields?.length ? `${t('MissingFields', 'Missing fields')}: ${doc.document_summary.missingFields.map((field) => localizeMissingField(field, t)).join(', ')}` : t('AllFieldsExtracted', 'All required fields were extracted.')}</div>
        ) : (
          <div>{doc.verification_status === 'REJECTED' ? `${t('Rejected', 'Rejected')}: ${t('BlockedForSafety', 'Blocked for safety')}` : t('StoredInVault', 'Stored in the secure vault.')}</div>
        )}
      </div>

      {Array.isArray(doc.verification_logs) && doc.verification_logs.length > 0 && (
        <details style={{ marginTop: 14 }}>
          <summary style={{ cursor: 'pointer', color: '#2563eb', fontSize: 13, fontWeight: 700 }}>
            {t('VerificationTrail', 'View verification history')}
          </summary>
          <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
            {doc.verification_logs.slice(0, 4).map((log, idx) => (
              <div key={idx} style={{ background: '#f8fafc', borderRadius: 12, padding: 10, fontSize: 12, color: '#334155' }}>
                <strong>{localizeVaultValue(log.step, t)}:</strong> {summarizeLogResult(log.step, log.result, t)}
              </div>
            ))}
          </div>
        </details>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
        <div style={{ color: '#64748b', fontSize: 12 }}>
          {t('DocumentHash', 'Document hash')} {doc.hash ? `${String(doc.hash).slice(0, 10)}...` : t('NotAvailable', 'N/A')}
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button type="button" onClick={() => onPreview(doc._id)} style={{ border: 'none', background: 'transparent', color: '#2563eb', fontWeight: 700, cursor: 'pointer' }}>{t('Preview', 'Preview')}</button>
          <button type="button" onClick={() => onDownload(doc._id)} style={{ border: 'none', background: 'transparent', color: '#2563eb', fontWeight: 700, cursor: 'pointer' }}>{t('Download', 'Download')}</button>
          <button
            type="button"
            onClick={() => onDelete(doc._id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              border: 'none',
              background: 'transparent',
              color: '#dc2626',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <Trash2 size={14} /> {t('Delete', 'Delete')}
          </button>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div style={{
      background: '#f8fafc',
      borderRadius: 16,
      padding: '12px 14px',
      border: '1px solid rgba(148,163,184,0.12)',
    }}>
      <div style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {label}
      </div>
      <div style={{ color: '#0f172a', fontSize: 16, fontWeight: 800, marginTop: 4 }}>{value}</div>
    </div>
  );
}


function IdentityLockCard({ identity, resetAvailable, onReset }) {
  const { t, i18n } = useTranslation();
  const locked = identity?.identityLocked;
  const verificationLabel = identity?.verification_method
    ? localizeVaultValue(identity.verification_method, t)
    : locked
      ? t('AadhaarIdentityVerificationTitle', 'Aadhaar Identity Verification')
      : t('NotAvailable', 'Not Available');
  const statusLabel = localizeVaultValue(identity?.verification_status || (locked ? 'Verified' : 'Not Available'), t);
  const documentTypeLabel = localizeVaultValue(identity?.document_type || (locked ? 'Aadhaar Card' : 'Not Available'), t);
  return (
    <div style={{
      background: locked
        ? 'linear-gradient(135deg, rgba(34,197,94,0.12), rgba(14,165,233,0.10))'
        : 'linear-gradient(135deg, rgba(245,158,11,0.14), rgba(239,68,68,0.08))',
      border: `1px solid ${locked ? 'rgba(34,197,94,0.18)' : 'rgba(245,158,11,0.2)'}`,
      borderRadius: 28,
      padding: 24,
      backdropFilter: 'blur(16px)',
      boxShadow: '0 24px 60px rgba(15,23,42,0.10)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{
              width: 46,
              height: 46,
              borderRadius: 16,
              background: locked ? '#16a34a' : '#d97706',
              color: '#fff',
              display: 'grid',
              placeItems: 'center',
            }}>
              <ShieldCheck size={22} />
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>{t('AadhaarCardVerification', 'Aadhaar Card Verification')}</div>
              <div style={{ color: '#334155', fontSize: 13 }}>
                {locked ? t('VerifiedIdentityLocked', 'Verified identity is locked to this account') : t('AadhaarVerificationRequired', 'Aadhaar verification is required to unlock the vault')}
              </div>
            </div>
          </div>
          {locked ? (
            <div style={{ display: 'grid', gap: 8, color: '#0f172a' }}>
              <LockRow icon={UserRound} label="Full Name" labelKey="FullName" value={displayValue(identity?.full_name)} />
              <LockRow icon={CalendarDays} label="Date of Birth" labelKey="DateOfBirth" value={formatDate(identity?.dob, i18n.language, t('NotAvailable', 'Not Available'))} />
              <LockRow icon={VenetianMask} label="Gender" labelKey="Gender" value={localizeVaultValue(identity?.gender, t)} />
              <LockRow icon={Shield} label="Verification Status" labelKey="VerificationStatus" value={statusLabel} />
              <LockRow icon={Sparkles} label="Confidence" labelKey="Confidence" value={identity?.confidence ? `${Math.round(identity.confidence)}%` : t('NotAvailable', 'Not Available')} />
              <LockRow icon={Clock3} label="Verification Date" labelKey="VerificationDate" value={formatDate(identity?.verified_at, i18n.language, t('NotAvailable', 'Not Available'))} />
              <LockRow icon={FileSearch} label="Document Type" labelKey="DocumentType" value={documentTypeLabel} />
              <LockRow icon={BadgeCheck} label="Verification Method" labelKey="VerificationMethod" value={verificationLabel} />
            </div>
          ) : (
            <div style={{ marginTop: 10, maxWidth: 680 }}>
              <p style={{ color: '#1f2937', margin: 0, lineHeight: 1.7 }}>
                {t('UploadVerifyAadhaarFirstNote', 'Upload and verify your Aadhaar first. SATYA will then create a permanent Identity Lock for this account.')}
              </p>
              <p style={{ color: '#7c2d12', marginTop: 12, lineHeight: 1.7, fontSize: 13 }}>
                {t('GovtDisclaimerNote', 'SATYA is not affiliated with any government agency and does not replace official government verification.')}
              </p>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
          <Badge tone={locked ? 'green' : 'amber'}>
            {locked ? t('IdentityVerified', 'Identity verified') : t('Pending', 'Pending')}
          </Badge>
          <button
            type="button"
            disabled={!locked}
            onClick={onReset}
            style={{
              border: 'none',
              borderRadius: 14,
              padding: '12px 16px',
              cursor: !locked ? 'not-allowed' : 'pointer',
              background: !locked ? '#cbd5e1' : '#0f172a',
              color: '#fff',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            {t('ResetIdentity', 'Reset Identity')}
            <ChevronRight size={16} />
          </button>
          {!resetAvailable && <div style={{ color: '#7c2d12', fontSize: 12 }}>{t('ResetCooldownActive', 'Reset cooldown is active.')}</div>}
        </div>
      </div>
    </div>
  );
}

function CasteIdentityLockCard({ casteLocked, casteProfile, casteDocument, onReset }) {
  const { t, i18n } = useTranslation();
  const confidenceLabel = casteProfile?.confidence ? `${Math.round(casteProfile.confidence)}%` : t('NotAvailable', 'Not Available');
  const statusLabel = localizeVaultValue(casteProfile?.verification_status || (casteLocked ? 'Verified' : 'Pending'), t);
  const documentTypeLabel = localizeVaultValue(casteProfile?.document_type || (casteLocked ? 'Caste Certificate' : 'Not Available'), t);
  const verificationLabel = localizeVaultValue(casteProfile?.verification_method || (casteLocked ? 'Caste Certificate User Confirmed OCR' : 'Not Available'), t);

  return (
    <div style={{
      background: casteLocked
        ? 'linear-gradient(135deg, rgba(34,197,94,0.12), rgba(14,165,233,0.10))'
        : 'linear-gradient(135deg, rgba(245,158,11,0.14), rgba(239,68,68,0.08))',
      border: `1px solid ${casteLocked ? 'rgba(34,197,94,0.18)' : 'rgba(245,158,11,0.2)'}`,
      borderRadius: 28,
      padding: 24,
      backdropFilter: 'blur(16px)',
      boxShadow: '0 24px 60px rgba(15,23,42,0.10)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{
              width: 46,
              height: 46,
              borderRadius: 16,
              background: casteLocked ? '#16a34a' : '#d97706',
              color: '#fff',
              display: 'grid',
              placeItems: 'center',
            }}>
              <ShieldCheck size={22} />
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>{t('CasteCategoryVerification', 'Caste Category Verification')}</div>
              <div style={{ color: '#334155', fontSize: 13 }}>
                {casteLocked ? t('VerifiedCasteCategoryLocked', 'Verified caste category is locked to this account') : t('CasteVerificationRequired', 'Caste Certificate verification is required for scheme reservation')}
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gap: 8, color: '#0f172a' }}>
            <LockRow icon={UserRound} label="Full Name" labelKey="FullName" value={displayValue(casteProfile?.name)} />
            <LockRow icon={Sparkles} label="Category" labelKey="Category" value={displayValue(casteProfile?.category)} />
            <LockRow icon={Shield} label="Verification Status" labelKey="VerificationStatus" value={statusLabel} />
            <LockRow icon={Sparkles} label="Confidence" labelKey="Confidence" value={confidenceLabel} />
            <LockRow icon={Clock3} label="Verification Date" labelKey="VerificationDate" value={formatDate(casteProfile?.verification_date || casteDocument?.created_at, i18n.language, t('NotAvailable', 'Not Available'))} />
            <LockRow icon={FileSearch} label="Document Type" labelKey="DocumentType" value={documentTypeLabel} />
            <LockRow icon={BadgeCheck} label="Verification Method" labelKey="VerificationMethod" value={verificationLabel} />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
          <Badge tone={casteLocked ? 'green' : 'amber'}>
            {casteLocked ? t('IdentityVerified', 'Identity verified') : t('Pending', 'Pending')}
          </Badge>
          <button
            type="button"
            disabled={!casteLocked}
            onClick={onReset}
            style={{
              border: 'none',
              borderRadius: 14,
              padding: '12px 16px',
              cursor: !casteLocked ? 'not-allowed' : 'pointer',
              background: !casteLocked ? '#cbd5e1' : '#0f172a',
              color: '#fff',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            {t('ResetCasteIdentity', 'Reset Caste Identity')}
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function Modal({ title, subtitle, children, onClose, width = 620 }) {
  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{ ...styles.modalCard, width, maxWidth: 'calc(100vw - 32px)' }}>
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
      </div>
    </div>
  );
}

export default function DocumentVault() {
  const { t } = useTranslation();
  const user = useMemo(() => getUser(), []);
  const userId = user?.id || user?._id || '';
  const navigate = useNavigate();

  const [documents, setDocuments] = useState([]);
  const [identity, setIdentity] = useState({ identityLocked: false, resetAvailable: true });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [stage, setStage] = useState('idle');
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);
  const [pendingUpload, setPendingUpload] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [reviewDoc, setReviewDoc] = useState(null); // New state for review modal
  const [vaultUnlocked, setVaultUnlocked] = useState(false);
  const [vaultVerificationStatus, setVaultVerificationStatus] = useState('checking');
  const [otpBooting, setOtpBooting] = useState(true);
  const [otpSending, setOtpSending] = useState(false);
  const [otpBanner, setOtpBanner] = useState('');
  
  // OTP State for document review confirmation
  const [showOTPModal, setShowOTPModal] = useState(false);
  const [pendingReviewData, setPendingReviewData] = useState(null);
  const [banner, setBanner] = useState(null);
  const [error, setError] = useState(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetPassword, setResetPassword] = useState('');
  const [resetBusy, setResetBusy] = useState(false);

  // Caste Category Verification State
  const [casteStatus, setCasteStatus] = useState({ caste_locked: false });
  const [casteProfile, setCasteProfile] = useState(null);
  const [casteDocument, setCasteDocument] = useState(null);
  const [casteUploading, setCasteUploading] = useState(false);
  const [casteResetOpen, setCasteResetOpen] = useState(false);
  const [casteResetPassword, setCasteResetPassword] = useState('');
  const [casteResetBusy, setCasteResetBusy] = useState(false);

  const fetchCasteStatus = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await apiFetch(`/caste_status?user_id=${encodeURIComponent(userId)}`);
      const data = await res.json();
      if (res.ok) {
        setCasteStatus(data);
        setCasteProfile(data.caste_profile || null);
        setCasteDocument(data.caste_document || null);
      }
    } catch {
      // Silently handle caste status errors
    }
  }, [userId]);

  const [casteStage, setCasteStage] = useState('idle');

  const handleCasteUpload = async (file) => {
    if (!userId || casteUploading) return;
    setCasteUploading(true);
    setCasteStage('uploading');
    setError(null);
    setBanner(null);

    const timeline = ['uploading', 'ocr', 'matching', 'fraud', 'saving'];
    let idx = 0;
    const interval = setInterval(() => {
      idx = Math.min(idx + 1, timeline.length - 1);
      setCasteStage(timeline[idx]);
    }, 600);

    try {
      const formData = new FormData();
      formData.append('user_id', userId);
      formData.append('file', file);
      const res = await apiFetch('/verify_caste', { method: 'POST', body: formData });
      const data = await res.json();
      clearInterval(interval);
      setCasteStage('idle');

      if (res.ok && data.document_id) {
        // Fetch fresh document and open Review Modal so user can confirm/edit fields
        const docRes = await apiFetch(`/documents?user_id=${encodeURIComponent(userId)}`);
        const docData = await docRes.json().catch(() => ({}));
        const freshDoc = (docData.documents || []).find(d => String(d._id) === String(data.document_id)) || {
          _id: data.document_id,
          document_id: data.document_id,
          user_id: userId,
          document_type: 'caste_certificate',
          document_label: 'Caste Certificate',
          confidence: data.confidence || 94.0,
          verified_data: { category: data.category, name: data.profile?.full_name || '' },
          ocr_data: { category: data.category, name: data.profile?.full_name || '' }
        };
        setReviewDoc({ document_id: data.document_id, document: freshDoc });
        await Promise.all([fetchCasteStatus(), fetchVault(query, true)]);
      } else {
        setError({ title: 'Caste Verification Failed', message: data.error || data.message || 'Could not verify Caste Certificate.' });
      }
    } catch {
      clearInterval(interval);
      setCasteStage('idle');
      setError({ title: 'Upload Failed', message: 'Could not reach server to verify Caste Certificate.' });
    } finally {
      setCasteUploading(false);
      setCasteStage('idle');
    }
  };

  const handleCasteReset = async () => {
    if (!userId) return;
    setCasteResetBusy(true);
    try {
      const res = await apiFetch('/reset_caste_lock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          password: casteResetPassword,
          reason: 'User Requested',
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setCasteResetOpen(false);
        setCasteResetPassword('');
        setBanner({ tone: 'green', title: 'Caste Identity Reset', message: data.message });
        setCasteStatus({ caste_locked: false });
        setCasteProfile(null);
        setCasteDocument(null);
        await Promise.all([fetchCasteStatus(), fetchVault(query, true)]);
      } else {
        setError({ title: 'Reset failed', message: data.error || 'Could not reset caste identity lock.' });
      }
    } catch {
      setError({ title: 'Reset failed', message: 'Could not reach the server.' });
    } finally {
      setCasteResetBusy(false);
    }
  };

  const fetchOtpStatus = useCallback(async () => {
    const token = localStorage.getItem('satya_token');
    const res = await fetch('http://localhost:5000/api/otp/status?purpose=document_verification', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || 'Could not check vault verification status.');
    }
    return data;
  }, []);

  const requestVaultOtp = useCallback(async () => {
    if (!userId) return false;
    setOtpSending(true);
    setError(null);
    try {
      const status = await fetchOtpStatus();
      if (status.verified) {
        setVaultUnlocked(true);
        setVaultVerificationStatus('verified');
        setShowOTPModal(false);
        setOtpBanner('Vault verification already completed for this session.');
        return true;
      }

      if (status.active && !status.verified) {
        setShowOTPModal(true);
        setOtpBanner('A verification code is already active for this session.');
        return true;
      }

      const token = localStorage.getItem('satya_token');
      const res = await fetch('http://localhost:5000/api/otp/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ purpose: 'document_verification' }),
        credentials: 'include',
      });
      const data = await res.json().catch(() => ({}));

      if (res.ok) {
        setShowOTPModal(true);
        setOtpBanner(data.message || `OTP sent to ${data.masked_email || 'your registered email'}.`);
        return true;
      }

      if (data.already_verified) {
        setVaultUnlocked(true);
        setVaultVerificationStatus('verified');
        setShowOTPModal(false);
        setOtpBanner(data.message || 'Vault verification already completed for this session.');
        return true;
      }

      if (data.already_pending) {
        setShowOTPModal(true);
        setOtpBanner(data.message || 'A verification code is already active for this session.');
        return true;
      }

      throw new Error(data.error || 'Could not send OTP.');
    } finally {
      setOtpSending(false);
      setOtpBooting(false);
    }
  }, [fetchOtpStatus, userId]);

  const fetchIdentity = useCallback(async (force = false) => {
    if (!userId) return;
    try {
      const res = await apiFetch(`/identity?user_id=${encodeURIComponent(userId)}`);
      const data = await res.json();
      if (res.ok) {
        setIdentity(normalizeIdentityProfile({
          ...(data.identityProfile || {}),
          identity_locked: data.identityLocked,
          identityLocked: data.identityLocked,
          resetAvailable: data.resetAvailable,
          lastResetAt: data.lastResetAt,
          nextResetAllowedAt: data.nextResetAllowedAt,
        }));
      }
    } catch (err) {
      // Silently fail on identity fetch errors
    }
  }, [userId]);

  const fetchVault = useCallback(async (search = '', force = false) => {
    if (!userId || (!vaultUnlocked && !force)) return;
    setLoading(true);
    try {
      const path = search ? `/search?user_id=${encodeURIComponent(userId)}&q=${encodeURIComponent(search)}` : `/?user_id=${encodeURIComponent(userId)}`;
      const res = await apiFetch(path);
      const data = await res.json();
      if (res.ok) {
        setDocuments(data.documents || []);
        if (data.identity_profile || data.identity_locked !== undefined) {
          setIdentity((prev) => normalizeIdentityProfile({
            ...prev,
            ...(data.identity_profile || {}),
            identity_locked: data.identity_locked ?? prev.identityLocked,
            identityLocked: data.identity_locked ?? prev.identityLocked,
          }));
        }
      } else {
        setError({ title: 'Vault load failed', message: data.error || 'Could not load your vault.' });
      }
    } catch (err) {
      setError({ title: 'Vault load failed', message: 'Could not reach the server.' });
    }
    setLoading(false);
  }, [userId, vaultUnlocked]);

  const handleVaultOTPVerified = useCallback(async (otpCode) => {
    if (!userId) return;
    setOtpSending(true);
    setError(null);
    try {
      const token = localStorage.getItem('satya_token');
      const res = await fetch('http://localhost:5000/api/otp/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ purpose: 'document_verification', otp_code: otpCode }),
        credentials: 'include',
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.verified) {
        throw new Error(data.error || 'OTP verification failed.');
      }

      setVaultUnlocked(true);
      setVaultVerificationStatus('verified');
      setShowOTPModal(false);
      setOtpBanner('Vault unlocked successfully.');
      await Promise.all([fetchIdentity(true), fetchVault('', true)]);
    } catch (err) {
      setError({ title: 'OTP verification failed', message: err.message || 'Could not verify OTP.' });
      throw err;
    } finally {
      setOtpSending(false);
    }
  }, [fetchIdentity, fetchVault, userId]);

  useEffect(() => {
    let active = true;
    const boot = async () => {
      if (!userId) {
        setLoading(false);
        setOtpBooting(false);
        return;
      }
      try {
        await fetchIdentity(true);
        await fetchCasteStatus();
        const status = await fetchOtpStatus();
        if (!active) return;
        if (status.verified) {
          setVaultUnlocked(true);
          setVaultVerificationStatus('verified');
          await Promise.all([fetchIdentity(true), fetchCasteStatus(), fetchVault('', true)]);
        } else {
          setVaultUnlocked(false);
          setVaultVerificationStatus('required');
          await requestVaultOtp();
        }
      } catch (err) {
        if (active) {
          setVaultVerificationStatus('required');
          setError({ title: 'OTP required', message: err.message || 'Could not verify vault access.' });
        }
      } finally {
        if (active) {
          setOtpBooting(false);
          if (!vaultUnlocked) setLoading(false);
        }
      }
      if (!active) return;
    };
    boot();
    return () => {
      active = false;
    };
  }, [userId, fetchIdentity, fetchCasteStatus, fetchVault, fetchOtpStatus, requestVaultOtp]);

  useEffect(() => {
    if (!userId || !vaultUnlocked) return undefined;
    const timer = setTimeout(() => {
      fetchVault(deferredQuery.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [deferredQuery, userId, vaultUnlocked, fetchVault]);

  const handleUpload = async (file, confirm_match = false) => {
    if (!file || uploading) return;
    setUploading(true);
    setError(null);
    setBanner(null);
    const timeline = ['uploading', 'ocr', 'matching', 'fraud', 'saving'];
    let idx = 0;
    const interval = setInterval(() => {
      idx = Math.min(idx + 1, timeline.length - 1);
      setStage(timeline[idx]);
    }, 600);

    try {
      const formData = new FormData();
      formData.append('user_id', userId);
      formData.append('file', file);
      if (confirm_match) formData.append('confirm_match', 'true');

      const res = await apiFetch('/upload', { method: 'POST', body: formData });
      const data = await res.json();
      clearInterval(interval);

      if (data.status === 'CONFIRMATION_REQUIRED') {
        setPendingUpload({ file });
        setConfirmation({
          title: 'Confirm Document Ownership',
          message: data.message || 'Please confirm the extracted details to continue.',
          details: data.extracted || {},
          score: data.identityMatchScore || 0,
        });
        setUploading(false);
        setStage('idle');
        return;
      }

      if (data.status === 'AWAITING_REVIEW') {
        // Pop the review modal
        setReviewDoc(data);
        setUploading(false);
        setStage('idle');
        return;
      }

      if (!res.ok || data.status === 'FAILED' || data.status === 'REJECTED') {
        setError({
          title: data.reason === 'Identity Mismatch' ? 'Identity Verification Failed' : 'Document Rejected',
          message: data.message || data.error || 'The uploaded document could not be verified.',
        });
        setUploading(false);
        setStage('idle');
        return;
      }

      setBanner({
        tone: 'green',
        title: 'Document Accepted',
        message: `${data.document?.document_label || data.classification?.document_label || 'Document'} added to your secure vault.`,
      });
      await Promise.all([fetchVault(query), fetchIdentity(), fetchCasteStatus()]);
      setUploading(false);
      setStage('idle');
    } catch (err) {
      clearInterval(interval);
      setUploading(false);
      setStage('idle');
      setError({
        title: 'Upload failed',
        message: err.message?.includes('fetch') ? 'The backend server is not reachable.' : err.message || 'Something went wrong.',
      });
    }
  };

  const confirmPendingUpload = async () => {
    if (!pendingUpload) return;
    const file = pendingUpload.file;
    setPendingUpload(null);
    setConfirmation(null);
    await handleUpload(file, true);
  };

  const handleReviewConfirm = async (verifiedData, corrections) => {
    if (!reviewDoc) return;

    try {
      const reviewDocumentId = reviewDoc.document_id || reviewDoc.document?._id || reviewDoc.document?._id?.$oid || reviewDoc.document?.id;
      const isCasteDoc = reviewDoc.document?.document_type === 'caste_certificate' || reviewDoc.document?.document_label === 'Caste Certificate' || Boolean(reviewDoc.document?.caste_category);
      const endpoint = isCasteDoc ? '/confirm_caste_review' : '/confirm_review';

      const res = await apiFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          document_id: reviewDocumentId,
          verified_data: verifiedData,
          corrections: corrections,
        }),
      });
      const raw = await res.text();
      let data = {};
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        data = { error: raw || 'Could not save review.' };
      }
      if (res.ok) {
        if (isCasteDoc) {
          if (data.caste_profile) setCasteProfile(data.caste_profile);
          setCasteStatus({ caste_locked: Boolean(data.locked) });
        } else if (data.identity_profile || data.identity_locked !== undefined) {
          setIdentity((prev) => normalizeIdentityProfile({
            ...prev,
            ...(data.identity_profile || {}),
            identity_locked: data.identity_locked ?? prev.identityLocked,
            identityLocked: data.identity_locked ?? prev.identityLocked,
          }));
        }
        setReviewDoc(null);
        setBanner({
          tone: 'green',
          title: isCasteDoc ? 'Caste Certificate Verified' : `Document ${data.document_status || 'Saved'}`,
          message: data.message || 'Document reviewed and saved successfully.',
        });
        await Promise.all([fetchVault(query, true), fetchIdentity(true), fetchCasteStatus()]);
      } else {
        setError({ title: 'Verification Failed', message: data.error || 'Could not save review.' });
      }
    } catch {
      setError({ title: 'Verification Failed', message: 'Could not reach server to save review.' });
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm(`${t('Delete', 'Delete')} ${t('VaultDocument', 'Vault document')}?`)) return;
    const res = await apiFetch(`/${docId}?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' });
    if (res.ok) {
      setBanner({ tone: 'green', title: 'Deleted', message: 'The document was removed from your vault.' });
      await Promise.all([fetchVault(query, true), fetchIdentity(true), fetchCasteStatus()]);
    } else {
      const data = await res.json().catch(() => ({}));
      setError({ title: 'Delete failed', message: data.error || 'Could not delete the document.' });
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchIdentity(true), fetchVault(query, true)]);
    setRefreshing(false);
  };

  const handleReset = async () => {
    setResetBusy(true);
    try {
      const res = await apiFetch('/identity/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          password: resetPassword,
          reason: 'User Requested',
          device: navigator.userAgent,
          ipAddress: '',
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setResetOpen(false);
        setResetPassword('');
        setBanner({ tone: 'green', title: 'Identity successfully reset', message: data.message });
        setIdentity({ identityLocked: false, resetAvailable: true, confidence: 0 });
        setDocuments([]);
        await Promise.all([fetchIdentity(true), fetchVault('', true)]);
      } else {
        setError({ title: 'Reset failed', message: data.error || 'Could not reset identity lock.' });
      }
    } catch {
      setError({ title: 'Reset failed', message: 'Could not reach the server.' });
    } finally {
      setResetBusy(false);
    }
  };

  const acceptedCount = documents.filter((d) => (d.document_status || d.verification_status || '').toUpperCase() === 'ACCEPTED').length;
  const rejectedCount = documents.filter((d) => (d.document_status || d.verification_status || '').toUpperCase() === 'REJECTED').length;
  const pendingCount = documents.length - acceptedCount - rejectedCount;
  const avgConfidence = documents.length
    ? Math.round(documents.reduce((acc, doc) => acc + (doc.confidence || 0), 0) / documents.length)
    : 0;

  if (!userId) {
    return (
      <div style={styles.shell}>
        <div style={styles.heroBackdrop} />
        <div style={styles.contentWrap}>
          <div style={styles.emptyState}>
            <Lock size={36} />
            <h1 style={{ margin: '18px 0 8px', fontSize: 28, fontWeight: 900 }}>{t('VaultLoginRequired', 'Secure Vault Login Required')}</h1>
            <p style={{ margin: 0, color: '#475569', lineHeight: 1.7 }}>
              {t('VaultLoginRequiredDesc', 'Please sign in to access your SATYA Document Vault.')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (vaultVerificationStatus === 'checking') {
    return (
      <div style={styles.shell}>
        <div style={styles.heroBackdrop} />
        <div style={styles.contentWrap}>
          <div style={{ ...styles.emptyState, minHeight: 420, marginTop: 36 }}>
            <Loader2 size={40} className="spin" color="#2563eb" />
            <h2 style={{ margin: '18px 0 8px', fontSize: 28, fontWeight: 950, color: '#0f172a' }}>
              {t('LoadingVault', 'Loading Document Vault...')}
            </h2>
          </div>
        </div>
        <style>{`
          .spin { animation: spin 1s linear infinite; }
          @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  if (!vaultUnlocked) {
    return (
      <div style={styles.shell}>
        <div style={styles.heroBackdrop} />
        <div style={styles.contentWrap}>
          <div style={styles.header}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
                <div style={styles.brandMark}>
                  <ShieldCheck size={24} />
                </div>
                <Badge tone="blue">{t('SATYASecureVault', 'SATYA Secure Vault')}</Badge>
                <Badge tone="amber">{t('OTPProtected', 'OTP protected')}</Badge>
              </div>
              <h1 style={styles.title}>{t('UnlockVaultTitle', 'Unlock your Document Vault')}</h1>
              <p style={styles.subtitle}>
                {t('UnlockVaultDesc', 'A one-time password will be sent to your registered Gmail address before the vault contents are revealed.')}
              </p>
            </div>
          </div>

          <div style={{ ...styles.emptyState, minHeight: 420, marginTop: 36 }}>
            <div style={{
              width: 92,
              height: 92,
              borderRadius: 28,
              display: 'grid',
              placeItems: 'center',
              background: 'linear-gradient(135deg, rgba(37,99,235,0.12), rgba(16,185,129,0.12))',
              color: '#2563eb',
              marginBottom: 18,
            }}>
              <Lock size={40} />
            </div>
            <h2 style={{ margin: '0 0 10px', fontSize: 28, fontWeight: 950, color: '#0f172a' }}>
              {otpBooting ? t('CheckingVerification', 'Checking shared verification...') : t('VaultLocked', 'Vault locked')}
            </h2>
            <p style={{ maxWidth: 680, margin: 0, color: '#475569', lineHeight: 1.8, textAlign: 'center' }}>
              {otpBanner || t('VaultOTPNote', 'To access the vault, verify the shared OTP session first. The same verification will also be reused by Check Eligibility.')}
            </p>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center', marginTop: 22 }}>
              <button
                type="button"
                onClick={requestVaultOtp}
                disabled={otpSending || otpBooting}
                style={{
                  ...styles.primaryBtn,
                  opacity: (otpSending || otpBooting) ? 0.7 : 1,
                }}
              >
                {otpSending ? <Loader2 size={18} className="spin" /> : <ShieldCheck size={18} />}
                {otpSending ? t('SendingOTP', 'Sending OTP...') : t('SendOTPToUnlock', 'Send OTP to unlock')}
              </button>
            </div>
            {error && (
              <div style={{ ...styles.bannerError, marginTop: 18, width: '100%', maxWidth: 720 }}>
                <AlertTriangle size={20} color="#dc2626" />
                <div>
                  <div style={{ fontWeight: 800, color: '#991b1b' }}>{error.title || t('OTPRequired', 'OTP required')}</div>
                  <div style={{ color: '#7f1d1d', marginTop: 4 }}>{error.message || t('VerificationRequired', 'Verification is required to continue.')}</div>
                </div>
              </div>
            )}
          </div>
        </div>

        <OTPVerificationModal
          isOpen={showOTPModal}
          onClose={() => setShowOTPModal(false)}
          onVerified={handleVaultOTPVerified}
          purpose="document_verification"
        />

        <style>{`
          .spin { animation: spin 1s linear infinite; }
          @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  return (
    <div style={styles.shell}>
      <div style={styles.heroBackdrop} />
      <div style={styles.contentWrap}>
        <header style={styles.header}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <div style={styles.brandMark}>
                <Shield size={22} />
              </div>
              <Badge tone="blue">{t('SATYASecureVault', 'SATYA Secure Vault')}</Badge>
              <Badge tone="amber">{t('GovtGradeWorkflow', 'Government-grade workflow')}</Badge>
            </div>
            <h1 style={styles.title}>{t('VaultPageTitle')}</h1>
            <p style={styles.subtitle}>
              {t('GovtDisclaimerNote')}
            </p>
          </div>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button onClick={handleRefresh} disabled={refreshing} style={styles.secondaryBtn}>
              <RefreshCw size={16} /> {t('Refresh', 'Refresh')}
            </button>
            <button onClick={() => document.getElementById('vault-upload-input')?.click()} style={styles.primaryBtn}>
              <Upload size={16} /> {t('UploadDocument', 'Upload Document')}
            </button>
          </div>
        </header>

        <div style={styles.statsGrid}>
          <StatCard icon={ShieldCheck} label={t('Accepted', 'Accepted')} value={acceptedCount} accent="#16a34a" subtext={t('StoredAfterFullVerification', 'Stored after full verification')} />
          <StatCard icon={Clock3} label={t('Pending', 'Pending')} value={pendingCount} accent="#d97706" subtext={t('AwaitingFinalReview', 'Awaiting final review')} />
          <StatCard icon={XCircle} label={t('Rejected', 'Rejected')} value={rejectedCount} accent="#dc2626" subtext={t('BlockedForSafety', 'Blocked for safety')} />
          <StatCard icon={Sparkles} label={t('AvgConfidence', 'Avg confidence')} value={`${avgConfidence}%`} accent="#2563eb" subtext={t('AcrossAllStoredDocuments', 'Across all stored documents')} />
        </div>

        <AnimatePresence>
          {banner && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} style={styles.bannerSuccess}>
              <CheckCircle2 size={18} />
              <div>
                <div style={{ fontWeight: 900, color: '#14532d' }}>{t(banner.title, banner.title)}</div>
                <div style={{ color: '#166534', fontSize: 13 }}>{t(banner.message, banner.message)}</div>
              </div>
            </motion.div>
          )}
          {error && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} style={styles.bannerError}>
              <BadgeAlert size={18} />
              <div>
                <div style={{ fontWeight: 900, color: '#7f1d1d' }}>{t(error.title, error.title)}</div>
                <div style={{ color: '#991b1b', fontSize: 13 }}>{t(error.message, error.message)}</div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div style={{ marginTop: 24, marginBottom: 24 }}>
          <IdentityLockCard
            identity={identity}
            resetAvailable={identity?.resetAvailable !== false}
            onReset={() => setResetOpen(true)}
          />
        </div>

        <div style={{ marginTop: 24, marginBottom: 24 }}>
          <CasteIdentityLockCard
            casteLocked={casteStatus?.caste_locked}
            casteProfile={casteProfile}
            casteDocument={casteDocument}
            onReset={() => setCasteResetOpen(true)}
          />
        </div>

        <div style={styles.mainGrid}>
          <div style={{ display: 'grid', gap: 20 }}>
          <section style={styles.panel}>
            <div style={styles.panelHeader}>
              <div>
                <div style={styles.panelKicker}>{t('UploadDocument', 'Upload')}</div>
                <h2 style={styles.panelTitle}>{t('AddAadhaarCard', 'Add Aadhaar Card')}</h2>
              </div>
              <Badge tone={identity.identityLocked ? 'green' : 'amber'}>
                {identity.identityLocked ? t('IdentityLocked', 'Identity locked') : t('AadhaarRequired', 'Aadhaar required')}
              </Badge>
            </div>

            <div style={styles.uploadBox} onClick={() => document.getElementById('vault-upload-input')?.click()}>
              <input
                id="vault-upload-input"
                type="file"
                accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUpload(file);
                }}
              />
              <div style={styles.uploadIcon}>
                {uploading ? <Loader2 size={24} className="spin" /> : <Upload size={24} />}
              </div>
              <div style={{ fontSize: 18, fontWeight: 900, color: '#0f172a' }}>
                {t('DragDropBrowseFiles', 'Drag and drop or browse files')}
              </div>
              <div style={{ color: '#64748b', textAlign: 'center', lineHeight: 1.7 }}>
                {t('FilesCheckedQualityNote', 'Files are checked for quality, OCR confidence, fraud, QR validity, and identity match before storage.')}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                <Badge>{t('AadhaarCard', 'Aadhaar Card')}</Badge>
              </div>
            </div>

            <AnimatePresence>
              {uploading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  style={styles.progressCard}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: '#64748b', fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        {t('Processing', 'Processing')}
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 900, color: '#0f172a' }}>
                        {stage === 'uploading' ? t('Processing', 'Processing') : stage === 'ocr' ? t('OcrExtractionValidationTitle', 'OCR Extraction & Validation') : stage === 'matching' ? t('IdentityMatchDetails', 'Identity Match Details') : stage === 'fraud' ? t('QrFraudChecksTitle', 'QR/Code & Fraud Checks') : t('Processing', 'Processing')}
                      </div>
                    </div>
                    <Loader2 size={20} className="spin" />
                  </div>
                  <div style={styles.stepTrack}>
                    {['uploading', 'ocr', 'matching', 'fraud', 'saving'].map((step, idx) => (
                      <div key={step} style={{ ...styles.stepDot, background: idx <= ['uploading', 'ocr', 'matching', 'fraud', 'saving'].indexOf(stage) ? '#2563eb' : '#cbd5e1' }} />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </section>

          <section style={styles.panel}>
            <div style={styles.panelHeader}>
              <div>
                <div style={styles.panelKicker}>{t('UploadDocument', 'Upload')}</div>
                <h2 style={styles.panelTitle}>{t('AddCasteCertificate', 'Add Caste Certificate')}</h2>
              </div>
              <Badge tone={casteStatus?.caste_locked ? 'green' : 'amber'}>
                {casteStatus?.caste_locked ? t('CasteVerified', 'Caste verified') : t('Pending', 'Pending')}
              </Badge>
            </div>
            <div style={styles.uploadBox} onClick={() => document.getElementById('vault-caste-upload-input')?.click()}>
              <input
                id="vault-caste-upload-input"
                type="file"
                accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleCasteUpload(file);
                }}
              />
              <div style={styles.uploadIcon}>
                {casteUploading ? <Loader2 size={24} className="spin" /> : <Upload size={24} />}
              </div>
              <div style={{ fontSize: 18, fontWeight: 900, color: '#0f172a' }}>{t('DragDropBrowseFiles', 'Drag and drop or browse files')}</div>
              <div style={{ color: '#64748b', textAlign: 'center', lineHeight: 1.7 }}>
                {t('UploadCasteCertificateNote', 'Upload a Caste Certificate for OCR, caste category detection, and verification before storage.')}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                <Badge>{t('CasteCert', 'Caste Certificate')}</Badge>
              </div>
            </div>

            <AnimatePresence>
              {casteUploading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  style={styles.progressCard}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: '#64748b', fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        {t('Processing', 'Processing')}
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 900, color: '#0f172a' }}>
                        {casteStage === 'uploading' ? t('Processing', 'Processing') : casteStage === 'ocr' ? t('OcrExtractionValidationTitle', 'OCR Extraction & Validation') : casteStage === 'matching' ? t('CasteCategoryVerification', 'Caste Category Verification') : casteStage === 'fraud' ? t('QrFraudChecksTitle', 'QR/Code & Fraud Checks') : t('Processing', 'Processing')}
                      </div>
                    </div>
                    <Loader2 size={20} className="spin" />
                  </div>
                  <div style={styles.stepTrack}>
                    {['uploading', 'ocr', 'matching', 'fraud', 'saving'].map((step, idx) => (
                      <div key={step} style={{ ...styles.stepDot, background: idx <= ['uploading', 'ocr', 'matching', 'fraud', 'saving'].indexOf(casteStage) ? '#2563eb' : '#cbd5e1' }} />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </section>
          </div>

          <section style={styles.panel}>
            <div style={styles.panelHeader}>
              <div>
                <div style={styles.panelKicker}>{t('Vault', 'Vault')}</div>
                <h2 style={styles.panelTitle}>{t('YourDocuments', 'Your documents')}</h2>
              </div>
              <div style={{ minWidth: 260 }}>
                <div style={styles.searchBox}>
                  <Search size={16} color="#64748b" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={t('SearchDocsPlaceholder', 'Search documents')}
                    style={styles.searchInput}
                  />
                </div>
              </div>
            </div>

            {loading ? (
              <div style={styles.skeletonGrid}>
                {[1, 2, 3].map((i) => <div key={i} style={styles.skeletonCard} />)}
              </div>
            ) : documents.length === 0 ? (
              <div style={styles.emptyVault}>
                <FileSearch size={42} />
                <h3 style={{ margin: '14px 0 8px', fontSize: 22, fontWeight: 900 }}>{t('NoDocumentsYet', 'No documents yet')}</h3>
                <p style={{ margin: 0, color: '#475569', lineHeight: 1.7, textAlign: 'center' }}>
                  {t('UploadDocsToBuildVaultNote', 'Upload identity documents to create a secure vault.')}
                </p>
              </div>
            ) : (
              <div style={styles.docGrid}>
                <AnimatePresence>
                  {documents.map((doc) => (
                    <DocumentCard 
                      key={doc._id} 
                      doc={doc} 
                      onDelete={handleDelete} 
                      onDownload={(id) => window.open(`${API_BASE}/download/${id}?user_id=${userId}`, '_blank')}
                      onPreview={(id) => window.open(`${API_BASE}/preview/${id}?user_id=${userId}`, '_blank')}
                    />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </section>
        </div>

        <div style={styles.bottomGrid}>
          <div style={styles.infoPanel}>
            <div style={styles.infoHeader}>
              <div style={styles.infoAccentGreen} />
              <div>
                <div style={{ ...styles.infoKicker, color: '#16a34a', background: 'rgba(34,197,94,0.10)' }}>{t('Capabilities', 'Capabilities')}</div>
                <h3 style={styles.infoTitle}>{t('DocVerificationCapabilities', 'Document Verification Capabilities')}</h3>
              </div>
              <div style={{ ...styles.infoHeaderIcon, color: '#16a34a', background: 'rgba(34,197,94,0.10)' }}>
                <ShieldCheck size={27} />
              </div>
            </div>
            <p style={styles.infoIntro}>
              {t('CapabilitiesIntroNote', 'We verify Aadhaar Cards and Caste Certificates using advanced OCR, identity and category checks to ensure authenticity and prevent fraud.')}
            </p>
            <div style={styles.capabilityGrid}>
              {[
                [t('DocQualityChecksTitle', 'Document Quality Checks'), t('DocQualityChecksDesc', 'Detects blur, crop, low quality and manipulation attempts.')],
                [t('CasteCategoryDetectionTitle', 'Caste Category Detection'), t('CasteCategoryDetectionDesc', 'Extracts and verifies caste category from certificates.')],
                [t('OcrExtractionValidationTitle', 'OCR Extraction & Validation'), t('OcrExtractionValidationDesc', 'Extracts key details and validates the information.')],
                [t('QrFraudChecksTitle', 'QR/Code & Fraud Checks'), t('QrFraudChecksDesc', 'Validates QR codes and checks for tampering or fraud.')],
                [t('AadhaarIdentityVerificationTitle', 'Aadhaar Identity Verification'), t('AadhaarIdentityVerificationDesc', 'Verifies Aadhaar number, name and identity details where applicable.')],
                [t('SecureVerificationTitle', 'Secure Verification'), t('SecureVerificationDesc', 'Documents are accepted only after all applicable checks pass.')],
              ].map(([title, description]) => (
                <div key={title} style={styles.capabilityItem}>
                  <div style={styles.checkIcon}><CheckCircle2 size={15} /></div>
                  <div>
                    <div style={styles.capabilityTitle}>{title}</div>
                    <div style={styles.capabilityText}>{description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div style={styles.infoPanel}>
            <div style={styles.infoHeader}>
              <div style={styles.infoAccentBlue} />
              <div>
                <div style={{ ...styles.infoKicker, color: '#2563eb', background: 'rgba(37,99,235,0.10)' }}>{t('Policy', 'Policy')}</div>
                <h3 style={styles.infoTitle}>{t('VerificationPolicy', 'Verification Policy')}</h3>
              </div>
              <div style={{ ...styles.infoHeaderIcon, color: '#2563eb', background: 'rgba(37,99,235,0.10)' }}>
                <FileText size={27} />
              </div>
            </div>
            <p style={styles.infoIntro}>
              {t('VerificationPolicyIntroNote', 'Each document is verified through its own dedicated process to ensure authenticity, accurate identification, and secure storage.')}
            </p>
            <div style={styles.policyList}>
              {[
                [Fingerprint, t('AadhaarCardVerification', 'Aadhaar Card Verification'), t('AadhaarPolicyDesc', 'Verified through the Aadhaar verification process: OCR, identity and name matching.'), '#8b5cf6'],
                [VenetianMask, t('CasteCertificateVerification', 'Caste Certificate Verification'), t('CastePolicyDesc', 'Verified through caste-category extraction and verification from the uploaded certificate.'), '#7c3aed'],
                [Shield, t('DocumentWiseProcessingTitle', 'Document-wise Processing'), t('DocumentWiseProcessingDesc', 'Each document is processed according to its own verification requirements.'), '#16a34a'],
                [BadgeCheck, t('AcceptanceCriteriaTitle', 'Acceptance Criteria'), t('AcceptanceCriteriaDesc', 'Documents are accepted only after applicable quality, OCR, identity/category and security checks pass.'), '#2563eb'],
              ].map(([Icon, title, description, color]) => (
                <div key={title} style={styles.policyItem}>
                  <div style={{ ...styles.policyIcon, color, background: `${color}18` }}><Icon size={20} /></div>
                  <div>
                    <div style={styles.policyTitle}>{title}</div>
                    <div style={styles.policyText}>{description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {confirmation && pendingUpload && (
          <Modal
            title={t('ConfirmDocOwnership', 'Confirm Document Ownership')}
            subtitle={`${t('IdentityMatchScore', 'Identity match score')}: ${Math.round(confirmation.score || 0)}%`}
            onClose={() => {
              setConfirmation(null);
              setPendingUpload(null);
            }}
          >
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={styles.callout}>
                <Badge tone="amber"><BadgeInfo size={14} /> {t('LowConfidence', 'Low confidence')}</Badge>
                <div style={{ marginTop: 10, color: '#7c2d12', lineHeight: 1.7 }}>
                  {confirmation.message}
                </div>
              </div>
              <div style={styles.confirmGrid}>
                {Object.entries(confirmation.details || {}).slice(0, 6).map(([key, value]) => (
                  <div key={key} style={styles.confirmField}>
                    <div style={styles.confirmLabel}>{key.replace(/_/g, ' ')}</div>
                    <div style={styles.confirmValue}>{displayValue(value)}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => {
                    setConfirmation(null);
                    setPendingUpload(null);
                  }}
                  style={styles.secondaryBtn}
                >
                  {t('Cancel', 'Cancel')}
                </button>
                <button type="button" onClick={confirmPendingUpload} style={styles.primaryBtn}>
                  {t('ConfirmAndAdd', 'Confirm and Add')}
                </button>
              </div>
            </div>
          </Modal>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {resetOpen && (
          <Modal
            title={t('ResetIdentityVerification', 'Reset Identity Verification')}
            subtitle={t('ResetIdentitySubtitle', 'This permanently removes your stored identity verification data.')}
            onClose={() => setResetOpen(false)}
            width={720}
          >
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={styles.calloutDanger}>
                {t('ResetIdentityWarning', 'Resetting your Identity Lock will permanently erase your stored identity verification data. Unrelated documents in your SATYA Vault will remain available. This action cannot be undone.')}
              </div>
              <div style={styles.inputGrid}>
                <label style={styles.label}>
                  {t('AccountPassword', 'Account Password')}
                  <input
                    type="password"
                    value={resetPassword}
                    onChange={(e) => setResetPassword(e.target.value)}
                    style={styles.input}
                    placeholder={t('ReEnterPassword', 'Re-enter your password')}
                  />
                </label>
              </div>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                <button type="button" onClick={() => setResetOpen(false)} style={styles.secondaryBtn} disabled={resetBusy}>
                  {t('Cancel', 'Cancel')}
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={resetBusy || !resetPassword}
                  style={{
                    ...styles.dangerBtn,
                    opacity: resetBusy || !resetPassword ? 0.6 : 1,
                    cursor: resetBusy || !resetPassword ? 'not-allowed' : 'pointer',
                  }}
                >
                  {resetBusy ? t('Resetting', 'Resetting...') : t('ConfirmReset', 'Confirm Reset')}
                </button>
              </div>
            </div>
          </Modal>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {casteResetOpen && (
          <Modal
            title={t('ResetCasteVerification', 'Reset Caste Verification')}
            subtitle={t('ResetCasteSubtitle', 'This permanently removes your verified caste reservation status.')}
            onClose={() => setCasteResetOpen(false)}
            width={720}
          >
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={styles.calloutDanger}>
                {t('ResetCasteWarning', 'Resetting your Caste Identity Lock will permanently erase your verified caste category (General, OBC, SC, ST). Scheme eligibility matching will fall back to manual selection. This action does not reset your Aadhaar Identity Lock.')}
              </div>
              <div style={styles.inputGrid}>
                <label style={styles.label}>
                  {t('AccountPassword', 'Account Password')}
                  <input
                    type="password"
                    value={casteResetPassword}
                    onChange={(e) => setCasteResetPassword(e.target.value)}
                    style={styles.input}
                    placeholder={t('ReEnterPassword', 'Re-enter your password')}
                  />
                </label>
              </div>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                <button type="button" onClick={() => setCasteResetOpen(false)} style={styles.secondaryBtn} disabled={casteResetBusy}>
                  {t('Cancel', 'Cancel')}
                </button>
                <button
                  type="button"
                  onClick={handleCasteReset}
                  disabled={casteResetBusy || !casteResetPassword}
                  style={{
                    ...styles.dangerBtn,
                    opacity: casteResetBusy || !casteResetPassword ? 0.6 : 1,
                    cursor: casteResetBusy || !casteResetPassword ? 'not-allowed' : 'pointer',
                  }}
                >
                  {casteResetBusy ? t('Resetting', 'Resetting...') : t('ConfirmCasteReset', 'Confirm Caste Reset')}
                </button>
              </div>
            </div>
          </Modal>
        )}
      </AnimatePresence>

      <DocumentReviewModal
        key={reviewDoc?.document_id || reviewDoc?.document?._id || 'review-modal'}
        isOpen={!!reviewDoc}
        document={reviewDoc?.document || {}}
        onClose={() => {
          setReviewDoc(null);
          fetchVault(query, true); // refresh to show Awaiting Review doc
        }}
        onConfirm={handleReviewConfirm}
      />

      <OTPVerificationModal
        isOpen={showOTPModal}
        onClose={() => setShowOTPModal(false)}
        onVerified={handleVaultOTPVerified}
        purpose="document_verification"
      />

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const styles = {
  shell: {
    minHeight: '100vh',
    position: 'relative',
    overflow: 'hidden',
    background: 'linear-gradient(180deg, #FF9933 0%, #FFFFFF 50%, #138808 100%)',
  },
  heroBackdrop: {
    position: 'absolute',
    inset: 0,
    background: 'radial-gradient(circle at 15% 20%, rgba(255,153,51,0.15), transparent 28%), radial-gradient(circle at 85% 8%, rgba(19,136,8,0.16), transparent 24%), radial-gradient(circle at 50% 85%, rgba(79,70,229,0.08), transparent 28%)',
    pointerEvents: 'none',
  },
  contentWrap: {
    position: 'relative',
    zIndex: 1,
    maxWidth: 1440,
    margin: '0 auto',
    padding: '32px 24px 80px',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 20,
    flexWrap: 'wrap',
    marginBottom: 22,
  },
  brandMark: {
    width: 46,
    height: 46,
    borderRadius: 16,
    background: 'linear-gradient(135deg, #0f172a, #2563eb)',
    color: '#fff',
    display: 'grid',
    placeItems: 'center',
    boxShadow: '0 18px 36px rgba(15,23,42,0.18)',
  },
  title: {
    margin: 0,
    fontSize: 'clamp(2rem, 4vw, 3.4rem)',
    lineHeight: 1.02,
    fontWeight: 950,
    letterSpacing: '-0.04em',
    color: '#0f172a',
  },
  subtitle: {
    margin: '14px 0 0',
    maxWidth: 860,
    color: '#475569',
    fontSize: 15,
    lineHeight: 1.8,
  },
  primaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 10,
    border: 'none',
    borderRadius: 16,
    background: 'linear-gradient(135deg, #0f172a, #2563eb)',
    color: '#fff',
    fontWeight: 900,
    padding: '13px 18px',
    boxShadow: '0 18px 32px rgba(37,99,235,0.22)',
    cursor: 'pointer',
  },
  secondaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 10,
    borderRadius: 16,
    padding: '13px 18px',
    border: '1px solid rgba(148,163,184,0.28)',
    background: 'rgba(255,255,255,0.9)',
    color: '#0f172a',
    fontWeight: 900,
    cursor: 'pointer',
  },
  dangerBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
    padding: '13px 18px',
    border: 'none',
    background: 'linear-gradient(135deg, #dc2626, #ef4444)',
    color: '#fff',
    fontWeight: 900,
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: 16,
    marginBottom: 22,
  },
  bannerSuccess: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 12,
    padding: 16,
    borderRadius: 20,
    background: 'linear-gradient(135deg, rgba(220,252,231,0.95), rgba(240,253,244,0.95))',
    border: '1px solid rgba(34,197,94,0.18)',
    marginBottom: 14,
  },
  bannerError: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 12,
    padding: 16,
    borderRadius: 20,
    background: 'linear-gradient(135deg, rgba(254,226,226,0.95), rgba(255,247,247,0.95))',
    border: '1px solid rgba(239,68,68,0.16)',
    marginBottom: 14,
  },
  mainGrid: {
    display: 'grid',
    gridTemplateColumns: 'minmax(320px, 430px) 1fr',
    gap: 20,
    alignItems: 'start',
  },
  panel: {
    background: 'rgba(255,255,255,0.8)',
    border: '1px solid rgba(148,163,184,0.16)',
    borderRadius: 28,
    padding: 22,
    backdropFilter: 'blur(18px)',
    boxShadow: '0 22px 60px rgba(15,23,42,0.08)',
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    flexWrap: 'wrap',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  panelKicker: {
    color: '#2563eb',
    fontSize: 11,
    fontWeight: 900,
    textTransform: 'uppercase',
    letterSpacing: '0.12em',
  },
  panelTitle: {
    margin: '6px 0 0',
    color: '#0f172a',
    fontSize: 24,
    fontWeight: 950,
    letterSpacing: '-0.03em',
  },
  uploadBox: {
    minHeight: 430,
    borderRadius: 28,
    border: '1.5px dashed rgba(37,99,235,0.22)',
    background: 'linear-gradient(180deg, rgba(248,250,252,0.95), rgba(255,255,255,0.9))',
    display: 'grid',
    placeItems: 'center',
    padding: 26,
    gap: 18,
    cursor: 'pointer',
  },
  uploadIcon: {
    width: 72,
    height: 72,
    borderRadius: 24,
    background: 'linear-gradient(135deg, rgba(37,99,235,0.12), rgba(16,185,129,0.12))',
    display: 'grid',
    placeItems: 'center',
    color: '#2563eb',
  },
  progressCard: {
    marginTop: 16,
    background: '#fff',
    borderRadius: 22,
    padding: 18,
    border: '1px solid rgba(148,163,184,0.14)',
  },
  stepTrack: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, 1fr)',
    gap: 8,
    marginTop: 14,
  },
  stepDot: {
    height: 8,
    borderRadius: 999,
    transition: 'background 200ms ease',
  },
  searchBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: '#fff',
    borderRadius: 16,
    border: '1px solid rgba(148,163,184,0.2)',
    padding: '0 14px',
    height: 50,
  },
  searchInput: {
    border: 'none',
    outline: 'none',
    width: '100%',
    fontSize: 14,
    background: 'transparent',
    color: '#0f172a',
  },
  skeletonGrid: {
    display: 'grid',
    gap: 14,
  },
  skeletonCard: {
    height: 170,
    borderRadius: 22,
    background: 'linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 37%, #f1f5f9 63%)',
    backgroundSize: '400% 100%',
    animation: 'shimmer 1.4s ease infinite',
  },
  emptyVault: {
    minHeight: 360,
    borderRadius: 26,
    border: '1px dashed rgba(148,163,184,0.24)',
    background: 'linear-gradient(180deg, rgba(248,250,252,0.8), rgba(255,255,255,0.9))',
    display: 'grid',
    placeItems: 'center',
    padding: 28,
    color: '#334155',
    textAlign: 'center',
  },
  docGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 16,
  },
  bottomGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: 20,
    marginTop: 20,
  },
  infoPanel: {
    background: 'linear-gradient(135deg, rgba(255,255,255,0.96), rgba(247,251,255,0.92))',
    border: '1px solid rgba(255,255,255,0.72)',
    borderRadius: 26,
    padding: 28,
    boxShadow: '0 18px 50px rgba(15,23,42,0.10)',
  },
  infoHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 13,
  },
  infoAccentGreen: {
    width: 4,
    height: 52,
    borderRadius: 999,
    background: '#22c55e',
    flex: '0 0 auto',
  },
  infoAccentBlue: {
    width: 4,
    height: 52,
    borderRadius: 999,
    background: '#3b82f6',
    flex: '0 0 auto',
  },
  infoKicker: {
    display: 'inline-flex',
    borderRadius: 999,
    padding: '4px 10px',
    fontSize: 10,
    fontWeight: 900,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  infoTitle: {
    margin: '7px 0 0',
    color: '#0f2343',
    fontSize: 22,
    fontWeight: 900,
    letterSpacing: '-0.02em',
  },
  infoHeaderIcon: {
    width: 52,
    height: 52,
    display: 'grid',
    placeItems: 'center',
    borderRadius: 13,
    marginLeft: 'auto',
  },
  infoIntro: {
    margin: '13px 0 20px 17px',
    maxWidth: 560,
    color: '#64748b',
    fontSize: 13,
    lineHeight: 1.55,
  },
  capabilityGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '18px 24px',
  },
  capabilityItem: {
    display: 'grid',
    gridTemplateColumns: '26px minmax(0, 1fr)',
    gap: 10,
  },
  checkIcon: {
    width: 24,
    height: 24,
    display: 'grid',
    placeItems: 'center',
    borderRadius: '50%',
    color: '#16a34a',
    background: 'rgba(34,197,94,0.13)',
  },
  capabilityTitle: {
    color: '#1e365b',
    fontSize: 13,
    fontWeight: 850,
    lineHeight: 1.3,
  },
  capabilityText: {
    marginTop: 4,
    color: '#718096',
    fontSize: 11.5,
    lineHeight: 1.45,
  },
  policyList: {
    display: 'grid',
    gap: 9,
  },
  policyItem: {
    display: 'grid',
    gridTemplateColumns: '48px minmax(0, 1fr)',
    gap: 13,
    alignItems: 'center',
    padding: '11px 13px',
    borderRadius: 12,
    background: 'linear-gradient(90deg, rgba(241,245,249,0.88), rgba(248,250,252,0.64))',
  },
  policyIcon: {
    width: 36,
    height: 36,
    display: 'grid',
    placeItems: 'center',
    borderRadius: 10,
  },
  policyTitle: {
    color: '#1e365b',
    fontSize: 12.5,
    fontWeight: 850,
    lineHeight: 1.35,
  },
  policyText: {
    marginTop: 3,
    color: '#718096',
    fontSize: 11.25,
    lineHeight: 1.4,
  },
  list: {
    margin: '14px 0 0',
    paddingLeft: 20,
    color: '#334155',
    lineHeight: 1.85,
  },
  paragraph: {
    margin: '12px 0 0',
    color: '#334155',
    lineHeight: 1.8,
  },
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(15,23,42,0.62)',
    backdropFilter: 'blur(8px)',
    zIndex: 80,
    display: 'grid',
    placeItems: 'center',
    padding: 16,
  },
  modalCard: {
    background: '#fff',
    borderRadius: 26,
    padding: 24,
    boxShadow: '0 30px 90px rgba(15,23,42,0.28)',
    border: '1px solid rgba(148,163,184,0.12)',
  },
  callout: {
    background: 'linear-gradient(180deg, #fff7ed, #fffbeb)',
    border: '1px solid rgba(245,158,11,0.18)',
    borderRadius: 18,
    padding: 16,
  },
  calloutDanger: {
    background: 'linear-gradient(180deg, #fef2f2, #fff7f7)',
    border: '1px solid rgba(239,68,68,0.16)',
    borderRadius: 18,
    padding: 16,
    color: '#7f1d1d',
    lineHeight: 1.8,
  },
  confirmGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: 12,
  },
  confirmField: {
    background: '#f8fafc',
    borderRadius: 16,
    padding: 14,
    border: '1px solid rgba(148,163,184,0.12)',
  },
  confirmLabel: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: 900,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  confirmValue: {
    color: '#0f172a',
    fontWeight: 800,
    marginTop: 6,
    wordBreak: 'break-word',
  },
  inputGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
    gap: 14,
  },
  label: {
    display: 'grid',
    gap: 8,
    color: '#0f172a',
    fontSize: 13,
    fontWeight: 800,
  },
  input: {
    height: 48,
    borderRadius: 14,
    border: '1px solid rgba(148,163,184,0.22)',
    padding: '0 14px',
    fontSize: 14,
    outline: 'none',
    background: '#fff',
  },
  emptyState: {
    background: 'rgba(255,255,255,0.88)',
    borderRadius: 28,
    padding: 28,
    textAlign: 'center',
    maxWidth: 700,
    margin: '80px auto 0',
    boxShadow: '0 24px 72px rgba(15,23,42,0.12)',
    border: '1px solid rgba(148,163,184,0.16)',
  },
};
